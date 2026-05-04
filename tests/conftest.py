import os
import secrets
import string
from datetime import datetime, timezone
from pathlib import Path

import pytest
import pytest_asyncio


@pytest.fixture(scope="session", autouse=True)
def _isolated_db(tmp_path_factory):
    db_file: Path = tmp_path_factory.mktemp("data") / "test.db"
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_file}"
    os.environ["JWT_SECRET_KEY"] = "test-secret-key"
    os.environ["RATE_LIMIT_ENABLED"] = "false"
    os.environ.pop("COINCAP_API_KEY", None)
    yield
    if db_file.exists():
        db_file.unlink()


@pytest_asyncio.fixture()
async def client(_isolated_db):
    from httpx import ASGITransport, AsyncClient

    from app.db import engine
    from app.main import app
    from app.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@pytest.fixture()
def random_credentials() -> dict:
    suffix = "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))
    password = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
    return {"email": f"test_{suffix}@example.com", "password": password}


@pytest_asyncio.fixture()
async def seed_coin():
    """Insert a fake coin via the async ORM session."""
    from app.db import SessionLocal
    from app.models import Coin

    async def _seed(
        external_id: str = "bitcoin", name: str = "Bitcoin", symbol: str = "BTC"
    ) -> int:
        async with SessionLocal() as db:
            coin = Coin(
                external_id=external_id,
                name=name,
                symbol=symbol,
                market_cap_rank=1,
                price_usd=50000.0,
                image_url="https://example.com/btc.png",
                last_updated=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            db.add(coin)
            await db.commit()
            await db.refresh(coin)
            return coin.id

    return _seed
