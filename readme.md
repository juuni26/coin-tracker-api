# Coin Tracker API — Tier 3 (Production)

> Final tier of a 3-tier teaching series. Async SQLAlchemy, Postgres-ready, refresh-token rotation, rate limiting, provider abstraction, Railway deploy.
>
> | Branch | What you learn |
> |---|---|
> | [`tier-0-original`](../../tree/tier-0-original) | The realistic "before" — single 417-line `main.py` |
> | [`tier-1-resource-based`](../../tree/tier-1-resource-based) | Resource-based routers, REST verbs, Pydantic response models |
> | [`tier-2-layered`](../../tree/tier-2-layered) | SQLAlchemy 2.0, Alembic, repository + service layers |
> | [`main`](../../tree/main) = [`tier-3-production`](../../tree/tier-3-production) | Async SQLAlchemy + Postgres, refresh tokens, rate limiting, Railway |

## What tier 3 actually buys you

Tier 1 was *organize*. Tier 2 was *layer*. Tier 3 is *make it production-grade.* The goal is a service you would not be embarrassed to run for real users — and the lessons are the things tutorials usually skip.

## What changed from tier 2

### 1. Async everywhere

Every layer is now `async`/`await`:

```python
# repositories/user.py
async def get_by_email(self, email: str) -> User | None:
    result = await self.db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()

# services/auth.py
async def authenticate(self, email: str, password: str) -> TokenPair: ...

# routers/auth.py
@router.post("/login")
async def login(...): ...
```

The DB engine is `create_async_engine`, the session is `AsyncSession`, and the request lifecycle is async end-to-end. Why does this matter? **Concurrency under load.** A sync FastAPI worker blocks on every DB call; an async worker frees the event loop to serve other requests during I/O waits. Same hardware, several times the throughput.

### 2. Postgres-ready (with SQLite for local dev)

`DATABASE_URL` is the single knob:

| Environment | URL |
|---|---|
| Local dev | `sqlite+aiosqlite:///./tracker_coin.db` |
| Railway / prod | `postgresql+asyncpg://...` (Railway sets this when you attach a Postgres add-on) |

The app **normalizes** Heroku/Railway-style `postgres://` → `postgresql+asyncpg://` automatically (`app/config.py:_normalize_database_url`). Tests still use SQLite for speed; the production deploy uses Postgres without code changes.

The same Alembic migrations run against both — no separate "sqlite migration" and "postgres migration."

### 3. Refresh-token rotation

This is the auth feature most tutorials skip. Tier 3 issues **two** tokens per session:

| Token | What it is | Lifetime | Stored where |
|---|---|---|---|
| Access | JWT, stateless | 15 min | Client memory |
| Refresh | Random opaque string, rotated on use | 14 days | Client + `refresh_tokens` table (hashed) |

Flow:

1. `POST /auth/register` or `/auth/login` → returns `{access_token, refresh_token}`
2. When access expires, client calls `POST /auth/refresh` with the refresh token
3. Server **revokes** the old refresh token and issues a fresh pair (access + refresh)
4. `POST /auth/logout` revokes the refresh token (logout now actually does something on the server)

Why rotate? If a refresh token leaks, an attacker can use it once — but then either the user's next refresh fails (detection signal) or the attacker keeps refreshing and the user's next refresh fails. Either way, you find out. Without rotation, a leaked refresh token is good for 14 days, silently.

We store `sha256(token)` not the raw value — so a DB read does not yield usable tokens.

### 4. Provider abstraction (`PriceProvider` Protocol)

Tier 1 swapped CoinCap for CoinGecko in a single file. Tier 3 introduces a **Protocol** so swapping is one config change:

```python
# providers/base.py
class PriceProvider(Protocol):
    name: str
    async def fetch_market_coins(self) -> list[MarketCoin]: ...

# providers/factory.py
def get_price_provider() -> PriceProvider:
    if settings.COINCAP_API_KEY:
        return CoinCapProvider()    # paid, more reliable
    return CoinGeckoProvider()      # keyless, free tier
```

The service receives a `PriceProvider` via dependency injection; it does not know or care which one. Adding a third provider (CryptoCompare, Binance, etc.) is one new file.

### 5. Rate limiting on auth endpoints

Brute-force is the #1 way poorly-deployed APIs get owned. Tier 3 adds [slowapi](https://github.com/laurentS/slowapi) per-IP limits:

| Endpoint | Limit |
|---|---|
| `POST /auth/register` | 3 / minute |
| `POST /auth/login` | 5 / minute |
| `POST /auth/refresh` | 10 / minute |

Limits are skipped in tests via `RATE_LIMIT_ENABLED=false` so the suite stays fast and deterministic.

### 6. Railway deploy config

Three files:

- **`Procfile`** — `release` runs `alembic upgrade head` before each deploy, `web` boots uvicorn on `$PORT`
- **`railway.json`** — health check at `/health`, restart policy, start command (Postgres-ready)
- **`runtime.txt`** — pins Python 3.12 for predictable nixpacks builds

Deploy steps:

```bash
# In Railway dashboard:
# 1. New Project → Deploy from GitHub repo → pick this branch
# 2. Add a Postgres plugin → Railway auto-injects DATABASE_URL
# 3. Add env vars: JWT_SECRET_KEY (long random), RATE_LIMIT_ENABLED=true
# 4. Deploy. Migrations run automatically via the Procfile release step.
```

That's it. The `_normalize_database_url` helper makes Railway's `postgres://...` value work without manual edits.

## Folder layout (additions over tier 2)

```
app/
├── rate_limit.py             # NEW: slowapi Limiter
├── providers/
│   ├── base.py               # NEW: PriceProvider Protocol + MarketCoin
│   ├── factory.py            # NEW: pick provider by config
│   ├── coingecko.py          # async (httpx.AsyncClient)
│   └── coincap.py            # NEW: alt provider, requires API key
├── models/
│   └── refresh_token.py      # NEW
├── repositories/
│   └── refresh_token.py      # NEW
├── services/auth.py          # rewritten: refresh + rotation + logout-revoke
├── schemas/auth.py           # + RefreshRequest, LogoutRequest, refresh_token field
├── routers/auth.py           # + /auth/refresh; rate-limited
├── main.py                   # + slowapi middleware + 429 handler
└── db.py                     # async engine + AsyncSession
alembic/versions/
└── 0002_refresh_tokens.py    # NEW
Procfile                      # NEW (Railway release + web)
railway.json                  # NEW
runtime.txt                   # NEW (Python 3.12)
pytest.ini                    # NEW (asyncio_mode = auto)
```

## Run it locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                 # set JWT_SECRET_KEY

alembic upgrade head                  # apply migrations to local sqlite
uvicorn app.main:app --reload
```

Open http://localhost:8000/docs.

## Test it

```bash
pytest -v
```

**18 async tests, all green.** Includes refresh-token rotation, revocation, and rate-limit-disabled coverage.

## Try the flow

```bash
# Populate coins (uses CoinGecko by default; CoinCap if COINCAP_API_KEY is set)
curl -X POST http://localhost:8000/coins/refresh

# Register — returns access_token + refresh_token
curl -X POST http://localhost:8000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"secret123","password_confirmation":"secret123"}'

ACCESS=...   # from response
REFRESH=...

# Use access token
curl -X POST http://localhost:8000/portfolio \
  -H "Authorization: Bearer $ACCESS" \
  -H 'Content-Type: application/json' \
  -d '{"coin_id":1}'

# Rotate when access expires (15 min)
curl -X POST http://localhost:8000/auth/refresh \
  -H 'Content-Type: application/json' \
  -d "{\"refresh_token\":\"$REFRESH\"}"

# Logout — actually revokes the refresh token server-side
curl -X POST http://localhost:8000/auth/logout \
  -H 'Content-Type: application/json' \
  -d "{\"refresh_token\":\"$REFRESH\"}"
```

## Design decisions worth knowing

1. **Why store refresh tokens hashed?** A database read should not be a security incident. With SHA-256 hashing, an attacker who dumps the table cannot replay sessions. Same logic as password hashing.

2. **Why JWT for access, opaque for refresh?** JWTs are great for stateless verification (every request) and bad for revocation (you can't take one back). Refresh tokens need server-side state for revocation, so they are opaque random strings backed by a row in `refresh_tokens`. Use the right tool for each purpose.

3. **Why async if SQLite is sync underneath?** `aiosqlite` runs SQLite operations on a thread pool; the FastAPI handler still gets to await without blocking. In production you swap to `asyncpg` (truly async) and gain real throughput. Same code path.

4. **Why a Protocol instead of an abstract base class?** PEP 544 structural typing — `CoinGeckoProvider` and `CoinCapProvider` don't need to inherit from anything. Any class with the right shape *is* a `PriceProvider`. Easier to mock in tests, easier to add new providers without touching base classes.

5. **Why does `/auth/logout` need the refresh token?** Because logout that does nothing on the server (tier 2's behavior) is a lie. Revoking the token is the difference between "we told the client to forget" and "this session is actually over."

6. **Why the `release: alembic upgrade head` step?** Schema changes must run *before* the new code starts handling traffic. Putting migrations in the release phase guarantees this — the new web process only boots after the DB is on the right version.

7. **Why does the test suite still work without Postgres?** Because the abstraction is the dialect, not the engine. SQLAlchemy 2.0 + Alembic generate dialect-appropriate SQL automatically. We test the contract; production exercises the dialect-specific paths.

## What this series covered (tier 0 → 3)

- Tier 0 → 1: separate concerns, fix REST verbs, add response models, swap a dead provider
- Tier 1 → 2: introduce ORM, migrations, repos, services, domain exceptions
- Tier 2 → 3: go async, add Postgres support, rotate refresh tokens, rate-limit auth, abstract providers, deploy to Railway

Same coin tracker. Same external API contract (one additive change: `refresh_token` in tier 3 responses). Three branches' worth of progressively production-grade lessons.

If this is your first FastAPI codebase, **diff the branches in order** — that is the lesson. The code is just the artifact.
