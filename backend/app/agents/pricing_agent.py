"""PricingAgent: otonom fiyat optimizasyonu — Gemini Function Calling veya deterministik fallback.

Fallback order: Gemini (1 attempt, per-turn timeout) → deterministic rule-based.
Deterministic path is the canonical spec; Gemini's job is to call the same tools
in the right order. Tests cover deterministic only — add Gemini tests via mock client.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from typing import Any

from app.integrations.base import BasePricingIntegration, IntegrationError

logger = logging.getLogger(__name__)

_BUYBOX_UNDERCUT = Decimal("0.50")            # TL below buybox winner
_MIN_PRICE_DELTA = Decimal("0.50")            # ignore changes smaller than this
_PROFIT_MAX_RATIO = Decimal("0.95")           # own_site: 5% below competitor
_OUTLIER_GAP_RATIO = Decimal("0.20")          # cheapest >20% below 2nd → treat as outlier
_PROFIT_MAX_RAISE_STEP = Decimal("1.05")      # max 5% raise per step when holding buybox
_MAX_GEMINI_TURNS = 6
_GEMINI_TOTAL_TIMEOUT = 40.0                  # hard cap across all turns
_CONFIDENCE_THRESHOLD = 75.0                  # below this → requires human approval


class PricingStrategy(str, Enum):
    BUYBOX = "buybox"
    LOGISTICS_BALANCE = "logistics_balance"
    PROFIT_MAX = "profit_max"


class PricingDecision(str, Enum):
    PRICE_UPDATED = "price_updated"
    NO_ACTION = "no_action"
    FLOOR_HIT = "floor_hit"


@dataclass
class PricingContext:
    product_platform_id: int
    sku: str
    platform_code: str
    strategy: PricingStrategy
    current_price: Decimal
    floor_price: Decimal
    ceiling_price: Decimal
    base_cost: Decimal
    shipping_cost: Decimal
    commission_rate: Decimal
    external_id: str
    min_margin: float = 0.05


@dataclass
class PricingResult:
    decision: PricingDecision
    old_price: Decimal
    new_price: Decimal
    reasoning: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    duration_ms: int = 0


# ─── Pure tool functions (single source of truth for floor formula) ────────────

def _tool_calculate_floor_price(
    base_cost: float, shipping: float, commission_rate: float, min_margin: float
) -> dict[str, Any]:
    """Wraps compute_floor_price — single definition of the formula."""
    from app.api.products import compute_floor_price  # lazy to avoid circular at import time

    floor = compute_floor_price(
        Decimal(str(base_cost)),
        Decimal(str(shipping)),
        Decimal(str(commission_rate)),
        min_margin,
    )
    return {"floor_price": float(floor)}


async def _tool_get_competitor_prices(
    integration: BasePricingIntegration, external_id: str
) -> dict[str, Any]:
    try:
        snapshot = await integration.get_competitor_snapshot(external_id)
        return {
            "competitors": [
                {"seller": c.seller_name, "price": float(c.price), "has_buybox": c.has_buybox}
                for c in snapshot.competitors
            ],
            "own_has_buybox": snapshot.own_has_buybox,
            "own_price": float(snapshot.own_price) if snapshot.own_price else None,
        }
    except IntegrationError as exc:
        logger.warning("get_competitor_prices failed for %s: %s", external_id, exc)
        return {"competitors": [], "own_has_buybox": False, "own_price": None, "error": str(exc)}


async def _tool_update_platform_price(
    integration: BasePricingIntegration, external_id: str, new_price: float, reason: str
) -> dict[str, Any]:
    try:
        success = await integration.update_price(external_id, new_price)
        return {"success": success, "new_price": new_price, "reason": reason}
    except IntegrationError as exc:
        logger.error("update_platform_price failed for %s: %s", external_id, exc)
        return {"success": False, "new_price": new_price, "error": str(exc)}


# ─── Strategy logic (pure, fully testable) ────────────────────────────────────

def _find_smart_reference(prices: list[Decimal]) -> Decimal:
    """Ignore outlier cheapest. If cheapest >20% below 2nd, use 2nd as reference."""
    if len(prices) < 2:
        return prices[0]
    if prices[0] < prices[1] * (Decimal("1") - _OUTLIER_GAP_RATIO):
        return prices[1]  # outlier — use 2nd cheapest
    return prices[0]


def _apply_strategy(
    strategy: PricingStrategy,
    current_price: Decimal,
    floor_price: Decimal,
    ceiling_price: Decimal,
    competitors: list[dict[str, Any]],
    own_has_buybox: bool = False,
) -> Decimal:
    """Compute target price from strategy + competitors. Always clamped to [floor, ceiling]."""
    if not competitors:
        if strategy == PricingStrategy.PROFIT_MAX:
            return ceiling_price  # no competitors → maximize profit at ceiling
        return current_price  # rakip yoksa mevcut fiyatı koru

    prices = sorted([Decimal(str(c["price"])) for c in competitors])
    min_price = prices[0]
    avg_price = sum(prices, Decimal("0")) / len(prices)
    n = len(prices)
    median_price = (
        (prices[n // 2 - 1] + prices[n // 2]) / Decimal("2")
        if n % 2 == 0
        else prices[n // 2]
    )

    # Find buybox winner
    buybox_candidates = [c for c in competitors if c.get("has_buybox")]
    buybox_winner_price = min(Decimal(str(c["price"])) for c in buybox_candidates) if buybox_candidates else min_price

    if strategy == PricingStrategy.BUYBOX:
        target = _buybox_target(current_price, sorted(prices), buybox_winner_price, own_has_buybox)
    elif strategy == PricingStrategy.LOGISTICS_BALANCE:
        target = _logistics_target(current_price, sorted(prices), median_price, buybox_winner_price, own_has_buybox, floor_price)
    else:  # PROFIT_MAX
        target = _profitmax_target(current_price, ceiling_price, sorted(prices), buybox_winner_price, own_has_buybox)

    return max(floor_price, min(ceiling_price, target)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def _buybox_target(
    current: Decimal,
    sorted_prices: list[Decimal],
    buybox_winner: Decimal,
    own_has_buybox: bool,
) -> Decimal:
    """Win buybox without leaving money on the table."""
    if own_has_buybox and sorted_prices:
        # We hold buybox — raise toward cheapest competitor (don't leave money)
        target = sorted_prices[0] - _BUYBOX_UNDERCUT
        return max(target, current)  # never drop when already winning

    # We don't have buybox — undercut the buybox winner
    ref = _find_smart_reference(sorted_prices)
    return ref - _BUYBOX_UNDERCUT


def _logistics_target(
    current: Decimal,
    sorted_prices: list[Decimal],
    median: Decimal,
    buybox_winner: Decimal,
    own_has_buybox: bool,
    floor_price: Decimal,
) -> Decimal:
    """Stay near market median, compete for buybox when needed."""
    if own_has_buybox:
        # Already winning buybox — stay near median, don't undercut unnecessarily
        if current <= median:
            return current  # already competitive
        return median  # above median, ease down

    # No buybox — target the median (logistics is about market stability)
    return median


def _profitmax_target(
    current: Decimal,
    ceiling: Decimal,
    sorted_prices: list[Decimal],
    buybox_winner: Decimal,
    own_has_buybox: bool,
) -> Decimal:
    """Maximize margin: raise when possible, undercut when necessary."""
    if own_has_buybox:
        # We hold buybox — gradually raise toward cheapest competitor
        raise_target = (current * _PROFIT_MAX_RAISE_STEP).quantize(Decimal("0.01"))
        if sorted_prices:
            cheapest_competitor = sorted_prices[0]
            cap = (cheapest_competitor * _PROFIT_MAX_RATIO).quantize(Decimal("0.01"))
            return max(current, min(raise_target, cap, ceiling))
        return max(current, min(raise_target, ceiling))

    # No buybox — undercut using smart reference
    ref = _find_smart_reference(sorted_prices)
    return ref * _PROFIT_MAX_RATIO


# ─── Gemini prompt + tool declarations ───────────────────────────────────────

_SYSTEM_PROMPT = (
    "Sen bir e-ticaret fiyatlandırma uzmanısın. Amacın maksimum kâr ile buybox kazanmak arasında "
    "denge kurmak. Belirtilen strateji doğrultusunda şu sırayı takip et:\n"
    "1) get_competitor_prices ile rakip fiyatlarını ve buybox durumunu al\n"
    "2) calculate_floor_price ile taban fiyatı doğrula\n"
    "3) Strateji kuralını uygula — ama AKILLI ol:\n"
    "   - PARAYI MASADA BIRAKMA: Eğer buybox sende ise ve ikinci en düşük rakipten çok aşağıdaysan, "
    "fiyatı ikinci rakibin 0.50 TL altına YÜKSELT (mevcut fiyatı düşürme)\n"
    "   - OUTLIER'LARI GÖRMEZDEN GEL: En düşük rakip diğerlerinden %20'den fazla ucuzsa, "
    "ikinci en düşüğü referans al (en ucuz outlier muhtemelen stok eritiyordur)\n"
    "   - Her rakibin has_buybox flag'ine bak; buybox sahibinin fiyatını referans al\n"
    "4) Fiyat değişmesi gerekiyorsa update_platform_price çağır\n"
    "5) log_decision ile kararını ve DETAYLI gerekçeni yaz (price_updated | no_action | floor_hit)"
)

_STRATEGY_HINTS: dict[PricingStrategy, str] = {
    PricingStrategy.BUYBOX: (
        "BUYBOX STRATEJİSİ:\n"
        "- Buybox KAYBETTİYSEN: buybox sahibi rakibin 0.50 TL altına in\n"
        "- Buybox SENDE İSE: ikinci en düşük rakibin 0.50 TL altına YÜKSEL (para bırakma!) "
        "— ama mevcut fiyatından aşağı inme\n"
        "- En düşük rakip outlier ise (diğerlerinden %20+ ucuz), ikinci en düşüğü referans al"
    ),
    PricingStrategy.LOGISTICS_BALANCE: (
        "LOJİSTİK DENGESİ:\n"
        "- Rakip fiyatlarının MEDYAN'ına yakın dur (ortalamayı outlier'lar bozabilir)\n"
        "- Buybox sende ise ve medyandan düşüksen fiyatı koru\n"
        "- Buybox sende değilse buybox kazananın 0.50 TL altına in (floor'a saygılı)"
    ),
    PricingStrategy.PROFIT_MAX: (
        "KÂR MAKSİMİZASYONU:\n"
        "- Rakip YOKSA: tavan fiyatta kal\n"
        "- Buybox SENDE İSE: fiyatı %5 kademeli YÜKSELT (tavanı aşma)\n"
        "- Buybox KAYBETTİYSEN: referans rakibin %5 altına in"
    ),
}


def _build_context_prompt(ctx: PricingContext) -> str:
    hint = _STRATEGY_HINTS.get(ctx.strategy, ctx.strategy.value)
    return (
        f"Platform: {ctx.platform_code.upper()} | SKU: {ctx.sku}\n"
        f"Strateji: {ctx.strategy.value} — {hint}\n\n"
        f"Mevcut Durum:\n"
        f"  Fiyat: {ctx.current_price} TL\n"
        f"  Floor: {ctx.floor_price} TL | Ceiling: {ctx.ceiling_price} TL\n"
        f"  Maliyet: {ctx.base_cost} TL | Kargo: {ctx.shipping_cost} TL | "
        f"Komisyon: %{float(ctx.commission_rate) * 100:.0f}\n"
        f"  External ID: {ctx.external_id}\n"
    )


def _make_gemini_tools() -> Any:
    from google.genai import types

    return [types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="get_competitor_prices",
            description="Platformdaki rakip fiyatlarını ve buybox durumunu çek.",
            parameters=types.Schema(type=types.Type.OBJECT, properties={}, required=[]),
        ),
        types.FunctionDeclaration(
            name="calculate_floor_price",
            description="Kâr marjını koruyarak minimum satış fiyatını hesapla.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "base_cost": types.Schema(type=types.Type.NUMBER, description="Ürün maliyeti (TL)"),
                    "shipping": types.Schema(type=types.Type.NUMBER, description="Kargo maliyeti (TL)"),
                    "commission_rate": types.Schema(type=types.Type.NUMBER, description="Komisyon oranı (0-1)"),
                    "min_margin": types.Schema(type=types.Type.NUMBER, description="Min kâr marjı (0-1)"),
                },
                required=["base_cost", "shipping", "commission_rate", "min_margin"],
            ),
        ),
        types.FunctionDeclaration(
            name="update_platform_price",
            description="Platformda yeni fiyatı uygula.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "new_price": types.Schema(type=types.Type.NUMBER, description="Yeni fiyat (TL)"),
                    "reason": types.Schema(type=types.Type.STRING, description="Değişim gerekçesi"),
                },
                required=["new_price", "reason"],
            ),
        ),
        types.FunctionDeclaration(
            name="log_decision",
            description="Fiyatlandırma kararını ve gerekçesini kaydet.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "reasoning": types.Schema(type=types.Type.STRING),
                    "decision": types.Schema(
                        type=types.Type.STRING,
                        description="price_updated | no_action | floor_hit",
                    ),
                },
                required=["reasoning", "decision"],
            ),
        ),
    ])]


# ─── Agent ────────────────────────────────────────────────────────────────────

class PricingAgent:
    """Autonomous pricing via Gemini Function Calling or deterministic fallback.

    Pass `client` for testing (avoids real API calls). Omit in production.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
        timeout: float = 15.0,
        *,
        client: Any = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._per_turn_timeout = timeout
        self._client = client
        self._available = bool(api_key)

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        from google import genai
        return genai.Client(api_key=self._api_key)

    async def run(
        self,
        ctx: PricingContext,
        integration: BasePricingIntegration,
        trigger_event: str = "manual",
    ) -> PricingResult:
        """Run the agent. Returns result; caller handles DB persistence."""
        if not self._available:
            logger.info(
                "PricingAgent: no API key — deterministic mode for %s/%s",
                ctx.platform_code, ctx.sku,
            )
            return await self._run_deterministic(ctx, integration)

        try:
            return await asyncio.wait_for(
                self._run_with_gemini(ctx, integration),
                timeout=_GEMINI_TOTAL_TIMEOUT,  # hard cap; per-turn timeout is inner
            )
        except (TimeoutError, asyncio.TimeoutError):
            logger.error(
                "PricingAgent: total timeout (%ss) for %s/%s — deterministic fallback",
                _GEMINI_TOTAL_TIMEOUT, ctx.platform_code, ctx.sku,
            )
        except Exception as exc:
            logger.error(
                "PricingAgent: Gemini error for %s/%s — deterministic fallback: %s",
                ctx.platform_code, ctx.sku, exc,
            )
        return await self._run_deterministic(ctx, integration)

    async def _dispatch_tool(
        self,
        name: str,
        args: dict[str, Any],
        ctx: PricingContext,
        integration: BasePricingIntegration,
    ) -> dict[str, Any]:
        if name == "get_competitor_prices":
            return await _tool_get_competitor_prices(integration, ctx.external_id)
        if name == "calculate_floor_price":
            return _tool_calculate_floor_price(**args)
        if name == "update_platform_price":
            return await _tool_update_platform_price(
                integration, ctx.external_id,
                float(args["new_price"]), str(args.get("reason", "")),
            )
        if name == "log_decision":
            return {"logged": True, "decision": args.get("decision", ""), "reasoning": args.get("reasoning", "")}
        return {"error": f"Unknown tool: {name}"}

    async def _run_with_gemini(
        self, ctx: PricingContext, integration: BasePricingIntegration
    ) -> PricingResult:
        from google.genai import types

        client = self._get_client()
        start = time.monotonic()
        tool_calls: list[dict[str, Any]] = []
        final_reasoning = ""
        final_decision = PricingDecision.NO_ACTION
        new_price = ctx.current_price
        turn = 0

        contents: list[types.Content] = [
            types.Content(
                role="user",
                parts=[types.Part(text=_SYSTEM_PROMPT + "\n\n" + _build_context_prompt(ctx))],
            )
        ]
        config = types.GenerateContentConfig(
            tools=_make_gemini_tools(),
            temperature=0.3,
        )

        for turn in range(_MAX_GEMINI_TURNS):
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    client.models.generate_content,
                    model=self._model,
                    contents=list(contents),
                    config=config,
                ),
                timeout=self._per_turn_timeout,
            )

            candidate = response.candidates[0] if response.candidates else None
            if candidate is None:
                break
            contents.append(candidate.content)

            # Collect function calls; getattr guards against text-only parts
            function_calls_in_turn = [
                fc
                for part in candidate.content.parts
                for fc in [getattr(part, "function_call", None)]
                if fc is not None and getattr(fc, "name", None)
            ]

            if not function_calls_in_turn:
                break  # model finished with a text reply

            fn_response_parts = []
            for fc in function_calls_in_turn:
                tool_name: str = fc.name
                tool_args: dict[str, Any] = dict(fc.args) if fc.args else {}
                result = await self._dispatch_tool(tool_name, tool_args, ctx, integration)
                tool_calls.append({"tool": tool_name, "args": tool_args, "result": result})

                if tool_name == "log_decision":
                    final_reasoning = result.get("reasoning", "")
                    try:
                        final_decision = PricingDecision(result.get("decision", "no_action"))
                    except ValueError:
                        final_decision = PricingDecision.NO_ACTION
                elif tool_name == "update_platform_price" and result.get("success"):
                    new_price = Decimal(str(result["new_price"])).quantize(Decimal("0.01"))

                fn_response_parts.append(
                    types.Part(
                        function_response=types.FunctionResponse(name=tool_name, response=result)
                    )
                )

            contents.append(types.Content(role="user", parts=fn_response_parts))

        if not final_reasoning:
            final_reasoning = f"Gemini completed in {turn + 1} turn(s)."
        if new_price != ctx.current_price and final_decision == PricingDecision.NO_ACTION:
            final_decision = PricingDecision.PRICE_UPDATED

        return PricingResult(
            decision=final_decision,
            old_price=ctx.current_price,
            new_price=new_price,
            reasoning=final_reasoning,
            tool_calls=tool_calls,
            duration_ms=int((time.monotonic() - start) * 1000),
        )

    async def _run_deterministic(
        self, ctx: PricingContext, integration: BasePricingIntegration
    ) -> PricingResult:
        start = time.monotonic()
        tool_calls: list[dict[str, Any]] = []

        # 1. Competitor prices
        comp_result = await _tool_get_competitor_prices(integration, ctx.external_id)
        tool_calls.append({"tool": "get_competitor_prices", "args": {}, "result": comp_result})

        # 2. Verify floor price
        floor_args = {
            "base_cost": float(ctx.base_cost),
            "shipping": float(ctx.shipping_cost),
            "commission_rate": float(ctx.commission_rate),
            "min_margin": ctx.min_margin,
        }
        floor_result = _tool_calculate_floor_price(**floor_args)
        # ctx.floor_price is the authoritative stored floor (computed at listing time).
        # We call the tool for transparency in logs; use the stored value for decisions.
        floor_price = ctx.floor_price
        tool_calls.append({"tool": "calculate_floor_price", "args": floor_args, "result": floor_result})

        # 3. Strategy → target price
        competitors = comp_result.get("competitors", [])
        own_has_buybox = comp_result.get("own_has_buybox", False)
        target = _apply_strategy(ctx.strategy, ctx.current_price, floor_price, ctx.ceiling_price, competitors, own_has_buybox)

        # 4. Decide
        delta = abs(target - ctx.current_price)
        # hit_floor: only meaningful when we were pushed down TO the floor from above it.
        # Does not fire when current_price is already at/below floor (those edge cases stay NO_ACTION).
        hit_floor = target <= floor_price and floor_price < ctx.current_price

        if delta < _MIN_PRICE_DELTA:
            decision = PricingDecision.NO_ACTION
            new_price = ctx.current_price
            reasoning = (
                f"Strateji {ctx.strategy.value}: hedef {target} TL, "
                f"delta {delta:.2f} TL eşiğin ({_MIN_PRICE_DELTA} TL) altında."
            )
        else:
            update_result = await _tool_update_platform_price(
                integration, ctx.external_id, float(target), f"strategy:{ctx.strategy.value}"
            )
            tool_calls.append({
                "tool": "update_platform_price",
                "args": {"new_price": float(target), "reason": f"strategy:{ctx.strategy.value}"},
                "result": update_result,
            })

            new_price = target
            if hit_floor:
                decision = PricingDecision.FLOOR_HIT
                reasoning = (
                    f"Rakip baskısı floor'u tetikledi: {ctx.current_price} → {new_price} TL "
                    f"(floor={floor_price})."
                )
            else:
                decision = PricingDecision.PRICE_UPDATED
                reasoning = (
                    f"Strateji {ctx.strategy.value}: {ctx.current_price} → {new_price} TL "
                    f"({len(competitors)} rakip, floor {floor_price} TL)."
                )

        return PricingResult(
            decision=decision,
            old_price=ctx.current_price,
            new_price=new_price,
            reasoning=reasoning,
            tool_calls=tool_calls,
            duration_ms=int((time.monotonic() - start) * 1000),
        )
