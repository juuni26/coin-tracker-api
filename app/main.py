from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import init_db
from app.routers import auth, coins, portfolio


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Coin Tracker API — Tier 1 (Resource-Based)",
    description=(
        "Teaching example: FastAPI evolution across tiers. "
        "Tier 1 introduces resource-based routers, REST-correct verbs, "
        "and Pydantic response models. Still uses raw sqlite3."
    ),
    version="1.0.0-tier1",
    lifespan=lifespan,
)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(coins.router)
app.include_router(portfolio.router)
