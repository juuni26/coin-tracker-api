from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import AlreadyInPortfolio, CoinNotFound, NotInPortfolio
from app.models import PortfolioItem
from app.repositories.coin import CoinRepository
from app.repositories.portfolio import PortfolioRepository


class PortfolioService:
    def __init__(
        self,
        db: AsyncSession,
        portfolio: PortfolioRepository,
        coins: CoinRepository,
    ) -> None:
        self.db = db
        self.portfolio = portfolio
        self.coins = coins

    async def list_for_user(self, user_id: int) -> list[PortfolioItem]:
        return await self.portfolio.list_for_user(user_id)

    async def add(self, user_id: int, coin_id: int) -> PortfolioItem:
        if await self.coins.get(coin_id) is None:
            raise CoinNotFound()
        if await self.portfolio.get(user_id, coin_id) is not None:
            raise AlreadyInPortfolio()
        try:
            await self.portfolio.add(user_id, coin_id)
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise AlreadyInPortfolio()

        item = await self.portfolio.get(user_id, coin_id)
        assert item is not None
        return item

    async def remove(self, user_id: int, coin_id: int) -> None:
        deleted = await self.portfolio.remove(user_id, coin_id)
        if not deleted:
            await self.db.rollback()
            raise NotInPortfolio()
        await self.db.commit()
