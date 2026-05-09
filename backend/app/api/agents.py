"""Agents API — SSE live-log stream.

Single-process broadcast via module-level subscriber queues.
If the server ever moves to multi-worker, swap broadcast_log for Redis pub/sub.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from decimal import Decimal
from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agents", tags=["agents"])

# ─── In-memory SSE broadcast ─────────────────────────────────────────────────

_subscribers: list[asyncio.Queue[dict[str, Any]]] = []

_SSE_QUEUE_MAX = 100
_SSE_KEEPALIVE_SECS = 25.0


def _default_serializer(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


async def broadcast_log(log_data: dict[str, Any]) -> None:
    """Push a pricing log event to every connected SSE client.

    Called from both the manual trigger endpoint and the CompetitorWatcher.
    Dead (full) queues are silently dropped.
    """
    dead: list[asyncio.Queue[dict[str, Any]]] = []
    for q in _subscribers:
        try:
            q.put_nowait(log_data)
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        try:
            _subscribers.remove(q)
        except ValueError:
            pass
    if dead:
        logger.debug("SSE: dropped %d full subscriber queue(s)", len(dead))


# ─── Endpoint ─────────────────────────────────────────────────────────────────

@router.get("/logs/stream")
async def log_stream() -> StreamingResponse:
    """Server-Sent Events stream. Frontend connects once; new agent decisions push automatically."""

    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=_SSE_QUEUE_MAX)
    _subscribers.append(queue)

    async def generate() -> AsyncIterator[str]:
        # Initial connection confirmation
        yield 'data: {"type":"connected"}\n\n'
        try:
            while True:
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=_SSE_KEEPALIVE_SECS)
                    yield f"data: {json.dumps(data, default=_default_serializer)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"  # prevents proxy / browser disconnection
        finally:
            try:
                _subscribers.remove(queue)
            except ValueError:
                pass

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering if behind nginx
        },
    )


@router.get("/logs/subscribers")
async def subscriber_count() -> dict[str, int]:
    """Dev/debug endpoint — returns number of active SSE connections."""
    return {"active_connections": len(_subscribers)}
