import os
import secrets
import string
from datetime import datetime, timezone
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def _isolated_db(tmp_path_factory):
    """Point the app at a throwaway SQLite file for the whole test session."""
    db_file: Path = tmp_path_factory.mktemp("data") / "test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"
    os.environ["JWT_SECRET_KEY"] = "test-secret-key"
    yield
    if db_file.exists():
        db_file.unlink()


@pytest.fixture()
def client(_isolated_db):
    # Import inside the fixture so env vars are set before the engine is built.
    from fastapi.testclient import TestClient

    from app.db import engine
    from app.main import app
    from app.models import Base

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def random_credentials() -> dict:
    suffix = "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))
    password = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
    return {"email": f"test_{suffix}@example.com", "password": password}


@pytest.fixture()
def seed_coin():
    """Insert a fake coin row directly via ORM so tests don't depend on CoinGecko."""
    from app.db import SessionLocal
    from app.models import Coin

    def _seed(external_id: str = "bitcoin", name: str = "Bitcoin", symbol: str = "BTC") -> int:
        with SessionLocal() as db:
            coin = Coin(
                external_id=external_id,
                name=name,
                symbol=symbol,
                market_cap_rank=1,
                price_usd=50000.0,
                image_url="https://example.com/btc.png",
                last_updated=datetime.now(timezone.utc),
            )
            db.add(coin)
            db.commit()
            db.refresh(coin)
            return coin.id

    return _seed
