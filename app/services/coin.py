import httpx
from sqlalchemy.orm import Session

from app.exceptions import ProviderUnavailable
from app.models import Coin
from app.providers.coingecko import fetch_market_coins
from app.repositories.coin import CoinRepository


class CoinService:
    def __init__(self, db: Session, coins: CoinRepository) -> None:
        self.db = db
        self.coins = coins

    def list_coins(self) -> list[Coin]:
        return self.coins.list_all()

    def refresh_from_provider(self) -> int:
        try:
            market_coins = fetch_market_coins()
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(f"Upstream price provider failed: {exc}")

        count = self.coins.upsert_many(market_coins)
        self.db.commit()
        return count
