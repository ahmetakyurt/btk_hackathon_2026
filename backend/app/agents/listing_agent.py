"""ListingAgent: generates platform-specific title, description, and keywords via Gemini.

Uses google-genai SDK with structured output (response_schema). If GEMINI_API_KEY is
empty the agent falls back to passthrough mode (raw product title/description), so the
rest of the system stays fully functional during local dev without a key.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ─── Output schema (one per platform) ────────────────────────────────────────

class PlatformListing(BaseModel):
    platform_code: str
    title: str
    description: str
    keywords: list[str]


# ─── Prompt templates ─────────────────────────────────────────────────────────

_SYSTEM_PROMPT = (
    "Sen bir e-ticaret uzmanısın. Sana verilen ürün bilgisinden, "
    "belirtilen platform için optimize edilmiş bir listeleme oluştur. "
    "Yanıtın YALNIZCA istenen JSON formatında olmalı, açıklama veya markdown ekleme."
)

_PLATFORM_INSTRUCTIONS: dict[str, str] = {
    "trendyol": (
        "Platform: Trendyol (Türkiye'nin en büyük pazaryeri).\n"
        "Stil: SEO odaklı. Başlıkta anahtar kelimeleri öne koy, karakter sınırı 100.\n"
        "Açıklama: Madde madde, emoji kullan, 200-300 karakter.\n"
        "Keywords: 5-8 adet, Türkçe, Trendyol aramasında öne çıkacak kelimeler."
    ),
    "amazon": (
        "Platform: Amazon (küresel, teknik alıcı kitlesi).\n"
        "Stil: Bullet-point odaklı, teknik özellikler öne çıkar, İngilizce UYGUN ancak Türkçe de kabul.\n"
        "Başlık: Marka + model + ana özellik formatında, 80-100 karakter.\n"
        "Açıklama: 3-5 bullet point (• sembolü ile), toplam 300-400 karakter.\n"
        "Keywords: 5-8 adet, teknik arama terimleri."
    ),
    "own_site": (
        "Platform: Satıcının kendi sitesi (marka odaklı, sadık müşteri kitlesi).\n"
        "Stil: Hikaye anlatımı, marka tonu, samimi dil.\n"
        "Başlık: Çekici, kısa, marka kimliği öne çıkar, max 70 karakter.\n"
        "Açıklama: 2-3 cümle, ürünün yaşam kalitesine katkısını anlat, 200-300 karakter.\n"
        "Keywords: 4-6 adet, marka ve lifestyle odaklı."
    ),
}


def _build_prompt(platform_code: str, product_info: dict[str, Any]) -> str:
    platform_instr = _PLATFORM_INSTRUCTIONS.get(
        platform_code,
        f"Platform: {platform_code}. Genel e-ticaret listeleme tonu kullan.",
    )
    specs_str = ", ".join(f"{k}: {v}" for k, v in (product_info.get("raw_specs") or {}).items())
    return (
        f"{platform_instr}\n\n"
        f"Ürün Bilgisi:\n"
        f"- SKU: {product_info['sku']}\n"
        f"- Ham Başlık: {product_info['title']}\n"
        f"- Kategori: {product_info.get('category', 'Belirtilmemiş')}\n"
        f"- Özellikler: {specs_str or 'Belirtilmemiş'}\n\n"
        f"Şu JSON formatında yanıt ver:\n"
        f'{{"platform_code": "{platform_code}", "title": "...", "description": "...", "keywords": ["..."]}}'
    )


# ─── Agent ────────────────────────────────────────────────────────────────────

class ListingAgent:
    """Generates platform-optimized listings using Gemini structured output.

    Pass `client` for testing (avoids real API calls); omit in production
    and the agent builds its own client from settings.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
        timeout: float = 15.0,
        *,
        client: Any = None,  # google.genai.Client injection for tests
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._client = client
        from app.core.gemini_client import vertex_configured
        self._available = bool(client) or bool(api_key) or vertex_configured()

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        from app.core.gemini_client import build_genai_client
        return build_genai_client(self._api_key)

    async def generate_listing(
        self, platform_code: str, product_info: dict[str, Any]
    ) -> PlatformListing:
        """Generate a platform-specific listing. Falls back to passthrough if no key."""
        if not self._available:
            logger.warning(
                "ListingAgent: no GEMINI_API_KEY — using passthrough for %s/%s",
                platform_code,
                product_info.get("sku"),
            )
            return self._passthrough(platform_code, product_info)

        prompt = _build_prompt(platform_code, product_info)

        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self._call_gemini, prompt, platform_code),
                timeout=self._timeout,
            )
        except TimeoutError:
            logger.error(
                "ListingAgent: Gemini timeout (%ss) for %s/%s — passthrough",
                self._timeout,
                platform_code,
                product_info.get("sku"),
            )
            return self._passthrough(platform_code, product_info)
        except Exception as exc:
            logger.error(
                "ListingAgent: Gemini error for %s/%s — passthrough: %s",
                platform_code,
                product_info.get("sku"),
                exc,
            )
            return self._passthrough(platform_code, product_info)

    def _call_gemini(self, prompt: str, platform_code: str) -> PlatformListing:
        from google import genai
        from google.genai import types

        client = self._get_client()
        response = client.models.generate_content(
            model=self._model,
            contents=[
                types.Content(
                    role="user",
                    parts=[types.Part(text=_SYSTEM_PROMPT + "\n\n" + prompt)],
                )
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=PlatformListing,
                temperature=0.7,
            ),
        )
        # The SDK populates .parsed when response_schema is a Pydantic model
        if hasattr(response, "parsed") and response.parsed is not None:
            result = response.parsed
            result.platform_code = platform_code  # ensure correct code
            return result
        # Fallback: parse text manually
        import json
        data = json.loads(response.text)
        data["platform_code"] = platform_code
        return PlatformListing(**data)

    @staticmethod
    def _passthrough(platform_code: str, product_info: dict[str, Any]) -> PlatformListing:
        return PlatformListing(
            platform_code=platform_code,
            title=product_info["title"],
            description=f"{product_info['title']} — {product_info.get('category', '')}".strip(" —"),
            keywords=[],
        )

    async def generate_all_platforms(
        self,
        platform_codes: list[str],
        product_info: dict[str, Any],
    ) -> dict[str, PlatformListing]:
        """Generate listings for all platforms concurrently."""
        tasks = [
            self.generate_listing(platform_code, product_info)
            for platform_code in platform_codes
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        output: dict[str, PlatformListing] = {}
        for platform_code, result in zip(platform_codes, results):
            if isinstance(result, Exception):
                logger.error(
                    "ListingAgent: failed for platform %s: %s", platform_code, result
                )
                output[platform_code] = ListingAgent._passthrough(platform_code, product_info)
            else:
                output[platform_code] = result  # type: ignore[assignment]
        return output
