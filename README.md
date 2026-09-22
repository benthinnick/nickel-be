# Shekel Backend

Modular FastAPI monolith for the Shekel MVP. Products, users, sellers, orders, payments, deliveries, and the transactional outbox persist in **PostgreSQL**. Carts live in **Redis**.

## Requirements

- Python 3.12+
- PostgreSQL and Redis for local runtime (see Docker)

## Local setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
copy .env.example .env
```

On macOS/Linux, activate with `source .venv/bin/activate` and copy env with `cp .env.example .env`.

Default `DATABASE_URL` is Postgres (`postgresql+asyncpg://shekel:shekel@localhost:5432/shekel`). Tables are created on startup.

## Run

```bash
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

## Authentication

Register, then exchange email/password for a JWT (OAuth2 password grant). `username` is the email:

```bash
POST /api/v1/users
POST /api/v1/auth/token   # application/x-www-form-urlencoded: username, password
GET  /api/v1/users/me     # Authorization: Bearer <access_token>
```

Cart and checkout are public. A valid Bearer token uses Redis key `user:{id}`; otherwise the signed `shekel_session` cookie uses `session:{id}`. Logging in merges the session cart into the user cart.

## Sellers and RBAC

Any logged-in user can create a seller and becomes **owner**. Owners invite or remove members (by registered email). **Owners and members** can create products, adjust stock, and hide/unhide that seller's catalog. Non-members get **403**.

Product **create** does not write the row in the HTTP handler. `POST /api/v1/sellers/{id}/products` authorizes, writes `product_created` to the outbox (`shekel.products`), and returns **202** `{product_id, event_id}`. A Kafka consumer inserts the product. When `KAFKA_ENABLED=false` (local and tests), the same handler runs in-process after commit.

Public `GET /api/v1/products` stays unauthenticated and lists **active** products only. Hidden products are `inactive` and 404 on the public API. Cart add/checkout reject quantities above stock; checkout decrements stock.

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| GET | `/health` | Liveness |
| GET | `/api/v1/products` | List active products (`limit`, `offset`) |
| GET | `/api/v1/products/{product_id}` | Get an active product by id |
| POST | `/api/v1/users` | Register |
| POST | `/api/v1/auth/token` | Issue JWT |
| GET | `/api/v1/users/me` | Current user (Bearer) |
| POST | `/api/v1/sellers` | Create seller (caller is owner) |
| GET | `/api/v1/sellers/me` | Sellers for the current user |
| GET | `/api/v1/sellers/{seller_id}` | Seller detail (member) |
| POST | `/api/v1/sellers/{seller_id}/members` | Invite member by email (owner) |
| DELETE | `/api/v1/sellers/{seller_id}/members/{user_id}` | Remove member (owner) |
| GET | `/api/v1/sellers/{seller_id}/products` | Seller catalog including hidden (member) |
| POST | `/api/v1/sellers/{seller_id}/products` | Enqueue product create (202) |
| POST | `/api/v1/sellers/{seller_id}/products/{product_id}/stock` | Adjust stock (`delta`) |
| POST | `/api/v1/sellers/{seller_id}/products/{product_id}/hide` | Hide product |
| POST | `/api/v1/sellers/{seller_id}/products/{product_id}/unhide` | Unhide product |
| GET | `/api/v1/cart` | Get cart (cookie or Bearer) |
| PUT | `/api/v1/cart/items` | Add or update a cart item |
| DELETE | `/api/v1/cart/items/{product_id}` | Remove a cart item |
| POST | `/api/v1/cart/checkout` | Create an order from the cart |
| GET | `/api/v1/orders/{order_id}` | Get an order |
| POST | `/api/v1/orders/{order_id}/payments` | Start payment (stub provider) |
| GET | `/api/v1/orders/{order_id}/delivery` | Get delivery for an order |

Checkout writes `order_created` to the outbox. Starting payment writes `order_payment_succeeded` or `order_payment_failed`. After a succeeded payment is consumed, delivery is stubbed and `order_delivered` is enqueued.

Kafka is **disabled** by default (`KAFKA_ENABLED=false`). Outbox rows are still written. Enable Kafka to start the outbox publisher and consumer:

```bash
KAFKA_ENABLED=true
```

## Tests

```bash
pytest
```

Tests use in-memory SQLite and fakeredis; they do not need Docker.

## Docker

Postgres, Redis, and the app:

```bash
docker compose up --build
```

Optional Kafka (KRaft):

```bash
docker compose --profile kafka up
```
