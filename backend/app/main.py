import os
import time
import json
import logging
from datetime import datetime, timezone
from typing import List, Optional

import httpx
from fastapi import FastAPI, HTTPException, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import and_

from .db import Base, engine, get_db
from .models import (
    User, Address, Product, CartItem, Order, OrderItem, OrderStatus,
    CouponTemplate, UserCoupon, CouponType, CouponStatus,
)
from .auth import create_access_token, require_user, get_current_user, RUN_MODE
from .log_config import setup_logging
from .wechat_pay import (
    create_jsapi_order,
    verify_notify_signature,
    decrypt_notify_resource,
    yuan_to_fen,
)

logger = logging.getLogger("shop.main")

app = FastAPI(title="WeChat Shop API", version="1.0.0")

allowed_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")
IMAGES_DIR = os.path.join(STATIC_DIR, "images")
if os.path.isdir(IMAGES_DIR):
    app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")

DELIVERY_FEE = 5.0


@app.on_event("startup")
def on_startup() -> None:
    setup_logging()
    logger.info("Shop API starting up...")
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    try:
        if db.query(Product).count() == 0:
            seed_products(db)
        if db.query(CouponTemplate).count() == 0:
            seed_coupons(db)
    finally:
        db.close()


# ============================================================
# Seed data
# ============================================================

PRODUCT_SEED_DATA = [
    {"name": "Wireless Headphones", "name_zh": "无线耳机", "description": "Premium noise-cancelling wireless headphones with 30hr battery life.", "description_zh": "高级降噪无线耳机，续航30小时", "price": 49.99, "image_url": "/images/headphones.jpg", "stock": 120, "category": "electronics", "sales_count": 56},
    {"name": "Smart Watch", "name_zh": "智能手表", "description": "Fitness tracker with heart rate monitor and GPS.", "description_zh": "心率监测运动手表，内置GPS定位", "price": 89.00, "image_url": "/images/watch.jpg", "stock": 80, "category": "electronics", "sales_count": 34},
    {"name": "Bluetooth Speaker", "name_zh": "蓝牙音箱", "description": "Portable waterproof speaker with deep bass.", "description_zh": "便携防水蓝牙音箱，重低音震撼", "price": 35.50, "image_url": "/images/speaker.jpg", "stock": 200, "category": "electronics", "sales_count": 78},
    {"name": "Backpack", "name_zh": "双肩背包", "description": "Lightweight travel backpack, water-resistant.", "description_zh": "轻量防水旅行背包，大容量收纳", "price": 28.75, "image_url": "/images/backpack.jpg", "stock": 150, "category": "accessories", "sales_count": 22},
    {"name": "Running Shoes", "name_zh": "跑步鞋", "description": "Breathable mesh running shoes with cushioned sole.", "description_zh": "透气网面跑步鞋，缓震鞋底舒适耐穿", "price": 64.20, "image_url": "/images/shoes.jpg", "stock": 60, "category": "sports", "sales_count": 91},
    {"name": "Power Bank", "name_zh": "充电宝", "description": "20000mAh fast-charging power bank with USB-C.", "description_zh": "20000毫安大容量快充充电宝，Type-C接口", "price": 22.99, "image_url": "/images/powerbank.jpg", "stock": 180, "category": "electronics", "sales_count": 110},
    {"name": "Coffee Mug", "name_zh": "咖啡杯", "description": "Insulated stainless steel mug, 500ml.", "description_zh": "不锈钢保温咖啡杯，容量500ml", "price": 15.99, "image_url": "/images/mug.jpg", "stock": 300, "category": "kitchen", "sales_count": 45},
    {"name": "Desk Lamp", "name_zh": "台灯", "description": "LED desk lamp with adjustable brightness.", "description_zh": "LED护眼台灯，亮度可调节", "price": 19.99, "image_url": "/images/lamp.jpg", "stock": 90, "category": "home", "sales_count": 67},
]


def seed_products(db: Session) -> None:
    """Seed products if empty, or update existing with Chinese translations."""
    count = db.query(Product).count()
    if count == 0:
        for d in PRODUCT_SEED_DATA:
            db.add(Product(**d))
        db.commit()
        logger.info(f"Seeded {len(PRODUCT_SEED_DATA)} products")
    else:
        # Update existing products with Chinese names if missing
        updated = 0
        for d in PRODUCT_SEED_DATA:
            p = db.query(Product).filter(Product.name == d["name"]).first()
            if p and (not p.name_zh or not p.description_zh):
                p.name_zh = d["name_zh"]
                p.description_zh = d["description_zh"]
                updated += 1
        if updated > 0:
            db.commit()
            logger.info(f"Updated {updated} products with Chinese translations")

# 品类名翻译映射
CATEGORY_ZH = {
    "electronics": "电子产品",
    "accessories": "服饰配件",
    "sports": "运动户外",
    "kitchen": "厨房用品",
    "home": "家居生活",
}
CATEGORY_EN = {
    "electronics": "Electronics",
    "accessories": "Accessories",
    "sports": "Sports",
    "kitchen": "Kitchen",
    "home": "Home",
}


def seed_coupons(db: Session) -> None:
    now = datetime.now(timezone.utc)
    templates = [
        CouponTemplate(name="新用户满100减20", description="新用户首单专享", type=CouponType.FULL_REDUCTION, threshold=100.0, value=20.0, total_count=500, start_time=now, end_time=now.replace(year=now.year + 1)),
        CouponTemplate(name="全场满200减30", description="全场通用", type=CouponType.FULL_REDUCTION, threshold=200.0, value=30.0, total_count=1000, start_time=now, end_time=now.replace(year=now.year + 1)),
        CouponTemplate(name="电子产品9折券", description="电子产品专享", type=CouponType.DISCOUNT, threshold=0.0, value=90.0, total_count=300, start_time=now, end_time=now.replace(year=now.year + 1)),
    ]
    for t in templates:
        db.add(t)
    db.commit()


# ============================================================
# Pydantic schemas
# ============================================================

class ProductOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    price: float
    image_url: Optional[str] = None
    images: Optional[str] = None
    stock: int
    category: str
    is_on_sale: bool
    sales_count: int

    class Config:
        from_attributes = True


class ProductListOut(BaseModel):
    products: List[ProductOut]
    total: int


class CartItemIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0, default=1)


class CartItemOut(BaseModel):
    id: int
    product_id: int
    product_name: str
    product_image: Optional[str] = None
    product_price: float
    quantity: int
    subtotal: float


class CartOut(BaseModel):
    items: List[CartItemOut]
    total: float


class AddressIn(BaseModel):
    full_name: str = Field(min_length=2)
    phone: str = Field(min_length=5)
    province: str
    city: str
    district: str
    street: str
    zip_code: Optional[str] = None
    is_default: bool = False


class AddressOut(BaseModel):
    id: int
    full_name: str
    phone: str
    province: str
    city: str
    district: str
    street: str
    zip_code: Optional[str] = None
    is_default: bool

    class Config:
        from_attributes = True


class OrderCreateIn(BaseModel):
    address_id: int
    coupon_id: Optional[int] = None
    payment_method: str = "wechat"
    remark: Optional[str] = None
    item_ids: Optional[List[int]] = None


class OrderItemOut(BaseModel):
    id: int
    product_id: int
    product_name: str
    product_image: Optional[str] = None
    product_price: float
    quantity: int

    class Config:
        from_attributes = True


class AddressSnapshot(BaseModel):
    full_name: str
    phone: str
    province: str
    city: str
    district: str
    street: str


class TrackingInfo(BaseModel):
    company: Optional[str] = None
    number: Optional[str] = None
    status: Optional[str] = None
    updated_at: Optional[str] = None
    traces: list = []


class OrderListItem(BaseModel):
    id: int
    order_no: str
    status: OrderStatus
    total_amount: float
    payment_amount: float
    created_at: Optional[str] = None
    items_count: int
    first_item: Optional[dict] = None


class OrderListOut(BaseModel):
    orders: List[OrderListItem]
    total: int
    page: int
    pages: int


class OrderDetailOut(BaseModel):
    id: int
    order_no: str
    status: OrderStatus
    created_at: Optional[str] = None
    paid_at: Optional[str] = None
    shipped_at: Optional[str] = None
    delivered_at: Optional[str] = None
    cancelled_at: Optional[str] = None
    cancel_reason: Optional[str] = None
    total_amount: float
    discount_amount: float
    delivery_fee: float
    payment_amount: float
    payment_method: Optional[str] = None
    remark: Optional[str] = None
    items: List[OrderItemOut]
    shipping_address: Optional[AddressSnapshot] = None
    tracking: Optional[TrackingInfo] = None


class OrderStatusUpdateIn(BaseModel):
    action: str  # "cancel" | "complete"


class OrderOut(BaseModel):
    id: int
    order_no: str
    total_amount: float
    discount_amount: float
    delivery_fee: float
    payment_amount: float
    status: OrderStatus
    payment_method: Optional[str] = None
    remark: Optional[str] = None
    created_at: Optional[str] = None
    items: List[OrderItemOut] = []

    class Config:
        from_attributes = True


class CouponOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    type: CouponType
    threshold: float
    value: float
    start_time: str
    end_time: str

    class Config:
        from_attributes = True


class UserCouponOut(BaseModel):
    id: int
    status: CouponStatus
    template: CouponOut

    class Config:
        from_attributes = True


class WxLoginIn(BaseModel):
    code: str
    nickname: Optional[str] = None
    avatar: Optional[str] = None


class LoginOut(BaseModel):
    token: str
    user_id: int
    nickname: Optional[str] = None


class UserProfileOut(BaseModel):
    id: int
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    phone: Optional[str] = None
    openid: str  # masked
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class UserProfileUpdate(BaseModel):
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    phone: Optional[str] = None


# ============================================================
# Helper functions
# ============================================================

def row2dict(obj):
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


def _mask_openid(openid: str) -> str:
    """Mask openid: show first 4 + last 4 chars, e.g. o7xK****abcd"""
    if len(openid) <= 8:
        return openid[:2] + "****" + openid[-2:]
    return openid[:4] + "****" + openid[-4:]


def get_lang(request: Request) -> str:
    """从请求头读取语言偏好，返回 'zh' 或 'en'"""
    lang = request.headers.get("accept-language", "en")
    return "zh" if lang.startswith("zh") else "en"


def localize_product(product, lang: str) -> dict:
    """根据语言返回商品数据的本地化版本"""
    if lang == "zh" and product.name_zh:
        return {
            "name": product.name_zh,
            "description": product.description_zh or product.description,
            "category": CATEGORY_ZH.get(product.category, product.category),
        }
    return {
        "name": product.name,
        "description": product.description,
        "category": CATEGORY_EN.get(product.category, product.category),
    }


# ============================================================
# Auth helpers
# ============================================================

WECHAT_CODE2SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session"


async def exchange_code_for_openid(code: str) -> str:
    """Exchange WeChat login code for openid.
    Dev mode: mock openid. Prod mode: call WeChat API.
    """
    from .auth import RUN_MODE, WECHAT_APPID, WECHAT_APP_SECRET

    if RUN_MODE == "dev":
        mock_openid = f"wx_{code}" if code else f"wx_dev_{int(time.time())}"
        logger.info(f"[DEV] Using mock openid: {mock_openid[:8]}...")
        return mock_openid

    # Production: call WeChat jscode2session
    params = {
        "appid": WECHAT_APPID,
        "secret": WECHAT_APP_SECRET,
        "js_code": code,
        "grant_type": "authorization_code",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(WECHAT_CODE2SESSION_URL, params=params)
            resp.raise_for_status()
            # Guard against non-JSON responses (e.g. gateway error pages)
            if not resp.headers.get("content-type", "").startswith("application/json"):
                logger.error("WeChat API returned non-JSON response")
                return None
            data = resp.json()
    except httpx.HTTPStatusError as e:
        logger.error("WeChat API HTTP error: status=%s", e.response.status_code)
        return None
    except (httpx.RequestError, httpx.TimeoutException) as e:
        logger.error("WeChat API unreachable: %s", e)
        return None

    if "errcode" in data and data["errcode"] != 0:
        # NEVER log full response — contains session_key
        logger.error("WeChat code2session error: errcode=%s errmsg=%s",
                     data.get("errcode"), data.get("errmsg", "unknown"))
        return None
    openid = data.get("openid")
    if not openid:
        logger.error("WeChat code2session response missing openid")
        return None
    return openid


# ============================================================
# Auth endpoints
# ============================================================

@app.post("/api/auth/login", response_model=LoginOut)
async def wx_login(payload: WxLoginIn, db: Session = Depends(get_db)):
    """
    WeChat mini-program login.
    In production, exchange code for openid via WeChat API.
    For dev: use code as a mock openid.
    """
    openid = await exchange_code_for_openid(payload.code)
    if not openid:
        raise HTTPException(status_code=400, detail="微信登录失败，请重试")

    user = db.query(User).filter(User.openid == openid).first()
    if not user:
        user = User(openid=openid, nickname=payload.nickname, avatar=payload.avatar)
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Re-activate soft-deleted account on re-login
        changed = False
        if not user.is_active:
            user.is_active = True
            changed = True
        if payload.nickname:
            user.nickname = payload.nickname
            changed = True
        if payload.avatar:
            user.avatar = payload.avatar
            changed = True
        if changed:
            db.commit()
            db.refresh(user)

    token = create_access_token(user.id)
    return LoginOut(token=token, user_id=user.id, nickname=user.nickname)


# ============================================================
# Product endpoints
# ============================================================

@app.get("/api/products", response_model=ProductListOut)
def list_products(
    request: Request,
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    lang = get_lang(request)
    q = db.query(Product).filter(Product.is_on_sale == True)
    if category:
        q = q.filter(Product.category == category)
    if search:
        if lang == "zh":
            q = q.filter(
                (Product.name.ilike(f"%{search}%")) |
                (Product.name_zh.ilike(f"%{search}%"))
            )
        else:
            q = q.filter(Product.name.ilike(f"%{search}%"))

    total = q.count()
    products = q.order_by(Product.sales_count.desc()).offset((page - 1) * page_size).limit(page_size).all()

    # Localize product names/categories
    result = []
    for p in products:
        loc = localize_product(p, lang)
        result.append(ProductOut(
            id=p.id,
            name=loc["name"],
            description=loc["description"],
            price=p.price,
            image_url=p.image_url,
            images=p.images,
            stock=p.stock,
            category=loc["category"],
            is_on_sale=p.is_on_sale,
            sales_count=p.sales_count,
        ))

    return ProductListOut(products=result, total=total)


@app.get("/api/products/{product_id}", response_model=ProductOut)
def get_product(product_id: int, request: Request, db: Session = Depends(get_db)):
    lang = get_lang(request)
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    loc = localize_product(product, lang)
    return ProductOut(
        id=product.id,
        name=loc["name"],
        description=loc["description"],
        price=product.price,
        image_url=product.image_url,
        images=product.images,
        stock=product.stock,
        category=loc["category"],
        is_on_sale=product.is_on_sale,
        sales_count=product.sales_count,
    )


@app.get("/api/categories")
def list_categories(request: Request, db: Session = Depends(get_db)):
    lang = get_lang(request)
    cats = db.query(Product.category).filter(Product.is_on_sale == True).distinct().all()
    result = []
    for c in cats:
        cat_key = c[0]
        if lang == "zh":
            result.append(CATEGORY_ZH.get(cat_key, cat_key))
        else:
            result.append(CATEGORY_EN.get(cat_key, cat_key))
    return {"categories": result}


# ============================================================
# Cart endpoints
# ============================================================

@app.get("/api/cart", response_model=CartOut)
def get_cart(user: User = Depends(require_user), db: Session = Depends(get_db)):
    items = db.query(CartItem).filter(CartItem.user_id == user.id).all()
    result = []
    total = 0.0
    for item in items:
        product = item.product
        subtotal = round(product.price * item.quantity, 2)
        total += subtotal
        result.append(CartItemOut(
            id=item.id,
            product_id=product.id,
            product_name=product.name,
            product_image=product.image_url,
            product_price=product.price,
            quantity=item.quantity,
            subtotal=subtotal,
        ))
    return CartOut(items=result, total=round(total, 2))


@app.post("/api/cart/items")
def add_to_cart(payload: CartItemIn, user: User = Depends(require_user), db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == payload.product_id, Product.is_on_sale == True).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.stock < payload.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")

    existing = db.query(CartItem).filter(
        CartItem.user_id == user.id, CartItem.product_id == payload.product_id
    ).first()
    if existing:
        existing.quantity += payload.quantity
    else:
        existing = CartItem(user_id=user.id, product_id=payload.product_id, quantity=payload.quantity)
        db.add(existing)
    db.commit()
    return {"message": "Added to cart"}


@app.put("/api/cart/items/{item_id}")
def update_cart_item(item_id: int, quantity: int = Query(ge=1, le=99),
                     user: User = Depends(require_user), db: Session = Depends(get_db)):
    item = db.query(CartItem).filter(CartItem.id == item_id, CartItem.user_id == user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    # Validate stock: requested quantity must not exceed available stock
    product = item.product
    if product and product.stock < quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")
    item.quantity = quantity
    db.commit()
    return {"message": "Updated"}


@app.delete("/api/cart/items/{item_id}")
def remove_cart_item(item_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)):
    item = db.query(CartItem).filter(CartItem.id == item_id, CartItem.user_id == user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    db.delete(item)
    db.commit()
    return {"message": "Removed"}


@app.delete("/api/cart")
def clear_cart(user: User = Depends(require_user), db: Session = Depends(get_db)):
    db.query(CartItem).filter(CartItem.user_id == user.id).delete()
    db.commit()
    return {"message": "Cart cleared"}


# ============================================================
# Order endpoints
# ============================================================

@app.post("/api/orders", response_model=OrderOut)
def create_order(payload: OrderCreateIn, request: Request, user: User = Depends(require_user), db: Session = Depends(get_db)):
    # Validate address
    address = db.query(Address).filter(Address.id == payload.address_id, Address.user_id == user.id).first()
    if not address:
        raise HTTPException(status_code=400, detail="Address not found")

    lang = get_lang(request)

    # Get cart items (filter by item_ids if specified)
    cart_items = db.query(CartItem).filter(CartItem.user_id == user.id)
    if payload.item_ids:
        cart_items = cart_items.filter(CartItem.id.in_(payload.item_ids))
    cart_items = cart_items.all()
    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    # Build order items & calculate total
    total_amount = 0.0
    order_items = []
    for ci in cart_items:
        product = ci.product
        product_name = product.name_zh if (lang == "zh" and product.name_zh) else product.name
        if not product or not product.is_on_sale:
            raise HTTPException(status_code=400, detail=f"Product {ci.product_id} is no longer available")
        if product.stock < ci.quantity:
            raise HTTPException(status_code=400, detail=f"Insufficient stock for {product_name}")

        total_amount += product.price * ci.quantity
        order_items.append({
            "product_id": product.id,
            "product_name": product_name,
            "product_image": product.image_url,
            "product_price": product.price,
            "quantity": ci.quantity,
        })

    # Calculate discount from coupon
    discount_amount = 0.0
    if payload.coupon_id:
        user_coupon = db.query(UserCoupon).filter(
            UserCoupon.id == payload.coupon_id,
            UserCoupon.user_id == user.id,
            UserCoupon.status == CouponStatus.UNUSED,
        ).first()
        if user_coupon:
            template = user_coupon.template
            now = datetime.now(timezone.utc)
            if template.start_time <= now <= template.end_time:
                coupon_applied = False
                if template.type == CouponType.FULL_REDUCTION:
                    if total_amount >= template.threshold:
                        discount_amount = template.value
                        coupon_applied = True
                elif template.type == CouponType.DISCOUNT:
                    discount_amount = round(total_amount * (1 - template.value / 100), 2)
                    coupon_applied = True
                if coupon_applied:
                    user_coupon.status = CouponStatus.USED
                    user_coupon.used_at = now
                    db.add(user_coupon)

    payment_amount = round(total_amount - discount_amount + DELIVERY_FEE, 2)
    order_no = f"ORD{int(time.time() * 1000)}"

    order = Order(
        order_no=order_no,
        user_id=user.id,
        address_id=address.id,
        address_snapshot=json.dumps(row2dict(address), default=str),
        total_amount=round(total_amount, 2),
        discount_amount=round(discount_amount, 2),
        delivery_fee=DELIVERY_FEE,
        payment_amount=payment_amount,
        status=OrderStatus.PENDING,
        payment_method=payload.payment_method,
        remark=payload.remark,
    )
    db.add(order)
    db.flush()

    for item_data in order_items:
        oi = OrderItem(order_id=order.id, **item_data)
        db.add(oi)

    # Deduct stock & clear cart
    for ci in cart_items:
        product = ci.product
        product.stock -= ci.quantity
        product.sales_count += ci.quantity
        db.add(product)
        db.delete(ci)

    db.commit()
    db.refresh(order)

    return OrderOut(
        id=order.id,
        order_no=order.order_no,
        total_amount=order.total_amount,
        discount_amount=order.discount_amount,
        delivery_fee=order.delivery_fee,
        payment_amount=order.payment_amount,
        status=order.status,
        payment_method=order.payment_method,
        remark=order.remark,
        created_at=order.created_at.isoformat() if order.created_at else None,
        items=[OrderItemOut.model_validate(oi) for oi in order.items],
    )


@app.get("/api/orders", response_model=OrderListOut)
def list_orders(
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
):
    """获取订单列表，支持状态筛选和分页"""
    q = db.query(Order).filter(Order.user_id == user.id)
    if status:
        try:
            status_enum = OrderStatus(status)
            q = q.filter(Order.status == status_enum)
        except ValueError:
            pass  # ignore invalid status

    total = q.count()
    orders = q.order_by(Order.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    result = []
    for o in orders:
        first_item = None
        if o.items:
            first = o.items[0]
            first_item = {"name": first.product_name, "image": first.product_image}

        result.append(OrderListItem(
            id=o.id,
            order_no=o.order_no,
            status=o.status,
            total_amount=o.total_amount,
            payment_amount=o.payment_amount,
            created_at=o.created_at.isoformat() if o.created_at else None,
            items_count=len(o.items),
            first_item=first_item,
        ))

    pages = (total + page_size - 1) // page_size if total > 0 else 1
    return OrderListOut(orders=result, total=total, page=page, pages=pages)


@app.get("/api/orders/{order_id}", response_model=OrderDetailOut)
def get_order(order_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)):
    """获取订单详情（含地址快照、物流信息）"""
    order = db.query(Order).filter(Order.id == order_id, Order.user_id == user.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    address_snapshot = None
    if order.address_snapshot:
        try:
            address_snapshot = AddressSnapshot(**json.loads(order.address_snapshot))
        except Exception:
            pass

    tracking = None
    if order.tracking_number:
        tracking = TrackingInfo(
            company=order.tracking_company,
            number=order.tracking_number,
            status=order.status.value if order.status else None,
            updated_at=order.shipped_at.isoformat() if order.shipped_at else None,
            traces=[],
        )

    return OrderDetailOut(
        id=order.id,
        order_no=order.order_no,
        status=order.status,
        created_at=order.created_at.isoformat() if order.created_at else None,
        paid_at=order.paid_at.isoformat() if order.paid_at else None,
        shipped_at=order.shipped_at.isoformat() if order.shipped_at else None,
        delivered_at=order.delivered_at.isoformat() if order.delivered_at else None,
        cancelled_at=order.cancelled_at.isoformat() if order.cancelled_at else None,
        cancel_reason=order.cancel_reason,
        total_amount=order.total_amount,
        discount_amount=order.discount_amount,
        delivery_fee=order.delivery_fee,
        payment_amount=order.payment_amount,
        payment_method=order.payment_method,
        remark=order.remark,
        items=[OrderItemOut.model_validate(oi) for oi in order.items],
        shipping_address=address_snapshot,
        tracking=tracking,
    )


@app.patch("/api/orders/{order_id}/status", response_model=OrderDetailOut)
def update_order_status(
    order_id: int,
    payload: OrderStatusUpdateIn,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """更新订单状态：取消(cancel) 或确认收货(complete)"""
    order = db.query(Order).filter(Order.id == order_id, Order.user_id == user.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    now = datetime.now(timezone.utc)

    if payload.action == "cancel":
        if order.status not in (OrderStatus.PENDING, OrderStatus.PAID):
            raise HTTPException(status_code=400, detail="当前状态不允许取消")
        order.status = OrderStatus.CANCELLED
        order.cancelled_at = now
    elif payload.action == "complete":
        if order.status != OrderStatus.DELIVERED:
            raise HTTPException(status_code=400, detail="当前状态不允许确认收货")
        order.status = OrderStatus.COMPLETED
        order.delivered_at = now
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

    db.commit()
    db.refresh(order)

    # 返回完整详情（同 get_order）
    address_snapshot = None
    if order.address_snapshot:
        try:
            address_snapshot = AddressSnapshot(**json.loads(order.address_snapshot))
        except Exception:
            pass

    tracking = None
    if order.tracking_number:
        tracking = TrackingInfo(
            company=order.tracking_company,
            number=order.tracking_number,
            status=order.status.value if order.status else None,
            updated_at=order.shipped_at.isoformat() if order.shipped_at else None,
            traces=[],
        )

    return OrderDetailOut(
        id=order.id, order_no=order.order_no, status=order.status,
        created_at=order.created_at.isoformat() if order.created_at else None,
        paid_at=order.paid_at.isoformat() if order.paid_at else None,
        shipped_at=order.shipped_at.isoformat() if order.shipped_at else None,
        delivered_at=order.delivered_at.isoformat() if order.delivered_at else None,
        cancelled_at=order.cancelled_at.isoformat() if order.cancelled_at else None,
        cancel_reason=order.cancel_reason,
        total_amount=order.total_amount, discount_amount=order.discount_amount,
        delivery_fee=order.delivery_fee, payment_amount=order.payment_amount,
        payment_method=order.payment_method, remark=order.remark,
        items=[OrderItemOut.model_validate(oi) for oi in order.items],
        shipping_address=address_snapshot, tracking=tracking,
    )


@app.get("/api/orders/{order_id}/tracking", response_model=TrackingInfo)
def get_order_tracking(order_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)):
    """获取物流信息"""
    order = db.query(Order).filter(Order.id == order_id, Order.user_id == user.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if not order.tracking_number:
        raise HTTPException(status_code=404, detail="暂无物流信息")

    return TrackingInfo(
        company=order.tracking_company,
        number=order.tracking_number,
        status=order.status.value if order.status else None,
        updated_at=order.shipped_at.isoformat() if order.shipped_at else None,
        traces=[
            {"time": order.shipped_at.isoformat() if order.shipped_at else None,
             "location": order.tracking_company or "快递公司",
             "description": "快件已发出"},
        ],
    )


@app.post("/api/orders/{order_id}/pay")
def pay_order(order_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)):
    """
    模拟支付（仅 Dev 模式）。
    Prod 模式下返回错误，引导使用微信支付。
    """
    if RUN_MODE == "prod":
        raise HTTPException(status_code=400, detail="请使用微信支付接口 /api/orders/{id}/wechat-pay")

    order = db.query(Order).filter(Order.id == order_id, Order.user_id == user.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != OrderStatus.PENDING:
        raise HTTPException(status_code=400, detail="Order cannot be paid")
    order.status = OrderStatus.PAID
    order.paid_at = datetime.now(timezone.utc)
    order.transaction_id = f"dev_txn_{order.order_no}"
    db.commit()
    return {"message": "Payment successful", "order_no": order.order_no}


@app.post("/api/orders/{order_id}/wechat-pay")
async def wechat_pay_order(order_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)):
    """
    微信支付 JSAPI 下单。
    返回 wx.requestPayment() 所需的参数。
    """
    order = db.query(Order).filter(Order.id == order_id, Order.user_id == user.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != OrderStatus.PENDING:
        raise HTTPException(status_code=400, detail="订单无法支付（状态不正确）")

    openid = user.openid
    amount_fen = yuan_to_fen(order.payment_amount)
    description = f"MiniShop订单{order.order_no}"

    try:
        result = await create_jsapi_order(
            openid=openid,
            order_no=order.order_no,
            total_amount=amount_fen,
            description=description,
        )
    except RuntimeError as e:
        logger.error(f"WeChat Pay failed for order {order.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    # 保存 prepay_id
    order.prepay_id = result.get("package", "").replace("prepay_id=", "")
    db.commit()

    return result


@app.post("/api/wechat-pay/notify")
async def wechat_pay_notify(request: Request, db: Session = Depends(get_db)):
    """
    微信支付结果通知回调。
    无需认证，通过微信签名验证。
    """
    # 读取原始 body
    body = await request.body()
    body_str = body.decode("utf-8")

    # 获取微信签名 headers
    timestamp = request.headers.get("wechatpay-timestamp", "")
    nonce = request.headers.get("wechatpay-nonce", "")
    signature = request.headers.get("wechatpay-signature", "")
    serial = request.headers.get("wechatpay-serial", "")

    logger.info(f"Payment notify received: serial={serial[:8] if serial else 'N/A'}..., "
                f"timestamp={timestamp}, nonce={nonce[:8]}...")

    # 验签
    if not verify_notify_signature(timestamp, nonce, signature, body_str):
        logger.error("Notify signature verification failed")
        raise HTTPException(status_code=400, detail="签名验证失败")

    # 解析通知体
    try:
        notify_data = json.loads(body_str)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    resource = notify_data.get("resource", {})
    ciphertext = resource.get("ciphertext", "")
    resource_nonce = resource.get("nonce", "")
    associated_data = resource.get("associated_data", "")

    # 解密 resource
    try:
        decrypted = decrypt_notify_resource(ciphertext, resource_nonce, associated_data)
    except RuntimeError as e:
        logger.error(f"Decrypt failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    out_trade_no = decrypted.get("out_trade_no", "")
    transaction_id = decrypted.get("transaction_id", "")
    trade_state = decrypted.get("trade_state", "")

    logger.info(f"Payment notify decrypted: out_trade_no={out_trade_no}, "
                f"transaction_id={transaction_id}, state={trade_state}")

    if trade_state != "SUCCESS":
        logger.warning(f"Trade state is not SUCCESS: {trade_state}, ignoring")
        return {"code": "SUCCESS", "message": "成功"}

    # 查找订单
    order = db.query(Order).filter(Order.order_no == out_trade_no).first()
    if not order:
        logger.error(f"Order not found for out_trade_no: {out_trade_no}")
        # 仍然返回 SUCCESS 让微信停止重试
        return {"code": "SUCCESS", "message": "成功"}

    # 金额校验
    notify_amount = decrypted.get("amount", {})
    notify_total = notify_amount.get("total", 0)
    if notify_total and yuan_to_fen(order.payment_amount) != notify_total:
        logger.error(f"Amount mismatch: order={order.payment_amount}, notify={notify_total / 100}")
        return {"code": "FAIL", "message": "金额不匹配"}

    # 更新订单状态
    if order.status == OrderStatus.PENDING:
        order.status = OrderStatus.PAID
        order.transaction_id = transaction_id
        order.paid_at = datetime.now(timezone.utc)
        db.commit()
        logger.info(f"Order {order.order_no} paid via notify, txn={transaction_id}")
    else:
        logger.info(f"Order {order.order_no} already in status {order.status}, skipping")

    # 必须返回此格式让微信停止重试
    return {"code": "SUCCESS", "message": "成功"}


# ============================================================
# Coupon endpoints
# ============================================================

@app.get("/api/coupons", response_model=List[CouponOut])
def list_available_coupons(db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    templates = db.query(CouponTemplate).filter(
        CouponTemplate.start_time <= now,
        CouponTemplate.end_time >= now,
        CouponTemplate.used_count < CouponTemplate.total_count,
    ).all()
    return [CouponOut(
        id=t.id, name=t.name, description=t.description, type=t.type,
        threshold=t.threshold, value=t.value,
        start_time=t.start_time.isoformat(), end_time=t.end_time.isoformat(),
    ) for t in templates]


@app.post("/api/coupons/{template_id}/claim")
def claim_coupon(template_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)):
    template = db.query(CouponTemplate).filter(CouponTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Coupon not found")

    now = datetime.now(timezone.utc)
    if not (template.start_time <= now <= template.end_time):
        raise HTTPException(status_code=400, detail="Coupon is not available")
    if template.used_count >= template.total_count:
        raise HTTPException(status_code=400, detail="Coupon has been fully claimed")

    existing = db.query(UserCoupon).filter(
        UserCoupon.user_id == user.id, UserCoupon.coupon_template_id == template_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You already claimed this coupon")

    user_coupon = UserCoupon(user_id=user.id, coupon_template_id=template_id, status=CouponStatus.UNUSED)
    template.used_count += 1
    db.add(user_coupon)
    db.add(template)
    db.commit()
    return {"message": "Coupon claimed"}


@app.get("/api/user/coupons", response_model=List[UserCouponOut])
def list_user_coupons(user: User = Depends(require_user), db: Session = Depends(get_db)):
    coupons = db.query(UserCoupon).filter(UserCoupon.user_id == user.id).all()
    result = []
    now = datetime.now(timezone.utc)
    for c in coupons:
        t = c.template
        # Auto-expire if past end time
        if c.status == CouponStatus.UNUSED and t.end_time < now:
            c.status = CouponStatus.EXPIRED
            db.add(c)
        result.append(UserCouponOut(
            id=c.id, status=c.status,
            template=CouponOut(
                id=t.id, name=t.name, description=t.description, type=t.type,
                threshold=t.threshold, value=t.value,
                start_time=t.start_time.isoformat(), end_time=t.end_time.isoformat(),
            ),
        ))
    if db.new or db.dirty:
        db.commit()
    return result


# ============================================================
# Address endpoints
# ============================================================

@app.get("/api/addresses", response_model=List[AddressOut])
def list_addresses(user: User = Depends(require_user), db: Session = Depends(get_db)):
    return [AddressOut.model_validate(a) for a in user.addresses]


@app.post("/api/addresses", response_model=AddressOut)
def create_address(payload: AddressIn, user: User = Depends(require_user), db: Session = Depends(get_db)):
    if payload.is_default:
        db.query(Address).filter(Address.user_id == user.id).update({"is_default": False})
    addr = Address(user_id=user.id, **payload.model_dump())
    db.add(addr)
    db.commit()
    db.refresh(addr)
    return AddressOut.model_validate(addr)


@app.put("/api/addresses/{address_id}", response_model=AddressOut)
def update_address(address_id: int, payload: AddressIn, user: User = Depends(require_user), db: Session = Depends(get_db)):
    addr = db.query(Address).filter(Address.id == address_id, Address.user_id == user.id).first()
    if not addr:
        raise HTTPException(status_code=404, detail="Address not found")
    if payload.is_default:
        db.query(Address).filter(Address.user_id == user.id).update({"is_default": False})
    for key, val in payload.model_dump().items():
        setattr(addr, key, val)
    db.commit()
    db.refresh(addr)
    return AddressOut.model_validate(addr)


@app.delete("/api/addresses/{address_id}")
def delete_address(address_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)):
    addr = db.query(Address).filter(Address.id == address_id, Address.user_id == user.id).first()
    if not addr:
        raise HTTPException(status_code=404, detail="Address not found")
    db.delete(addr)
    db.commit()
    return {"message": "Address deleted"}


# ============================================================
# Profile endpoints
# ============================================================

@app.get("/api/user/profile", response_model=UserProfileOut)
def get_profile(user: User = Depends(require_user)):
    """Get current user profile with masked openid."""
    return UserProfileOut(
        id=user.id,
        nickname=user.nickname,
        avatar=user.avatar,
        phone=user.phone,
        openid=_mask_openid(user.openid),
        created_at=user.created_at.isoformat() if user.created_at else None,
    )


@app.put("/api/user/profile", response_model=UserProfileOut)
def update_profile(payload: UserProfileUpdate, user: User = Depends(require_user), db: Session = Depends(get_db)):
    """Update current user profile (nickname, avatar, phone)."""
    if payload.nickname is not None:
        user.nickname = payload.nickname
    if payload.avatar is not None:
        user.avatar = payload.avatar
    if payload.phone is not None:
        user.phone = payload.phone
    db.commit()
    db.refresh(user)
    return UserProfileOut(
        id=user.id,
        nickname=user.nickname,
        avatar=user.avatar,
        phone=user.phone,
        openid=_mask_openid(user.openid),
        created_at=user.created_at.isoformat() if user.created_at else None,
    )


# ============================================================
# Account management
# ============================================================

@app.delete("/api/user/account")
def delete_account(user: User = Depends(require_user), db: Session = Depends(get_db)):
    """Soft-delete the current user's account."""
    user.is_active = False
    db.commit()
    return {"message": "Account deleted"}


# ============================================================
# Health
# ============================================================

@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello, World!"}
