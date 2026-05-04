import os
from dotenv import load_dotenv

load_dotenv()


def _normalize_database_url(raw: str) -> str:
    """Normalize DATABASE_URL to an async-compatible SQLAlchemy URL.

    Railway and Heroku-style providers set DATABASE_URL=postgres://..., but
    SQLAlchemy 2.0 requires postgresql+asyncpg://... for async connections.
    Plain sqlite:// also needs +aiosqlite for async.
    """
    if raw.startswith("postgres://"):
        raw = raw.replace("postgres://", "postgresql+asyncpg://", 1)
    elif raw.startswith("postgresql://") and "+asyncpg" not in raw:
        raw = raw.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif raw.startswith("sqlite://") and "+aiosqlite" not in raw:
        raw = raw.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return raw


def _bool(v: str | None, default: bool) -> bool:
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "dev-only-insecure-key")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "14"))

    DATABASE_URL: str = _normalize_database_url(
        os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./tracker_coin.db")
    )

    COINGECKO_URL: str = os.getenv(
        "COINGECKO_URL", "https://api.coingecko.com/api/v3/coins/markets"
    )
    COINCAP_API_KEY: str | None = os.getenv("COINCAP_API_KEY") or None
    COINCAP_URL: str = os.getenv("COINCAP_URL", "https://rest.coincap.io/v3/assets")

    RATE_LIMIT_ENABLED: bool = _bool(os.getenv("RATE_LIMIT_ENABLED"), True)


settings = Settings()
