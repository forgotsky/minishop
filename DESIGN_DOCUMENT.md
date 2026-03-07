# Web Shop Design Document

## 1. Objective
Build a small shopping application where users can:
- Browse products
- Add products to cart
- Enter delivery address
- Choose payment method
- Submit order

## 2. Architecture
Two-service architecture:
- Frontend service: React SPA (Vite build, served by Nginx)
- Backend service: Python FastAPI REST API

Communication:
- Frontend calls backend over HTTP JSON APIs (`/api/products`, `/api/checkout`)

## 3. Frontend Design (React)
Location:
- `frontend/src/App.jsx`
- `frontend/src/styles.css`

Responsibilities:
- Render product catalog from API
- Manage cart state in browser memory
- Validate checkout form before submit
- Send checkout payload to backend
- Show order success or error status

Runtime config:
- `frontend/public/config.js`
- `window.APP_CONFIG.API_BASE_URL`
  - Empty string for same-domain deployments
  - Backend base URL for separate deployments

## 4. Backend Design (FastAPI)
Location:
- `backend/app/main.py`

Responsibilities:
- Expose health, products, and checkout endpoints
- Validate input payload with Pydantic models
- Validate product IDs and quantities
- Compute subtotal, delivery fee, and total
- Return generated order ID and order summary

CORS:
- Controlled by `ALLOWED_ORIGINS` environment variable

## 5. API Contract
### GET `/api/health`
Response:
- `{ "status": "ok" }`

### GET `/api/products`
Response:
- `{ "products": [{"id":1,"name":"...","price":49.99}, ...] }`

### POST `/api/checkout`
Request body:
- `cart_items`: array of `{ id, qty }`
- `address`: `{ full_name, phone, street, city, zip }`
- `payment_method`: `card | cash`

Success response:
- `message`
- `order`: `order_id`, `subtotal`, `delivery_fee`, `total`, `payment_method`, `shipping_city`

## 6. Deployment Design
Containers:
- `frontend/Dockerfile`: builds React and serves via Nginx on port 80
- `backend/Dockerfile`: serves FastAPI via Uvicorn on port 8000

Kubernetes:
- Frontend Deployment + Service
- Backend Deployment + Service
- Optional ALB Ingress routes:
  - `/` -> frontend service
  - `/api` -> backend service

## 7. Security and Validation Notes
- Backend is source of truth for pricing and total calculation
- Backend validates cart item IDs/quantities and payment method
- CORS allowlist should be restricted in production
- TLS should be enabled at Ingress/Load Balancer

## 8. Scalability Notes
- Stateless services; horizontal scaling via replica count
- Product data is currently in-memory mock data
- For production, move product/order data to persistent database
