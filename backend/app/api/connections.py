"""Platform Connections API — connect/disconnect marketplace accounts."""

from __future__ import annotations

import asyncio
from datetime import datetime, UTC

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user_id
from app.db.models import Platform, PlatformConnection
from app.db.session import get_session

router = APIRouter(prefix="/api/connections", tags=["connections"])


class ConnectionIn(BaseModel):
    platform_code: str
    seller_id: str | None = None
    api_key: str | None = None


class ConnectionOut(BaseModel):
    id: int
    platform_id: int
    platform_code: str
    platform_name: str
    seller_id: str | None
    status: str
    connected_at: datetime


class TestResult(BaseModel):
    ok: bool
    store_name: str


async def _get_platform(session: AsyncSession, code: str) -> Platform:
    platform = await session.scalar(
        select(Platform).where(Platform.code == code, Platform.is_active.is_(True))
    )
    if platform is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Platform '{code}' not found or inactive")
    return platform


def _to_out(conn: PlatformConnection) -> ConnectionOut:
    return ConnectionOut(
        id=conn.id,
        platform_id=conn.platform_id,
        platform_code=conn.platform.code,
        platform_name=conn.platform.display_name,
        seller_id=conn.seller_id,
        status=conn.status,
        connected_at=conn.connected_at,
    )


@router.get("", response_model=list[ConnectionOut])
async def list_connections(
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> list[ConnectionOut]:
    rows = await session.scalars(
        select(PlatformConnection)
        .where(PlatformConnection.user_id == user_id)
        .options(selectinload(PlatformConnection.platform))
        .order_by(PlatformConnection.platform_id)
    )
    return [_to_out(c) for c in rows.all()]


@router.post("", response_model=ConnectionOut, status_code=status.HTTP_201_CREATED)
async def connect_platform(
    body: ConnectionIn,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> ConnectionOut:
    platform = await _get_platform(session, body.platform_code)

    existing = await session.scalar(
        select(PlatformConnection).where(
            PlatformConnection.user_id == user_id,
            PlatformConnection.platform_id == platform.id,
        )
    )
    if existing is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Already connected to '{platform.display_name}'. Disconnect first to re-connect.",
        )

    conn = PlatformConnection(
        user_id=user_id,
        platform_id=platform.id,
        seller_id=body.seller_id or None,
        api_key=body.api_key or None,
        status="connected",
        connected_at=datetime.now(UTC).replace(tzinfo=None),
    )
    session.add(conn)
    await session.commit()
    await session.refresh(conn)
    # load relationship
    await session.refresh(conn, attribute_names=["platform"])
    return _to_out(conn)


@router.delete("/{platform_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_platform(
    platform_id: int,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> None:
    conn = await session.scalar(
        select(PlatformConnection).where(
            PlatformConnection.user_id == user_id,
            PlatformConnection.platform_id == platform_id,
        )
    )
    if conn is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Connection not found")
    await session.delete(conn)
    await session.commit()


@router.post("/{platform_id}/test", response_model=TestResult)
async def test_connection(
    platform_id: int,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> TestResult:
    conn = await session.scalar(
        select(PlatformConnection)
        .where(
            PlatformConnection.user_id == user_id,
            PlatformConnection.platform_id == platform_id,
        )
        .join(Platform)
    )
    if conn is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Connection not found")

    await session.refresh(conn, attribute_names=["platform"])
    await asyncio.sleep(0.2)  # simulate network round-trip
    seller = conn.seller_id or "merchant"
    store_name = f"{seller}'s {conn.platform.display_name} Store"
    return TestResult(ok=True, store_name=store_name)
