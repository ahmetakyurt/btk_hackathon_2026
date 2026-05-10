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

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agents", tags=["agents"])

# ─── In-memory SSE broadcast ─────────────────────────────────────────────────

# Keyed by user_id — each user only receives their own product events.
_subscribers: dict[int, list[asyncio.Queue[dict[str, Any]]]] = {}

_SSE_QUEUE_MAX = 100
_SSE_KEEPALIVE_SECS = 25.0


def _default_serializer(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


async def broadcast_log(log_data: dict[str, Any], *, user_id: int) -> None:
    """Push a pricing log event to all SSE clients subscribed under user_id.

    Called from the manual trigger endpoint and the CompetitorWatcher.
    Dead (full) queues are silently dropped.
    """
    queues = _subscribers.get(user_id, [])
    dead: list[asyncio.Queue[dict[str, Any]]] = []
    for q in queues:
        try:
            q.put_nowait(log_data)
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        try:
            queues.remove(q)
        except ValueError:
            pass
    if dead:
        logger.debug("SSE: dropped %d full subscriber queue(s) for user %d", len(dead), user_id)


# ─── Endpoint ─────────────────────────────────────────────────────────────────

@router.get("/logs/stream")
async def log_stream(user_id: int = Query(...)) -> StreamingResponse:
    """Server-Sent Events stream scoped to the authenticated user.

    user_id is passed as a query param by the frontend (read from the NextAuth
    session server-side). EventSource cannot send custom headers, so the query
    param is the only practical option for browser-based SSE.
    """
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=_SSE_QUEUE_MAX)
    _subscribers.setdefault(user_id, []).append(queue)

    async def generate() -> AsyncIterator[str]:
        yield 'data: {"type":"connected"}\n\n'
        try:
            while True:
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=_SSE_KEEPALIVE_SECS)
                    yield f"data: {json.dumps(data, default=_default_serializer)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            user_queues = _subscribers.get(user_id, [])
            try:
                user_queues.remove(queue)
            except ValueError:
                pass
            if not user_queues:
                _subscribers.pop(user_id, None)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/logs/subscribers")
async def subscriber_count() -> dict[str, int]:
    """Dev/debug endpoint — returns number of active SSE connections."""
    total = sum(len(qs) for qs in _subscribers.values())
    return {"active_connections": total}
