"""Shared FastAPI dependencies."""
from __future__ import annotations

from fastapi import Header, HTTPException, status


async def get_current_user_id(
    x_user_id: int | None = Header(default=None, alias="X-User-Id"),
) -> int:
    """Extracts user id from the X-User-Id header set by the Next.js BFF.

    The Next.js layer reads the NextAuth session and forwards the user id;
    FastAPI itself does not validate the JWT. Endpoints requiring auth
    depend on this; public endpoints don't.
    """
    if x_user_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing X-User-Id header")
    return x_user_id


async def get_optional_user_id(
    x_user_id: int | None = Header(default=None, alias="X-User-Id"),
) -> int | None:
    """Same as above but returns None instead of raising — for endpoints
    that filter by user when present but stay open during the transition."""
    return x_user_id
