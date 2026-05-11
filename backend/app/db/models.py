from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    type_annotation_map = {dict[str, Any]: JSON}


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_pw: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    store_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    vacation_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    products: Mapped[list[Product]] = relationship(back_populates="user")
    reset_tokens: Mapped[list[PasswordResetToken]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user: Mapped[User] = relationship(back_populates="reset_tokens")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    base_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    shipping_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    raw_specs: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    platform_statuses: Mapped[list[ProductPlatformStatus]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    user: Mapped[User | None] = relationship(back_populates="products")


class Platform(Base):
    __tablename__ = "platforms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    commission_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    base_url: Mapped[str] = mapped_column(String(255), nullable=False)
    pricing_strategy: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ProductPlatformStatus(Base):
    __tablename__ = "product_platform_status"
    __table_args__ = (UniqueConstraint("product_id", "platform_id", name="uq_product_platform"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    platform_id: Mapped[int] = mapped_column(
        ForeignKey("platforms.id", ondelete="CASCADE"), nullable=False
    )
    external_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    ai_generated_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ai_generated_desc: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    floor_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    ceiling_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    competitor_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    has_buybox: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")

    product: Mapped[Product] = relationship(back_populates="platform_statuses")
    platform: Mapped[Platform] = relationship()
    logs: Mapped[list[PricingAgentLog]] = relationship(
        back_populates="product_platform", cascade="all, delete-orphan"
    )


class PricingAgentLog(Base):
    __tablename__ = "pricing_agent_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_platform_id: Mapped[int] = mapped_column(
        ForeignKey("product_platform_status.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_name: Mapped[str] = mapped_column(String(32), nullable=False)
    trigger_event: Mapped[str] = mapped_column(String(32), nullable=False)
    input_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_calls: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    old_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    new_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), index=True
    )

    product_platform: Mapped[ProductPlatformStatus] = relationship(back_populates="logs")
