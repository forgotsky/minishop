"""Initial schema — all tables as defined in models.py

This migration represents the full current model state.
On first Alembic deployment, it gets 'stamped' (marked as applied
without running) because the database already has these tables.
New migrations build on top of this as the base revision.

Revision ID: 001
Revises: None
Create Date: 2026-06-08
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("openid", sa.String(), unique=True, index=True, nullable=False),
        sa.Column("nickname", sa.String(), nullable=True),
        sa.Column("avatar", sa.String(), nullable=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- addresses ---
    op.create_table(
        "addresses",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("phone", sa.String(), nullable=False),
        sa.Column("province", sa.String(), nullable=False),
        sa.Column("city", sa.String(), nullable=False),
        sa.Column("district", sa.String(), nullable=False),
        sa.Column("street", sa.String(), nullable=False),
        sa.Column("zip_code", sa.String(), nullable=True),
        sa.Column("is_default", sa.Boolean(), default=False),
    )

    # --- products ---
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("name_zh", sa.String(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("description_zh", sa.Text(), nullable=True),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("image_url", sa.String(), nullable=True),
        sa.Column("images", sa.String(), nullable=True),
        sa.Column("stock", sa.Integer(), default=0),
        sa.Column("category", sa.String(), nullable=False, index=True),
        sa.Column("is_on_sale", sa.Boolean(), default=True),
        sa.Column("sales_count", sa.Integer(), default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # --- cart_items ---
    op.create_table(
        "cart_items",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, default=1),
    )

    # --- orders ---
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("order_no", sa.String(), unique=True, index=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("address_id", sa.Integer(), sa.ForeignKey("addresses.id"), nullable=True),
        sa.Column("address_snapshot", sa.String(), nullable=True),
        sa.Column("total_amount", sa.Float(), nullable=False, default=0),
        sa.Column("discount_amount", sa.Float(), nullable=False, default=0),
        sa.Column("delivery_fee", sa.Float(), nullable=False, default=0),
        sa.Column("payment_amount", sa.Float(), nullable=False, default=0),
        sa.Column("status", sa.Enum("pending","paid","shipped","delivered","completed","cancelled", name="orderstatus"), default="pending", nullable=False),
        sa.Column("payment_method", sa.String(), nullable=True),
        sa.Column("remark", sa.String(), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("shipped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("tracking_number", sa.String(50), nullable=True),
        sa.Column("tracking_company", sa.String(50), nullable=True),
        sa.Column("transaction_id", sa.String(64), nullable=True),
        sa.Column("prepay_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- order_items ---
    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("product_name", sa.String(), nullable=False),
        sa.Column("product_image", sa.String(), nullable=True),
        sa.Column("product_price", sa.Float(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
    )

    # --- coupon_templates ---
    op.create_table(
        "coupon_templates",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("type", sa.Enum("full_reduction","discount", name="coupontype"), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False, default=0),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("total_count", sa.Integer(), nullable=False, default=0),
        sa.Column("used_count", sa.Integer(), nullable=False, default=0),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- user_coupons ---
    op.create_table(
        "user_coupons",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("coupon_template_id", sa.Integer(), sa.ForeignKey("coupon_templates.id"), nullable=False),
        sa.Column("status", sa.Enum("unused","used","expired", name="couponstatus"), default="unused", nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("user_coupons")
    op.drop_table("coupon_templates")
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("cart_items")
    op.drop_table("products")
    op.drop_table("addresses")
    op.drop_table("users")
