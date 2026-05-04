from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class MarketCoin:
    external_id: str
    name: str
    symbol: str
    market_cap_rank: int | None
    price_usd: float
    image_url: str | None
    last_updated: datetime


class PriceProvider(Protocol):
    """Anything that can fetch a snapshot of market data.

    Implementations live in app/providers/{coingecko,coincap}.py and are
    selected by app.providers.factory.get_price_provider().
    """

    name: str

    async def fetch_market_coins(self) -> list[MarketCoin]: ...
