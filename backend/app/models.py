from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum as SAEnum,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .db import Base
import enum


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CouponType(str, enum.Enum):
    FULL_REDUCTION = "full_reduction"  # 满减
    DISCOUNT = "discount"              # 折扣


class CouponStatus(str, enum.Enum):
    UNUSED = "unused"
    USED = "used"
    EXPIRED = "expired"


# --- User ---
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    openid = Column(String, unique=True, index=True, nullable=False)
    nickname = Column(String, nullable=True)
    avatar = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, server_default='true', nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    addresses = relationship("Address", back_populates="user", cascade="all, delete-orphan")
    cart_items = relationship("CartItem", back_populates="user", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")
    coupons = relationship("UserCoupon", back_populates="user", cascade="all, delete-orphan")


# --- Address ---
class Address(Base):
    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    full_name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    province = Column(String, nullable=False)
    city = Column(String, nullable=False)
    district = Column(String, nullable=False)
    street = Column(String, nullable=False)
    zip_code = Column(String, nullable=True)
    is_default = Column(Boolean, default=False)

    user = relationship("User", back_populates="addresses")


# --- Product ---
class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)              # English name
    name_zh = Column(String, nullable=True)            # Chinese name
    description = Column(Text, nullable=True)           # English description
    description_zh = Column(Text, nullable=True)        # Chinese description
    price = Column(Float, nullable=False)
    image_url = Column(String, nullable=True)
    images = Column(String, nullable=True)  # comma-separated URLs
    stock = Column(Integer, default=0)
    category = Column(String, nullable=False, index=True)
    is_on_sale = Column(Boolean, default=True)
    sales_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# --- CartItem ---
class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)

    user = relationship("User", back_populates="cart_items")
    product = relationship("Product")


# --- Order ---
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_no = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    address_id = Column(Integer, ForeignKey("addresses.id"), nullable=True)
    address_snapshot = Column(String, nullable=True)  # JSON snapshot of address at order time
    total_amount = Column(Float, nullable=False, default=0)
    discount_amount = Column(Float, nullable=False, default=0)
    delivery_fee = Column(Float, nullable=False, default=0)
    payment_amount = Column(Float, nullable=False, default=0)
    status = Column(SAEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    payment_method = Column(String, nullable=True)
    remark = Column(String, nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    shipped_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancel_reason = Column(Text, nullable=True)
    tracking_number = Column(String(50), nullable=True)
    tracking_company = Column(String(50), nullable=True)
    transaction_id = Column(String(64), nullable=True)   # 微信支付交易单号
    prepay_id = Column(String(64), nullable=True)        # 微信支付预支付ID
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


# --- OrderItem ---
class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, nullable=False)
    product_name = Column(String, nullable=False)
    product_image = Column(String, nullable=True)
    product_price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)

    order = relationship("Order", back_populates="items")


# --- CouponTemplate ---
class CouponTemplate(Base):
    __tablename__ = "coupon_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    type = Column(SAEnum(CouponType), nullable=False)
    threshold = Column(Float, nullable=False, default=0)  # 满减阈值金额
    value = Column(Float, nullable=False)  # 满减：减多少元；折扣：百分比(85=八五折)
    total_count = Column(Integer, nullable=False, default=0)
    used_count = Column(Integer, nullable=False, default=0)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# --- UserCoupon ---
class UserCoupon(Base):
    __tablename__ = "user_coupons"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    coupon_template_id = Column(Integer, ForeignKey("coupon_templates.id"), nullable=False)
    status = Column(SAEnum(CouponStatus), default=CouponStatus.UNUSED, nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="coupons")
    template = relationship("CouponTemplate")
