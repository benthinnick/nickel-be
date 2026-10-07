# Nickel Backend

Modular FastAPI monolith for the Nickel MVP. Products, customers, sellers, orders, payments, deliveries, and the transactional outbox persist in **PostgreSQL**. Login identity lives in **Keycloak**. Carts live in **Redis**.

## Requirements

- Python 3.12+
- PostgreSQL and Redis for local runtime (see Docker)
- Keycloak (optional; tests and local default use an in-memory issuer)

## Local setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
copy .env.example .env
```

On macOS/Linux, activate with `source .venv/bin/activate` and copy env with `cp .env.example .env`.

Default `DATABASE_URL` is Postgres (`postgresql+asyncpg://nickel:nickel@localhost:5432/nickel`). Tables are created on startup.

## Run

```bash
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

## Authentication

The API is an OIDC resource server. Clients sign in at Keycloak (authorization code + PKCE) and send `Authorization: Bearer <access_token>`. The API validates the JWT and JIT-provisions a local **customer** row keyed by Keycloak `sub`.

```bash
GET /api/v1/customers/me   # Authorization: Bearer <Keycloak access token>
```

Default `KEYCLOAK_ISSUER=memory://` accepts HS256 test tokens without Docker. For real SSO:

```bash
docker compose --profile sso up
```

Then set `KEYCLOAK_ISSUER=http://localhost:8080/realms/nickel` and `KEYCLOAK_AUDIENCE=nickel-api`. Keycloak uses its own Postgres (`keycloak-postgres`) and can run without the app. Realm `nickel` includes public client `nickel-web` (SSO) and confidential client `nickel-api` (audience + admin lookup). Dev user: `ada@example.com` / `secret123`.

Cart and checkout are public. A valid Bearer token uses Redis key `customer:{id}`; otherwise the signed `nickel_session` cookie uses `session:{id}`. The first authenticated request that still has a session cookie merges the session cart into the customer cart.

## Sellers and RBAC

Any logged-in customer can create a seller and becomes **owner**. Owners invite or remove members (by email: local customer cache, then Keycloak Admin). **Owners and members** can create products, adjust stock, and hide/unhide that seller's catalog. Non-members get **403**.

Product **create** does not write the row in the HTTP handler. `POST /api/v1/sellers/{id}/products` authorizes, writes `product_created` to the outbox (`nickel.products`), and returns **202** `{product_id, event_id}`. A Kafka consumer inserts the product. When `KAFKA_ENABLED=false` (local and tests), the same handler runs in-process after commit.

Product **create** sanitizes `name`, `description`, and `sku` (HTML tags stripped and text escaped) and rejects non-`http`/`https` `image_url` values. Public `GET /api/v1/products` stays unauthenticated and lists **active** products only. Hidden products are `inactive` and 404 on the public API. Cart add/checkout reject quantities above stock; checkout decrements stock.

`GET /api/v1/products/search?q=` searches **active** products by name via Elasticsearch (or an in-memory index when `ELASTICSEARCH_URL=memory://`, the default). `GET /api/v1/products/search/autocomplete?q=` returns up to 5 unique name suggestions from that index. Create indexes a product; hide removes it from the index; unhide re-indexes it. Those updates go through the outbox (`product_created` / `product_hidden` / `product_unhidden`). When Kafka is off, the same handlers run in-process after commit.

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| GET | `/health` | Liveness |
| GET | `/api/v1/products` | List active products (`limit`, `offset`) |
| GET | `/api/v1/products/search` | Search active products by name (`q`, `limit`, `offset`) |
| GET | `/api/v1/products/search/autocomplete` | Name suggestions from the search index (`q`, max 5) |
| GET | `/api/v1/products/{product_id}` | Get an active product by id |
| GET | `/api/v1/customers/me` | Current customer (Keycloak Bearer; JIT provision) |
| POST | `/api/v1/sellers` | Create seller (caller is owner) |
| GET | `/api/v1/sellers/me` | Sellers for the current customer |
| GET | `/api/v1/sellers/{seller_id}` | Seller detail (member) |
| POST | `/api/v1/sellers/{seller_id}/members` | Invite member by email (owner) |
| DELETE | `/api/v1/sellers/{seller_id}/members/{customer_id}` | Remove member (owner) |
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

Tests use in-memory SQLite, fakeredis, an in-memory product search index, and `KEYCLOAK_ISSUER=memory://`; they do not need Docker.

## Docker

Postgres, Redis, and the app:

```bash
docker compose up --build
```

Optional Keycloak (own Postgres, can run without the app):

```bash
docker compose --profile sso up
```

Optional Kafka (KRaft):

```bash
docker compose --profile kafka up
```

Optional Elasticsearch:

```bash
docker compose --profile search up
```

Set `ELASTICSEARCH_URL=http://elasticsearch:9200` (or `http://localhost:9200` when the app runs on the host). The default `memory://` keeps search in-process without Elasticsearch.

## Roadmap

- Split the monolith into microservices behind an API gateway.
- Generate API clients and event contracts from the service schemas.
- Replace the stub delivery flow with a delivery system.
- Add an inventory system for stock across sellers.
- Store and serve product video.
- Add ratings and comments on products.
- Integrate a payment provider in place of the stub.
- Send email notifications for orders, payments, and delivery.
- Build an analytics ETL/ELT pipeline from orders, catalog, and search events.
- Add observability: metrics, traces, and logs across services.
- Support discounts on products and orders.
