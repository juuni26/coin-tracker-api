from sqlalchemy import nulls_last, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Coin
from app.providers.base import MarketCoin


class CoinRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_all(self) -> list[Coin]:
        stmt = select(Coin).order_by(nulls_last(Coin.market_cap_rank.asc()))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get(self, coin_id: int) -> Coin | None:
        return await self.db.get(Coin, coin_id)

    async def upsert_many(self, coins: list[MarketCoin]) -> int:
        if not coins:
            return 0

        rows = [
            {
                "external_id": c.external_id,
                "name": c.name,
                "symbol": c.symbol,
                "market_cap_rank": c.market_cap_rank,
                "price_usd": c.price_usd,
                "image_url": c.image_url,
                "last_updated": c.last_updated,
            }
            for c in coins
        ]

        dialect = self.db.bind.dialect.name if self.db.bind else ""
        if dialect == "postgresql":
            stmt = postgresql_insert(Coin).values(rows)
            stmt = stmt.on_conflict_do_update(
                index_elements=[Coin.external_id],
                set_={
                    "name": stmt.excluded.name,
                    "symbol": stmt.excluded.symbol,
                    "market_cap_rank": stmt.excluded.market_cap_rank,
                    "price_usd": stmt.excluded.price_usd,
                    "image_url": stmt.excluded.image_url,
                    "last_updated": stmt.excluded.last_updated,
                },
            )
        else:
            # SQLite path (also covers aiosqlite)
            stmt = sqlite_insert(Coin).values(rows)
            stmt = stmt.on_conflict_do_update(
                index_elements=[Coin.external_id],
                set_={
                    "name": stmt.excluded.name,
                    "symbol": stmt.excluded.symbol,
                    "market_cap_rank": stmt.excluded.market_cap_rank,
                    "price_usd": stmt.excluded.price_usd,
                    "image_url": stmt.excluded.image_url,
                    "last_updated": stmt.excluded.last_updated,
                },
            )

        await self.db.execute(stmt)
        return len(rows)
