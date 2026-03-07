from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List
import os
import time


class Product(BaseModel):
    id: int
    name: str
    price: float


class CartItem(BaseModel):
    id: int
    qty: int = Field(gt=0)


class Address(BaseModel):
    full_name: str = Field(min_length=2)
    phone: str = Field(min_length=5)
    street: str = Field(min_length=3)
    city: str = Field(min_length=2)
    zip: str = Field(min_length=3)


class CheckoutRequest(BaseModel):
    cart_items: List[CartItem] = Field(min_length=1)
    address: Address
    payment_method: str


class CheckoutResponse(BaseModel):
    message: str
    order: dict


app = FastAPI(title="Web Shop API", version="1.0.0")

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

PRODUCTS = [
    Product(id=1, name="Wireless Headphones", price=49.99),
    Product(id=2, name="Smart Watch", price=89.0),
    Product(id=3, name="Bluetooth Speaker", price=35.5),
    Product(id=4, name="Backpack", price=28.75),
    Product(id=5, name="Running Shoes", price=64.2),
    Product(id=6, name="Power Bank", price=22.99),
]
DELIVERY_FEE = 5.0


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/products")
def get_products() -> dict:
    return {"products": PRODUCTS}


@app.post("/api/checkout", response_model=CheckoutResponse)
def checkout(payload: CheckoutRequest) -> CheckoutResponse:
    if payload.payment_method not in ["card", "cash"]:
        raise HTTPException(status_code=400, detail="Invalid payment method.")

    subtotal = 0.0
    for item in payload.cart_items:
        product = next((p for p in PRODUCTS if p.id == item.id), None)
        if not product:
            raise HTTPException(status_code=400, detail=f"Product {item.id} not found.")
        subtotal += product.price * item.qty

    total = subtotal + DELIVERY_FEE
    order = {
        "order_id": f"ORD-{int(time.time() * 1000)}",
        "subtotal": round(subtotal, 2),
        "delivery_fee": DELIVERY_FEE,
        "total": round(total, 2),
        "payment_method": payload.payment_method,
        "shipping_city": payload.address.city,
    }

    return CheckoutResponse(
        message="Payment successful. Your order has been placed.",
        order=order,
    )
