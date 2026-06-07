"""
⚠️ 数据库重置脚本 — 删除所有表并重新创建 + 导入种子数据
仅 dev 环境使用，prod 请用 Alembic 增量迁移

用法:
    python scripts/reset_db.py

会删除所有数据并重建，包括:
  - 完整 Model schema（所有列）
  - 8个商品（中英双语）
  - 3张优惠券
"""
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Must set env before importing app modules
os.environ.setdefault("RUN_MODE", "dev")
os.environ.setdefault("DATABASE_URL", os.getenv("DATABASE_URL", "sqlite:///./shop.db"))

from app.db import Base, engine, SessionLocal
from app.models import (
    User, Address, Product, CartItem,
    Order, OrderItem, CouponTemplate, UserCoupon,
)
from app.main import PRODUCT_SEED_DATA
from datetime import datetime, timezone


def reset():
    db = SessionLocal()
    try:
        print("Dropping all tables...")
        Base.metadata.drop_all(bind=engine)

        print("Creating all tables with current schema...")
        Base.metadata.create_all(bind=engine)

        print(f"Seeding {len(PRODUCT_SEED_DATA)} products...")
        for d in PRODUCT_SEED_DATA:
            db.add(Product(**d))
        db.commit()

        print("Seeding coupons...")
        now = datetime.now(timezone.utc)
        templates = [
            CouponTemplate(
                name="新用户满100减20", description="新用户首单专享",
                type="full_reduction", threshold=100.0, value=20.0,
                total_count=500, start_time=now,
                end_time=now.replace(year=now.year + 1),
            ),
            CouponTemplate(
                name="全场满200减30", description="全场通用",
                type="full_reduction", threshold=200.0, value=30.0,
                total_count=1000, start_time=now,
                end_time=now.replace(year=now.year + 1),
            ),
            CouponTemplate(
                name="电子产品9折券", description="电子产品专享",
                type="discount", threshold=0.0, value=90.0,
                total_count=300, start_time=now,
                end_time=now.replace(year=now.year + 1),
            ),
        ]
        for t in templates:
            db.add(t)
        db.commit()

        print("[OK] Database reset complete!")
        print(f"   Products: {db.query(Product).count()}")
        print(f"   Coupons:  {db.query(CouponTemplate).count()}")

    finally:
        db.close()


if __name__ == "__main__":
    confirm = input("This will DELETE ALL DATA. Type 'yes' to confirm: ")
    if confirm == "yes":
        reset()
    else:
        print("Cancelled.")
