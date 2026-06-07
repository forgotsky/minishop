"""Fix missing columns on existing tables

Add columns that exist in models.py but are missing from the
production database (created before these columns were added to the model):
  - users.is_active
  - products.name_zh, products.description_zh
  - orders.remark, cancel_reason, tracking_number, tracking_company,
    transaction_id, prepay_id

All use IF NOT EXISTS — safe to re-run.

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
    # --- users ---
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true"
    )
    # --- products ---
    op.execute(
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS name_zh VARCHAR"
    )
    op.execute(
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS description_zh TEXT"
    )
    # --- orders ---
    op.execute(
        "ALTER TABLE orders ADD COLUMN IF NOT EXISTS remark VARCHAR"
    )
    op.execute(
        "ALTER TABLE orders ADD COLUMN IF NOT EXISTS cancel_reason TEXT"
    )
    op.execute(
        "ALTER TABLE orders ADD COLUMN IF NOT EXISTS tracking_number VARCHAR(50)"
    )
    op.execute(
        "ALTER TABLE orders ADD COLUMN IF NOT EXISTS tracking_company VARCHAR(50)"
    )
    op.execute(
        "ALTER TABLE orders ADD COLUMN IF NOT EXISTS transaction_id VARCHAR(64)"
    )
    op.execute(
        "ALTER TABLE orders ADD COLUMN IF NOT EXISTS prepay_id VARCHAR(64)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS is_active")
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS name_zh")
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS description_zh")
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS remark")
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS cancel_reason")
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS tracking_number")
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS tracking_company")
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS transaction_id")
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS prepay_id")
