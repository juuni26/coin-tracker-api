from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import PortfolioItem


class PortfolioRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_for_user(self, user_id: int) -> list[PortfolioItem]:
        stmt = (
            select(PortfolioItem)
            .options(selectinload(PortfolioItem.coin))
            .where(PortfolioItem.user_id == user_id)
            .order_by(PortfolioItem.added_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get(self, user_id: int, coin_id: int) -> PortfolioItem | None:
        stmt = (
            select(PortfolioItem)
            .options(selectinload(PortfolioItem.coin))
            .where(PortfolioItem.user_id == user_id, PortfolioItem.coin_id == coin_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def add(self, user_id: int, coin_id: int) -> PortfolioItem:
        item = PortfolioItem(user_id=user_id, coin_id=coin_id)
        self.db.add(item)
        await self.db.flush()
        return item

    async def remove(self, user_id: int, coin_id: int) -> bool:
        stmt = delete(PortfolioItem).where(
            PortfolioItem.user_id == user_id, PortfolioItem.coin_id == coin_id
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0
