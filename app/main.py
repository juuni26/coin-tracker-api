from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.exceptions import DomainError
from app.routers import auth, coins, portfolio


app = FastAPI(
    title="Coin Tracker API — Tier 2 (Layered + ORM)",
    description=(
        "Teaching example: FastAPI evolution across tiers. "
        "Tier 2 introduces SQLAlchemy 2.0, Alembic migrations, and "
        "repository + service layers. External API contract is identical to tier 1."
    ),
    version="2.0.0-tier2",
)


@app.exception_handler(DomainError)
async def handle_domain_error(_: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(coins.router)
app.include_router(portfolio.router)
