import os
import time
import json
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends, Query
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
from .auth import create_access_token, require_user, get_current_user

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
app.mount("/images", StaticFiles(directory=os.path.join(STATIC_DIR, "images")), name="images")

DELIVERY_FEE = 5.0


@app.on_event("startup")
def on_startup() -> None:
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

def seed_products(db: Session) -> None:
    products = [
        Product(name="Wireless Headphones", description="Premium noise-cancelling wireless headphones with 30hr battery life.", price=49.99, image_url="/images/headphones.jpg", stock=120, category="electronics", sales_count=56),
        Product(name="Smart Watch", description="Fitness tracker with heart rate monitor and GPS.", price=89.00, image_url="/images/watch.jpg", stock=80, category="electronics", sales_count=34),
        Product(name="Bluetooth Speaker", description="Portable waterproof speaker with deep bass.", price=35.50, image_url="/images/speaker.jpg", stock=200, category="electronics", sales_count=78),
        Product(name="Backpack", description="Lightweight travel backpack, water-resistant.", price=28.75, image_url="/images/backpack.jpg", stock=150, category="accessories", sales_count=22),
        Product(name="Running Shoes", description="Breathable mesh running shoes with cushioned sole.", price=64.20, image_url="/images/shoes.jpg", stock=60, category="sports", sales_count=91),
        Product(name="Power Bank", description="20000mAh fast-charging power bank with USB-C.", price=22.99, image_url="/images/powerbank.jpg", stock=180, category="electronics", sales_count=110),
        Product(name="Coffee Mug", description="Insulated stainless steel mug, 500ml.", price=15.99, image_url="/images/mug.jpg", stock=300, category="kitchen", sales_count=45),
        Product(name="Desk Lamp", description="LED desk lamp with adjustable brightness.", price=19.99, image_url="/images/lamp.jpg", stock=90, category="home", sales_count=67),
    ]
    for p in products:
        db.add(p)
    db.commit()


def seed_coupons(db: Session) -> None:
    now = datetime.utcnow()
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


class OrderOut(BaseModel):
    id: int
    order_no: str
    total_amount: float
    discount_amount: float
    delivery_fee: float
    payment_amount: float
    status: OrderStatus
    payment_method: Optional[str] = None
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


# ============================================================
# Helper functions
# ============================================================

def row2dict(obj):
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


# ============================================================
# Auth endpoints
# ============================================================

@app.post("/api/auth/login", response_model=LoginOut)
def wx_login(payload: WxLoginIn, db: Session = Depends(get_db)):
    """
    WeChat mini-program login.
    In production, exchange code for openid via WeChat API.
    For dev: use code as a mock openid.
    """
    # TODO: In production, call WeChat API:
    # GET https://api.weixin.qq.com/sns/jscode2session?appid=APPID&secret=SECRET&js_code=CODE&grant_type=authorization_code
    # The response contains openid and session_key.
    mock_openid = f"wx_{payload.code}" if payload.code else f"wx_dev_{int(time.time())}"

    user = db.query(User).filter(User.openid == mock_openid).first()
    if not user:
        user = User(openid=mock_openid, nickname=payload.nickname, avatar=payload.avatar)
        db.add(user)
        db.commit()
        db.refresh(user)
    elif payload.nickname:
        user.nickname = payload.nickname
        user.avatar = payload.avatar
        db.commit()
        db.refresh(user)

    token = create_access_token(user.id)
    return LoginOut(token=token, user_id=user.id, nickname=user.nickname)


# ============================================================
# Product endpoints
# ============================================================

@app.get("/api/products", response_model=ProductListOut)
def list_products(
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    q = db.query(Product).filter(Product.is_on_sale == True)
    if category:
        q = q.filter(Product.category == category)
    if search:
        q = q.filter(Product.name.ilike(f"%{search}%"))

    total = q.count()
    products = q.order_by(Product.sales_count.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return ProductListOut(products=[ProductOut.model_validate(p) for p in products], total=total)


@app.get("/api/products/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductOut.model_validate(product)


@app.get("/api/categories")
def list_categories(db: Session = Depends(get_db)):
    categories = db.query(Product.category).filter(Product.is_on_sale == True).distinct().all()
    return {"categories": [c[0] for c in categories]}


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
def create_order(payload: OrderCreateIn, user: User = Depends(require_user), db: Session = Depends(get_db)):
    # Validate address
    address = db.query(Address).filter(Address.id == payload.address_id, Address.user_id == user.id).first()
    if not address:
        raise HTTPException(status_code=400, detail="Address not found")

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
        if not product or not product.is_on_sale:
            raise HTTPException(status_code=400, detail=f"Product {ci.product_id} is no longer available")
        if product.stock < ci.quantity:
            raise HTTPException(status_code=400, detail=f"Insufficient stock for {product.name}")

        total_amount += product.price * ci.quantity
        order_items.append({
            "product_id": product.id,
            "product_name": product.name,
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
            now = datetime.utcnow()
            if template.start_time <= now <= template.end_time:
                if template.type == CouponType.FULL_REDUCTION:
                    if total_amount >= template.threshold:
                        discount_amount = template.value
                elif template.type == CouponType.DISCOUNT:
                    discount_amount = round(total_amount * (1 - template.value / 100), 2)
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
        created_at=order.created_at.isoformat() if order.created_at else None,
        items=[OrderItemOut.model_validate(oi) for oi in order.items],
    )


@app.get("/api/orders", response_model=List[OrderOut])
def list_orders(user: User = Depends(require_user), db: Session = Depends(get_db),
                page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=50)):
    orders = (
        db.query(Order)
        .filter(Order.user_id == user.id)
        .order_by(Order.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return [OrderOut(
        id=o.id, order_no=o.order_no, total_amount=o.total_amount,
        discount_amount=o.discount_amount, delivery_fee=o.delivery_fee,
        payment_amount=o.payment_amount, status=o.status,
        payment_method=o.payment_method,
        created_at=o.created_at.isoformat() if o.created_at else None,
        items=[OrderItemOut.model_validate(oi) for oi in o.items],
    ) for o in orders]


@app.get("/api/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id, Order.user_id == user.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return OrderOut(
        id=order.id, order_no=order.order_no, total_amount=order.total_amount,
        discount_amount=order.discount_amount, delivery_fee=order.delivery_fee,
        payment_amount=order.payment_amount, status=order.status,
        payment_method=order.payment_method,
        created_at=order.created_at.isoformat() if order.created_at else None,
        items=[OrderItemOut.model_validate(oi) for oi in order.items],
    )


@app.post("/api/orders/{order_id}/pay")
def pay_order(order_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id, Order.user_id == user.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != OrderStatus.PENDING:
        raise HTTPException(status_code=400, detail="Order cannot be paid")
    order.status = OrderStatus.PAID
    order.paid_at = datetime.utcnow()
    db.commit()
    return {"message": "Payment successful", "order_no": order.order_no}


# ============================================================
# Coupon endpoints
# ============================================================

@app.get("/api/coupons", response_model=List[CouponOut])
def list_available_coupons(db: Session = Depends(get_db)):
    now = datetime.utcnow()
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

    now = datetime.utcnow()
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
    now = datetime.utcnow()
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
# Health
# ============================================================

@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello, World!"}
