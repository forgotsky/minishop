"""补全所有 Model 中数据库缺失的列

Covers ALL columns from models.py that may be missing.
Uses IF NOT EXISTS — safe to re-run.

Revision ID: 002
Revises: 001
Create Date: 2026-06-08
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ============================================================
    # users
    # ============================================================
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS nickname VARCHAR")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar VARCHAR")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true")

    # ============================================================
    # addresses
    # ============================================================
    op.execute("ALTER TABLE addresses ADD COLUMN IF NOT EXISTS zip_code VARCHAR")
    op.execute("ALTER TABLE addresses ADD COLUMN IF NOT EXISTS is_default BOOLEAN DEFAULT false")

    # ============================================================
    # products
    # ============================================================
    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS name_zh VARCHAR")
    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS description_zh TEXT")
    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS images VARCHAR")
    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS is_on_sale BOOLEAN DEFAULT true")
    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS sales_count INTEGER DEFAULT 0")
    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ")

    # ============================================================
    # orders
    # ============================================================
    op.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS address_snapshot VARCHAR")
    op.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS discount_amount DOUBLE PRECISION NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS delivery_fee DOUBLE PRECISION NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_method VARCHAR")
    op.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS remark VARCHAR")
    op.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS paid_at TIMESTAMPTZ")
    op.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS shipped_at TIMESTAMPTZ")
    op.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS delivered_at TIMESTAMPTZ")
    op.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMPTZ")
    op.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS cancel_reason TEXT")
    op.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS tracking_number VARCHAR(50)")
    op.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS tracking_company VARCHAR(50)")
    op.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS transaction_id VARCHAR(64)")
    op.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS prepay_id VARCHAR(64)")

    # ============================================================
    # coupon_templates
    # ============================================================
    op.execute("ALTER TABLE coupon_templates ADD COLUMN IF NOT EXISTS description VARCHAR")
    op.execute("ALTER TABLE coupon_templates ADD COLUMN IF NOT EXISTS total_count INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE coupon_templates ADD COLUMN IF NOT EXISTS used_count INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE coupon_templates ADD COLUMN IF NOT EXISTS threshold DOUBLE PRECISION NOT NULL DEFAULT 0")

    # ============================================================
    # user_coupons
    # ============================================================
    op.execute("ALTER TABLE user_coupons ADD COLUMN IF NOT EXISTS used_at TIMESTAMPTZ")


def downgrade() -> None:
    pass
