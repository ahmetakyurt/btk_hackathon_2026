"""Unit tests for PricingAgent — deterministic path and mocked Gemini path."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.pricing_agent import (
    PricingAgent,
    PricingContext,
    PricingDecision,
    PricingStrategy,
    _apply_strategy,
    _tool_calculate_floor_price,
)
from app.integrations.schemas import CompetitorEntry, CompetitorSnapshot


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _ctx(
    strategy: PricingStrategy = PricingStrategy.BUYBOX,
    current_price: Decimal = Decimal("260"),
    floor_price: Decimal = Decimal("200"),
    ceiling_price: Decimal = Decimal("400"),
) -> PricingContext:
    return PricingContext(
        product_platform_id=1,
        sku="SKU-TEST",
        platform_code="trendyol",
        strategy=strategy,
        current_price=current_price,
        floor_price=floor_price,
        ceiling_price=ceiling_price,
        base_cost=Decimal("120"),
        shipping_cost=Decimal("20"),
        commission_rate=Decimal("0.20"),
        external_id="TY-00000001",
    )


def _mock_integration(competitor_prices: list[float], update_returns: bool = True) -> Any:
    snapshot = CompetitorSnapshot(
        external_id="TY-00000001",
        platform_code="trendyol",
        competitors=[
            CompetitorEntry(seller_name=f"Seller{i}", price=Decimal(str(p)))
            for i, p in enumerate(competitor_prices)
        ],
        fetched_at=datetime.now(UTC),
        own_has_buybox=False,
        own_price=None,
    )
    integration = AsyncMock()
    integration.get_competitor_snapshot = AsyncMock(return_value=snapshot)
    integration.update_price = AsyncMock(return_value=update_returns)
    return integration


# ─── _apply_strategy ─────────────────────────────────────────────────────────

class TestApplyStrategy:
    def test_buybox_undercuts_lowest_competitor(self) -> None:
        result = _apply_strategy(
            PricingStrategy.BUYBOX,
            current_price=Decimal("260"),
            floor_price=Decimal("200"),
            ceiling_price=Decimal("400"),
            competitors=[{"price": 250.0}, {"price": 255.0}],
        )
        assert result == Decimal("249.50")  # min(250,255) - 0.50

    def test_buybox_clamps_to_floor(self) -> None:
        # competitor at 200, undercut → 199.50 < floor 200 → clamped to 200
        result = _apply_strategy(
            PricingStrategy.BUYBOX,
            current_price=Decimal("210"),
            floor_price=Decimal("200"),
            ceiling_price=Decimal("400"),
            competitors=[{"price": 200.0}],
        )
        assert result == Decimal("200.00")

    def test_logistics_balance_uses_average(self) -> None:
        result = _apply_strategy(
            PricingStrategy.LOGISTICS_BALANCE,
            current_price=Decimal("115"),
            floor_price=Decimal("80"),
            ceiling_price=Decimal("200"),
            competitors=[{"price": 100.0}, {"price": 120.0}],
        )
        assert result == Decimal("110.00")  # avg = 110

    def test_profit_max_uses_ceiling_when_no_competitors(self) -> None:
        result = _apply_strategy(
            PricingStrategy.PROFIT_MAX,
            current_price=Decimal("100"),
            floor_price=Decimal("80"),
            ceiling_price=Decimal("200"),
            competitors=[],
        )
        assert result == Decimal("200.00")

    def test_profit_max_undercuts_by_5pct(self) -> None:
        result = _apply_strategy(
            PricingStrategy.PROFIT_MAX,
            current_price=Decimal("100"),
            floor_price=Decimal("80"),
            ceiling_price=Decimal("200"),
            competitors=[{"price": 100.0}],
        )
        assert result == Decimal("95.00")  # 100 * 0.95

    def test_no_competitors_buybox_keeps_current(self) -> None:
        result = _apply_strategy(
            PricingStrategy.BUYBOX,
            current_price=Decimal("200"),
            floor_price=Decimal("150"),
            ceiling_price=Decimal("400"),
            competitors=[],
        )
        assert result == Decimal("200.00")


# ─── _tool_calculate_floor_price ─────────────────────────────────────────────

class TestToolCalculateFloorPrice:
    def test_trendyol_20pct(self) -> None:
        result = _tool_calculate_floor_price(120.0, 20.0, 0.20, 0.05)
        assert result["floor_price"] == pytest.approx(186.67, abs=0.01)

    def test_own_site_2pct(self) -> None:
        # (120+20) / (1 - 0.02 - 0.05) = 140 / 0.93 ≈ 150.54
        result = _tool_calculate_floor_price(120.0, 20.0, 0.02, 0.05)
        assert result["floor_price"] == pytest.approx(150.54, abs=0.01)

    def test_degenerate_case(self) -> None:
        result = _tool_calculate_floor_price(100.0, 0.0, 0.95, 0.10)
        assert result["floor_price"] == pytest.approx(200.0, abs=0.01)


# ─── PricingAgent — deterministic path ───────────────────────────────────────

class TestPricingAgentDeterministic:
    @pytest.mark.asyncio
    async def test_buybox_price_updated(self) -> None:
        agent = PricingAgent(api_key="")
        ctx = _ctx(strategy=PricingStrategy.BUYBOX, current_price=Decimal("260"))
        integration = _mock_integration([250.0, 255.0])  # target = 249.50
        result = await agent.run(ctx, integration)
        assert result.decision == PricingDecision.PRICE_UPDATED
        assert result.new_price == Decimal("249.50")
        assert result.old_price == Decimal("260")

    @pytest.mark.asyncio
    async def test_floor_hit_when_competitors_below_floor(self) -> None:
        # competitor at 200 → undercut = 199.50 < floor 200 → target clamped to 200
        agent = PricingAgent(api_key="")
        ctx = _ctx(strategy=PricingStrategy.BUYBOX, current_price=Decimal("210"))
        integration = _mock_integration([200.0])
        result = await agent.run(ctx, integration)
        assert result.decision == PricingDecision.FLOOR_HIT
        assert result.new_price == Decimal("200.00")

    @pytest.mark.asyncio
    async def test_no_action_when_delta_too_small(self) -> None:
        # current=249.70, competitor=250 → target=249.50, delta=0.20 < 0.50
        agent = PricingAgent(api_key="")
        ctx = _ctx(strategy=PricingStrategy.BUYBOX, current_price=Decimal("249.70"))
        integration = _mock_integration([250.0])
        result = await agent.run(ctx, integration)
        assert result.decision == PricingDecision.NO_ACTION
        assert result.new_price == Decimal("249.70")
        integration.update_price.assert_not_called()

    @pytest.mark.asyncio
    async def test_profit_max_no_competitors_goes_to_ceiling(self) -> None:
        agent = PricingAgent(api_key="")
        ctx = _ctx(
            strategy=PricingStrategy.PROFIT_MAX,
            current_price=Decimal("200"),
            ceiling_price=Decimal("400"),
        )
        integration = _mock_integration([])  # no competitors → ceiling
        result = await agent.run(ctx, integration)
        assert result.decision == PricingDecision.PRICE_UPDATED
        assert result.new_price == Decimal("400.00")

    @pytest.mark.asyncio
    async def test_logistics_balance_tracks_average(self) -> None:
        agent = PricingAgent(api_key="")
        ctx = _ctx(
            strategy=PricingStrategy.LOGISTICS_BALANCE,
            current_price=Decimal("300"),
            floor_price=Decimal("150"),
            ceiling_price=Decimal("500"),
        )
        integration = _mock_integration([240.0, 260.0])  # avg = 250
        result = await agent.run(ctx, integration)
        assert result.decision == PricingDecision.PRICE_UPDATED
        assert result.new_price == Decimal("250.00")

    @pytest.mark.asyncio
    async def test_tool_calls_logged_in_result(self) -> None:
        agent = PricingAgent(api_key="")
        ctx = _ctx(current_price=Decimal("260"))
        integration = _mock_integration([250.0])
        result = await agent.run(ctx, integration)
        tool_names = [t["tool"] for t in result.tool_calls]
        assert "get_competitor_prices" in tool_names
        assert "calculate_floor_price" in tool_names
        assert "update_platform_price" in tool_names


# ─── PricingAgent — mocked Gemini path ───────────────────────────────────────

class TestPricingAgentMockedGemini:
    """Verify the Function Calling loop parses tool calls and dispatches correctly."""

    def _build_mock_client(self, turn_responses: list[list[tuple[str, dict]]]) -> Any:
        """
        turn_responses: list of turns; each turn is a list of (tool_name, args) pairs.
        Last turn should be empty [] to signal text-only finish.
        """
        call_index = 0

        def _make_response(tool_calls: list[tuple[str, dict]]) -> MagicMock:
            parts = []
            for name, args in tool_calls:
                fc = MagicMock()
                fc.name = name
                fc.args = args
                part = MagicMock()
                part.function_call = fc
                parts.append(part)

            if not tool_calls:
                # text-only part — no function_call attribute to trigger dispatch
                part = MagicMock(spec=[])  # spec=[] means no attributes
                parts.append(part)

            content = MagicMock()
            content.parts = parts

            candidate = MagicMock()
            candidate.content = content

            response = MagicMock()
            response.candidates = [candidate]
            return response

        responses = [_make_response(turn) for turn in turn_responses]
        client = MagicMock()
        client.models.generate_content = MagicMock(side_effect=responses)
        return client

    @pytest.mark.asyncio
    async def test_gemini_no_action_via_log_decision(self) -> None:
        # Turn 1: log_decision(decision="no_action") → finish
        mock_client = self._build_mock_client([
            [("log_decision", {"decision": "no_action", "reasoning": "Price already optimal."})],
            [],  # text finish
        ])
        agent = PricingAgent(api_key="fake-key", client=mock_client)
        ctx = _ctx(current_price=Decimal("260"))
        integration = _mock_integration([])

        result = await agent.run(ctx, integration)

        assert result.decision == PricingDecision.NO_ACTION
        assert "optimal" in result.reasoning
        assert result.new_price == Decimal("260")

    @pytest.mark.asyncio
    async def test_gemini_price_updated_via_update_tool(self) -> None:
        # Turn 1: update_platform_price(new_price=249.50) + log_decision(price_updated)
        mock_client = self._build_mock_client([
            [
                ("update_platform_price", {"new_price": 249.50, "reason": "buybox strategy"}),
                ("log_decision", {"decision": "price_updated", "reasoning": "Undercut competitor."}),
            ],
            [],
        ])
        agent = PricingAgent(api_key="fake-key", client=mock_client)
        ctx = _ctx(current_price=Decimal("260"))
        integration = _mock_integration([250.0])

        result = await agent.run(ctx, integration)

        assert result.decision == PricingDecision.PRICE_UPDATED
        assert result.new_price == Decimal("249.50")
        integration.update_price.assert_awaited_once_with("TY-00000001", 249.50)
