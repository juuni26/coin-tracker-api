# Coin Tracker API — Tier 2: Layered Architecture + ORM

> Part of a 3-tier teaching series. Follow the branches to watch a FastAPI codebase grow up.
>
> | Branch | What you learn |
> |---|---|
> | [`tier-0-original`](../../tree/tier-0-original) | The realistic "before" — single 417-line `main.py`, raw SQL, mixed concerns |
> | [`tier-1-resource-based`](../../tree/tier-1-resource-based) | Resource-based routers, REST verbs, Pydantic response models |
> | [`tier-2-layered`](../../tree/tier-2-layered) ← *you are here* | SQLAlchemy 2.0, Alembic, repository + service layers, domain exceptions |
> | `main` (tier 3) *(coming)* | Async SQLAlchemy, Postgres, refresh tokens, rate limiting, CI, Railway deploy |

## The headline lesson of tier 2

**Run `pytest` after this refactor and every test still passes — unchanged.** The internal architecture of the API was overhauled (raw SQL → ORM, monolithic handlers → repos + services + domain exceptions, ad-hoc schema → Alembic-managed migrations), but the external HTTP contract is byte-for-byte identical.

That is the whole point of layering: **clients should not be able to tell when you re-architect**. If your tests had to be rewritten, your "layers" leaked.

## What changed from tier 1

### 1. SQLAlchemy 2.0 ORM (sync)

Tier 1's raw SQL lives directly inside route handlers. Tier 2 introduces declarative models with the modern `Mapped[]` / `mapped_column(...)` syntax:

```python
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    portfolio_items: Mapped[list["PortfolioItem"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
```

Note: **sync**, not async. Async is tier 3's lesson — don't bundle two big concepts into one branch.

### 2. Alembic migrations

The tier-1 `init_db()` function (which called `CREATE TABLE IF NOT EXISTS` at app startup) is **gone**. Schema is now owned by Alembic:

```bash
alembic upgrade head     # apply all migrations
alembic downgrade -1     # roll back one
alembic revision --autogenerate -m "add foo column"   # after editing models
```

The initial migration (`alembic/versions/0001_initial_schema.py`) creates the same schema tier 1 had. From tier 2 onward, every schema change is a code-reviewed, version-controlled migration file.

### 3. Repository layer (`app/repositories/`)

Pure data access. Each repository takes a `Session` and exposes a small focused API:

```python
class UserRepository:
    def get_by_email(self, email: str) -> User | None
    def get(self, user_id: int) -> User | None
    def create(self, *, email: str, password_hash: str) -> User
```

Repositories know about ORM models. They do **not** know about HTTP, FastAPI, Pydantic, or business rules.

### 4. Service layer (`app/services/`)

Business logic. Services receive repositories via the constructor and orchestrate them:

```python
class AuthService:
    def register(self, email: str, password: str) -> User:
        if self.users.get_by_email(email) is not None:
            raise EmailAlreadyRegistered()
        user = self.users.create(email=email, password_hash=hash_password(password))
        self.db.commit()
        return user
```

Services raise **domain exceptions**, never `HTTPException`. This makes them reusable from CLI scripts, background workers, or tests — none of which know what HTTP is.

### 5. Domain exceptions (`app/exceptions.py`)

A small hierarchy under `DomainError`:

| Exception | HTTP | Detail |
|---|---|---|
| `EmailAlreadyRegistered` | 409 | Email already registered |
| `InvalidCredentials` | 401 | Invalid email or password |
| `CoinNotFound` | 404 | Coin not found |
| `AlreadyInPortfolio` | 409 | Coin already in portfolio |
| `NotInPortfolio` | 404 | Coin not in portfolio |
| `ProviderUnavailable` | 502 | Upstream price provider failed |

Translation happens in **one place** — a single exception handler in `app/main.py`:

```python
@app.exception_handler(DomainError)
async def handle_domain_error(_: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
```

### 6. Routers shrink to almost nothing

Compare tier 1's `add_to_portfolio` (~25 lines of SQL + checks + raises) to tier 2:

```python
@router.post("", response_model=PortfolioItemResponse, status_code=201)
def add_to_portfolio(
    payload: PortfolioAddRequest,
    user: CurrentUserDep,
    service: PortfolioServiceDep,
) -> PortfolioItemResponse:
    item = service.add(user.id, payload.coin_id)
    return _to_response(item)
```

That's the goal: **routers parse, services decide, repositories persist**.

### 7. DB session as a dependency

```python
DbDep = Annotated[Session, Depends(get_db)]

def get_auth_service(db: DbDep) -> AuthService:
    return AuthService(db, UserRepository(db))

AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
```

Wiring lives in `deps.py`. Routers stay declarative. Testing a service in isolation = pass a mock `Session`, no FastAPI involved.

## Folder layout (additions over tier 1)

```
app/
├── exceptions.py         # NEW: DomainError + concrete subclasses
├── db.py                 # REWRITTEN: SQLAlchemy engine + SessionLocal + get_db()
├── deps.py               # + DbDep + service factories
├── main.py               # + DomainError exception handler; init_db lifespan removed
├── models/               # NEW: SQLAlchemy 2.0 declarative models
│   ├── base.py
│   ├── user.py
│   ├── coin.py
│   └── portfolio.py
├── repositories/         # NEW: pure data access
│   ├── user.py
│   ├── coin.py
│   └── portfolio.py
├── services/             # NEW: business logic
│   ├── auth.py
│   ├── coin.py
│   └── portfolio.py
└── routers/...           # SHRUNK: 5–8 lines per handler
alembic/
├── env.py                # reads DATABASE_URL from app.config
└── versions/0001_initial_schema.py
alembic.ini
```

## Run it

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

alembic upgrade head      # create the schema
uvicorn app.main:app --reload
```

Open http://localhost:8000/docs.

## Test it

```bash
pytest -v
```

The same 17 tests from tier 1 pass on tier 2 with **zero edits**. Tests use `Base.metadata.create_all(engine)` against a tmp SQLite file — fast, deterministic, no Alembic needed for the test path. Alembic is for production schema management.

## Design decisions worth knowing

1. **Why repositories *and* services?** Repos answer "how do I store/retrieve this row?" Services answer "what does the business want to happen?" Mixing them puts SQL next to password hashing, and you can never test one without the other. With separation, services can be unit-tested with a fake repository — no DB needed.

2. **Why sync SQLAlchemy in tier 2?** Async adds a second axis of complexity (event loop, `await` everywhere, async test fixtures, async session). Tier 2's lesson is *layering*; tier 3's lesson is *async + Postgres*. Mixing both into tier 2 muddies which technique solves which problem.

3. **Why Alembic now?** Tier 1's `init_db()` was a teaching shortcut — fine for one schema, fatal once you ship. Alembic forces students to learn migrations *before* they have a production DB to break. The first migration is the safety net for everything that follows.

4. **Why domain exceptions, not HTTPException?** Services should be reusable from CLI scripts, background workers, tests — none of which know what HTTP is. Pushing HTTP awareness to a single exception handler keeps the domain layer portable. If you ever expose the same logic over gRPC or a CLI, only the handler changes.

5. **Why `Base.metadata.create_all` in tests but Alembic in production?** Alembic per test is slow and overkill — its job is *managing change over time*, not bootstrapping from empty. Tests want a clean slate every run; production wants reproducible upgrades. Different tools for different jobs.

6. **Why `service.commit()` and not the route handler?** A unit of work is a *business operation*, not an HTTP request. Today they map 1:1; tomorrow a service may run two sub-operations in one transaction or call another service. Keeping commits inside services makes that future trivial.

## What tier 3 will add

- **Async SQLAlchemy** + Postgres on Railway (via `DATABASE_URL`)
- **Refresh tokens** + token rotation (the #1 thing junior devs get wrong)
- **Rate limiting** on auth endpoints
- **Structured logging** + request IDs
- **CI pipeline** running pytest + alembic check on every PR
- **Provider abstraction** — `PriceProvider` protocol, with both CoinGecko and CoinCap (opt-in via API key) implementations

The contract still won't change. Diff `tier-2...main` to see what production-grade FastAPI actually looks like.
