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
    os.environ["DB_PATH"] = str(db_file)
    os.environ["JWT_SECRET_KEY"] = "test-secret-key"
    yield
    if db_file.exists():
        db_file.unlink()


@pytest.fixture()
def client(_isolated_db):
    from fastapi.testclient import TestClient
    from app.db import init_db
    from app.main import app

    init_db()
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def random_credentials() -> dict:
    suffix = "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))
    password = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
    return {"email": f"test_{suffix}@example.com", "password": password}


@pytest.fixture()
def seed_coin():
    """Insert a fake coin row directly so tests don't depend on the live CoinGecko API."""
    from app.db import get_connection

    def _seed(external_id: str = "bitcoin", name: str = "Bitcoin", symbol: str = "BTC") -> int:
        with get_connection() as con:
            cur = con.execute(
                """
                INSERT INTO coins (external_id, name, symbol, market_cap_rank,
                                   price_usd, image_url, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(external_id) DO UPDATE SET name = excluded.name
                RETURNING id
                """,
                (
                    external_id,
                    name,
                    symbol,
                    1,
                    50000.0,
                    "https://example.com/btc.png",
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            return cur.fetchone()[0]

    return _seed
