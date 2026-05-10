from __future__ import annotations

import logging
from datetime import datetime, timedelta, UTC

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import generate_reset_token, hash_password, verify_password
from app.db.models import PasswordResetToken, User
from app.db.session import get_session
from app.schemas.auth import (
    ForgotPasswordIn,
    GenericMessage,
    RegisterIn,
    ResetPasswordIn,
    UserOut,
    VerifyIn,
)
from app.services.email import send_password_reset_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterIn, session: AsyncSession = Depends(get_session)) -> UserOut:
    existing = (
        await session.execute(select(User).where(User.email == payload.email.lower()))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    user = User(
        email=payload.email.lower(),
        hashed_pw=hash_password(payload.password),
        full_name=payload.full_name,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return UserOut(id=user.id, email=user.email, full_name=user.full_name)


@router.post("/verify", response_model=UserOut)
async def verify(payload: VerifyIn, session: AsyncSession = Depends(get_session)) -> UserOut:
    """Credential check endpoint called by NextAuth's Credentials provider."""
    user = (
        await session.execute(select(User).where(User.email == payload.email.lower()))
    ).scalar_one_or_none()
    if user is None or not user.is_active or not verify_password(payload.password, user.hashed_pw):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    return UserOut(id=user.id, email=user.email, full_name=user.full_name)


@router.post("/forgot-password", response_model=GenericMessage)
async def forgot_password(
    payload: ForgotPasswordIn, session: AsyncSession = Depends(get_session)
) -> GenericMessage:
    """Always returns success to avoid email enumeration."""
    settings = get_settings()
    user = (
        await session.execute(select(User).where(User.email == payload.email.lower()))
    ).scalar_one_or_none()

    if user is not None and user.is_active:
        token = generate_reset_token()
        expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(
            seconds=settings.password_reset_ttl_seconds
        )
        session.add(
            PasswordResetToken(
                user_id=user.id, token=token, expires_at=expires_at, used=False
            )
        )
        await session.commit()

        reset_url = f"{settings.app_public_url.rstrip('/')}/auth/reset-password?token={token}"
        try:
            await send_password_reset_email(to=user.email, reset_url=reset_url)
        except Exception as exc:  # don't leak failure to caller
            logger.exception("Reset email send failed: %s", exc)

    return GenericMessage(ok=True, message="If that email exists, a reset link has been sent.")


@router.post("/reset-password", response_model=GenericMessage)
async def reset_password(
    payload: ResetPasswordIn, session: AsyncSession = Depends(get_session)
) -> GenericMessage:
    record = (
        await session.execute(
            select(PasswordResetToken).where(PasswordResetToken.token == payload.token)
        )
    ).scalar_one_or_none()

    if record is None or record.used or record.expires_at < datetime.now(UTC).replace(tzinfo=None):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired token")

    user = (await session.execute(select(User).where(User.id == record.user_id))).scalar_one()
    user.hashed_pw = hash_password(payload.new_password)
    record.used = True
    await session.commit()

    return GenericMessage(ok=True, message="Password updated.")
