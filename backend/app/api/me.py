from __future__ import annotations

from datetime import datetime, timedelta, UTC

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user_id
from app.core.security import hash_password, verify_password
from app.db.models import PricingAgentLog, Product, ProductPlatformStatus, User
from app.db.session import get_session

router = APIRouter(prefix="/api/me", tags=["me"])


class ProfileOut(BaseModel):
    id: int
    email: str
    full_name: str | None
    phone: str | None
    store_name: str | None
    vacation_mode: bool
    created_at: datetime
    total_products: int
    active_listings: int
    buybox_count: int
    price_updates_24h: int


class ProfileUpdateIn(BaseModel):
    full_name: str | None = Field(default=None, max_length=128)
    phone: str | None = Field(default=None, max_length=32)
    store_name: str | None = Field(default=None, max_length=128)


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class VacationModeIn(BaseModel):
    vacation_mode: bool


async def _build_profile(user: User, user_id: int, session: AsyncSession) -> ProfileOut:
    total_products = (
        await session.execute(
            select(func.count()).select_from(Product).where(Product.user_id == user_id)
        )
    ).scalar_one()

    active_listings = (
        await session.execute(
            select(func.count())
            .select_from(ProductPlatformStatus)
            .join(Product, ProductPlatformStatus.product_id == Product.id)
            .where(Product.user_id == user_id, ProductPlatformStatus.status == "active")
        )
    ).scalar_one()

    buybox_count = (
        await session.execute(
            select(func.count())
            .select_from(ProductPlatformStatus)
            .join(Product, ProductPlatformStatus.product_id == Product.id)
            .where(Product.user_id == user_id, ProductPlatformStatus.has_buybox.is_(True))
        )
    ).scalar_one()

    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=24)
    price_updates_24h = (
        await session.execute(
            select(func.count())
            .select_from(PricingAgentLog)
            .join(ProductPlatformStatus, PricingAgentLog.product_platform_id == ProductPlatformStatus.id)
            .join(Product, ProductPlatformStatus.product_id == Product.id)
            .where(
                Product.user_id == user_id,
                PricingAgentLog.decision == "price_updated",
                PricingAgentLog.created_at >= cutoff,
            )
        )
    ).scalar_one()

    return ProfileOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        store_name=user.store_name,
        vacation_mode=user.vacation_mode,
        created_at=user.created_at,
        total_products=total_products,
        active_listings=active_listings,
        buybox_count=buybox_count,
        price_updates_24h=price_updates_24h,
    )


@router.get("", response_model=ProfileOut)
async def get_profile(
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> ProfileOut:
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return await _build_profile(user, user_id, session)


@router.patch("", response_model=ProfileOut)
async def update_profile(
    payload: ProfileUpdateIn,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> ProfileOut:
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if payload.full_name is not None:
        user.full_name = payload.full_name or None
    if payload.phone is not None:
        user.phone = payload.phone or None
    if payload.store_name is not None:
        user.store_name = payload.store_name or None
    await session.commit()
    await session.refresh(user)
    return await _build_profile(user, user_id, session)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: ChangePasswordIn,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> None:
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None or not verify_password(payload.current_password, user.hashed_pw):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mevcut şifre hatalı")
    user.hashed_pw = hash_password(payload.new_password)
    await session.commit()


@router.patch("/vacation-mode", response_model=ProfileOut)
async def set_vacation_mode(
    payload: VacationModeIn,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> ProfileOut:
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    user.vacation_mode = payload.vacation_mode
    await session.commit()
    await session.refresh(user)
    return await _build_profile(user, user_id, session)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def close_account(
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> None:
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    user.is_active = False
    await session.commit()
