from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, Uuid


class Base(DeclarativeBase):
    pass


json_type = JSON().with_variant(SQLiteJSON(), "sqlite")


class CustomerRow(Base):
    __tablename__ = "customers"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    keycloak_sub: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SellerRow(Base):
    __tablename__ = "sellers"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    memberships: Mapped[list["SellerMembershipRow"]] = relationship(
        back_populates="seller",
        cascade="all, delete-orphan",
    )
    products: Mapped[list["ProductRow"]] = relationship(back_populates="seller")


class SellerMembershipRow(Base):
    __tablename__ = "seller_memberships"

    seller_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sellers.id", ondelete="CASCADE"),
        primary_key=True,
    )
    customer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    seller: Mapped[SellerRow] = relationship(back_populates="memberships")


class ProductRow(Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("seller_id", "sku", name="uq_products_seller_sku"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    seller_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sellers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    seller: Mapped[SellerRow] = relationship(back_populates="products")


class OrderRow(Base):
    __tablename__ = "orders"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    customer_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    items: Mapped[list["OrderItemRow"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
    )


class OrderItemRow(Base):
    __tablename__ = "order_items"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    order: Mapped[OrderRow] = relationship(back_populates="items")


class PaymentRow(Base):
    __tablename__ = "payments"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DeliveryRow(Base):
    __tablename__ = "deliveries"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OutboxEventRow(Base):
    __tablename__ = "outbox_events"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    event_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, unique=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    topic: Mapped[str] = mapped_column(String(128), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(json_type, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProcessedEventRow(Base):
    __tablename__ = "processed_events"

    event_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
