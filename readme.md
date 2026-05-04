# Coin Tracker API — Tier 1: Resource-Based

> Part of a 3-tier teaching series. Follow the branches to watch a FastAPI codebase grow from a 417-line `main.py` into a production-grade service.
>
> | Branch | What you learn |
> |---|---|
> | [`tier-0-original`](../../tree/tier-0-original) | The realistic "before" — single file, raw SQL, mixed concerns, GETs that mutate data. **Start here.** |
> | [`tier-1-resource-based`](../../tree/tier-1-resource-based) ← *you are here* | Resource-based routers, REST verbs, Pydantic response models |
> | [`tier-2-layered`](../../tree/tier-2-layered) *(coming)* | Service/repository layers, SQLAlchemy + Alembic, dependency injection for DB |
> | `main` (tier 3) *(coming)* | Async SQLAlchemy, Postgres, refresh tokens, rate limiting, CI, Railway deploy |

## Why this branch exists

Tier 0 is what most real codebases look like when a tutorial-grade project starts being used in anger: one big file, raw `sqlite3` calls scattered through route handlers, `GET /coins-update` that wipes and rebuilds the database, request bodies returned as plain `dict`s, and HTTP status codes hand-rolled inside JSON bodies (`{"status_code": 400}` returned with HTTP 200).

Tier 1 is the smallest meaningful jump: **organize the code by resource and speak HTTP correctly**. We don't introduce SQLAlchemy yet — that's tier 2's lesson. The point is that *structure comes first*, then abstractions.

## What changed from tier 0

### 1. Resource-based file layout

```
app/
├── main.py              # FastAPI() + router includes (15 lines)
├── config.py            # env loading, single Settings object
├── db.py                # sqlite3 connection helper + schema bootstrap
├── security.py          # password hashing + JWT encode/decode
├── deps.py              # get_current_user dependency
├── providers/
│   └── coingecko.py     # external price-data provider, isolated
├── schemas/             # Pydantic request + response models
│   ├── auth.py
│   ├── coin.py
│   └── portfolio.py
└── routers/             # one file per resource
    ├── auth.py          # /auth/*
    ├── coins.py         # /coins/*
    └── portfolio.py     # /portfolio/*
tests/
├── conftest.py          # isolated tmp sqlite per session
├── test_auth.py
├── test_coins.py
└── test_portfolio.py
```

Each route file owns one resource end-to-end. `main.py` becomes an index, not a kitchen sink.

### 2. REST-correct verbs and paths

| Tier 0 (RPC-flavored) | Tier 1 (RESTful) | Why |
|---|---|---|
| `GET /coins-update` | `POST /coins/refresh` (202) | A GET that mutates is an anti-pattern — caches, prefetchers, and bots can fire it |
| `GET /reset-data` | **removed** | Same problem, even more dangerous. Tests use isolated DBs instead |
| `POST /add-coin-track` | `POST /portfolio` (201) | Resource-based collection POST |
| `POST /remove-coin-track` | `DELETE /portfolio/{coin_id}` (204) | Path param, correct verb |
| `GET /coin-track` | `GET /portfolio` | Plural noun for collections |
| `POST /login` | `POST /auth/login` | Grouped under the `auth` resource |
| `POST /register` | `POST /auth/register` (201) | Creation returns 201, not 200 |
| `GET /` → `{"message": "Hi"}` | `GET /health` → `{"status": "ok"}` | Conventional health probe |

### 3. Pydantic response models

Tier 0 returned raw `dict`s. That means OpenAPI shows `{}` for every response and clients have no contract. Tier 1 declares `response_model=...` on every endpoint, which:
- generates a real schema at `/docs`,
- strips fields you forgot were in the dict (e.g. password hashes),
- gives you free runtime validation of your own outputs.

Request and response shapes are **separate classes** — `RegisterRequest` carries `password`; nothing in the response files does. This is how you avoid leaking sensitive fields by accident.

### 4. Status codes that mean something

Tier 0 returned HTTP 200 with `{"status_code": 400}` in the body. Tier 1:
- `201 Created` for register / portfolio add
- `202 Accepted` for the refresh action
- `204 No Content` for logout / portfolio delete
- `401 Unauthorized` for bad credentials / missing token
- `404 Not Found` for unknown coin / unknown portfolio item
- `409 Conflict` for duplicate email / duplicate portfolio entry
- `422 Unprocessable Entity` for schema validation failures (Pydantic gives this for free)

### 5. CoinCap → CoinGecko

The original code called `https://api.coincap.io/v2/assets`. **That host's DNS no longer resolves** — CoinCap moved to `pro.coincap.io` with a paid API key requirement. We migrated to **CoinGecko** (`/api/v3/coins/markets`, no key needed for the public endpoint) and put it in `app/providers/coingecko.py`. Isolating external calls in a `providers/` module is what makes tier 3's `PriceProvider` protocol a one-file change later.

> **Lesson:** external APIs die. Wrap them, never call `requests.get` directly from a route handler.

### 6. Schema fixes

The old `coins` table mixed `shortName` (camelCase) with `priceUsd`. Tier 1 standardizes on snake_case (`external_id`, `price_usd`, `market_cap_rank`, `image_url`, `last_updated`) and adds a `UNIQUE` constraint on `external_id` so refresh becomes an idempotent upsert (`INSERT ... ON CONFLICT DO UPDATE`) instead of "drop the table and re-insert everything."

### 7. Dependency injection for the current user

```python
# app/deps.py
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]

# app/routers/portfolio.py
def list_portfolio(user: CurrentUserDep) -> list[PortfolioItemResponse]:
    ...
```

No more `request.state.user_id` plumbing — typed, testable, autocompleted.

### 8. Tests that actually isolate state

Tier 0's tests ran against the live SQLite file in the repo and depended on a successful CoinCap fetch. Tier 1's `conftest.py` points the app at a throwaway DB per session and seeds coins directly, so tests are deterministic and don't need internet access.

## Run it

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                # edit JWT_SECRET_KEY
uvicorn app.main:app --reload
```

Open http://localhost:8000/docs for the interactive OpenAPI UI.

## Test it

```bash
pytest -v
```

17 tests, no network required.

## Try the flow

```bash
# Populate the local DB from CoinGecko (one-time, before adding to portfolio)
curl -X POST http://localhost:8000/coins/refresh

# Register
curl -X POST http://localhost:8000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"secret123","password_confirmation":"secret123"}'

# Use the access_token from the response above
TOKEN=...

# Add a coin (id=1 is the top-ranked one from your refresh)
curl -X POST http://localhost:8000/portfolio \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"coin_id":1}'

# List your portfolio
curl http://localhost:8000/portfolio -H "Authorization: Bearer $TOKEN"
```

## What tier 2 will add

- Replace raw SQL with **SQLAlchemy 2.0** models + **Alembic** migrations
- Introduce a **service layer** (business logic) and **repository layer** (data access) so handlers are 5 lines each
- Database session as a FastAPI **dependency** (`Depends(get_db)`), not a context manager inside the handler
- Same API contract — only internals change. Diff `tier-1...tier-2` to see exactly what an ORM buys you.

## Design decisions worth knowing

1. **Why no SQLAlchemy here?** Premature abstraction. You can't appreciate what an ORM solves until you've felt the pain of raw SQL spread across handlers. Tier 1 is that pain in a contained form.
2. **Why `Annotated[..., Depends(...)]`?** Modern FastAPI DI. Reusable as type aliases, plays well with mypy, replaces the older `= Depends(...)` default-arg style.
3. **Why a `providers/` folder for one file?** Because tier 3 will add a second one (`coincap.py` opt-in via API key) behind a `PriceProvider` protocol. Folders signal *intent*, not just current contents.
4. **Why is `db_truncate_tables` gone?** It existed only because tests needed a clean slate. Now tests use a tmp file — no production code path needs it.
