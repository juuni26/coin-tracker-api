import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ProviderUnavailable
from app.models import Coin
from app.providers.base import PriceProvider
from app.repositories.coin import CoinRepository


class CoinService:
    def __init__(
        self, db: AsyncSession, coins: CoinRepository, provider: PriceProvider
    ) -> None:
        self.db = db
        self.coins = coins
        self.provider = provider

    async def list_coins(self) -> list[Coin]:
        return await self.coins.list_all()

    async def refresh_from_provider(self) -> tuple[int, str]:
        try:
            market_coins = await self.provider.fetch_market_coins()
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(f"Upstream price provider failed: {exc}")

        count = await self.coins.upsert_many(market_coins)
        await self.db.commit()
        return count, self.provider.name
