from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.exceptions import DomainError
from app.rate_limit import limiter
from app.routers import auth, coins, portfolio


app = FastAPI(
    title="Coin Tracker API — Tier 3 (Production)",
    description=(
        "Teaching example: FastAPI evolution across tiers. "
        "Tier 3 is the production target — async SQLAlchemy, Postgres-ready, "
        "refresh-token rotation, rate limiting, provider abstraction, and a "
        "Railway deploy config."
    ),
    version="3.0.0-tier3",
)

# Rate limiting (slowapi)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def handle_rate_limit(_: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429, content={"detail": f"Rate limit exceeded: {exc.detail}"}
    )


@app.exception_handler(DomainError)
async def handle_domain_error(_: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.get("/health", tags=["meta"])
async def health() -> dict:
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(coins.router)
app.include_router(portfolio.router)
