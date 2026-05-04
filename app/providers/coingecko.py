from datetime import datetime

import httpx

from app.config import settings
from app.providers.base import MarketCoin


def _parse(item: dict) -> MarketCoin:
    last_updated_raw = item.get("last_updated")
    last_updated = (
        datetime.fromisoformat(last_updated_raw.replace("Z", "+00:00"))
        if last_updated_raw
        else datetime.utcnow()
    )
    return MarketCoin(
        external_id=item["id"],
        name=item["name"],
        symbol=item["symbol"].upper(),
        market_cap_rank=item.get("market_cap_rank"),
        price_usd=float(item["current_price"]),
        image_url=item.get("image"),
        last_updated=last_updated,
    )


class CoinGeckoProvider:
    name = "coingecko"

    def __init__(self, url: str | None = None) -> None:
        self.url = url or settings.COINGECKO_URL

    async def fetch_market_coins(self, per_page: int = 100, page: int = 1) -> list[MarketCoin]:
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": per_page,
            "page": page,
            "sparkline": "false",
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(self.url, params=params)
            response.raise_for_status()
            return [_parse(item) for item in response.json()]
