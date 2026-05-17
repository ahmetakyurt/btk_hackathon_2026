"""Central factory for google-genai clients.

Supports two auth modes:
- Vertex AI Express Mode (API key on Vertex) — uses GCP free credit when USE_VERTEX_AI=true.
- AI Studio (default) — uses GEMINI_API_KEY directly.

Returns None when no credentials are configured; callers fall back to deterministic paths.
"""
from __future__ import annotations

from typing import Any

from app.config import get_settings


def build_genai_client(api_key: str | None = None) -> Any | None:
    """Return a configured genai.Client, or None if no auth available.

    api_key arg is only used in AI Studio mode; Vertex mode reads its own key from settings.
    """
    from google import genai

    settings = get_settings()

    if settings.use_vertex_ai and settings.vertex_api_key and settings.gcp_project_id:
        return genai.Client(
            vertexai=True,
            project=settings.gcp_project_id,
            location=settings.gcp_location,
            http_options={"headers": {"X-Goog-Api-Key": settings.vertex_api_key}},
        )

    effective_key = api_key or settings.gemini_api_key
    if not effective_key:
        return None
    return genai.Client(api_key=effective_key)


def gemini_available() -> bool:
    settings = get_settings()
    if settings.use_vertex_ai:
        return bool(settings.vertex_api_key and settings.gcp_project_id)
    return bool(settings.gemini_api_key)


def vertex_configured() -> bool:
    """Vertex AI Express Mode is the active path."""
    settings = get_settings()
    return bool(settings.use_vertex_ai and settings.vertex_api_key and settings.gcp_project_id)
