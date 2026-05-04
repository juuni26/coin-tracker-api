from datetime import datetime, timezone

import httpx

from app.config import settings
from app.providers.base import MarketCoin


def _parse(item: dict) -> MarketCoin:
    rank_raw = item.get("rank")
    rank = int(rank_raw) if rank_raw is not None else None

    return MarketCoin(
        external_id=item["id"],
        name=item["name"],
        symbol=str(item.get("symbol", "")).upper(),
        market_cap_rank=rank,
        price_usd=float(item["priceUsd"]),
        image_url=None,
        # CoinCap returns ms-since-epoch in `time`
        last_updated=datetime.fromtimestamp(item.get("time", 0) / 1000, tz=timezone.utc),
    )


class CoinCapProvider:
    """CoinCap pro endpoint — requires an API key (Bearer header).

    Selected automatically when COINCAP_API_KEY is set; otherwise the app
    falls back to the keyless CoinGecko provider.
    """

    name = "coincap"

    def __init__(self, api_key: str | None = None, url: str | None = None) -> None:
        self.api_key = api_key or settings.COINCAP_API_KEY
        if not self.api_key:
            raise ValueError("CoinCapProvider requires COINCAP_API_KEY")
        self.url = url or settings.COINCAP_URL

    async def fetch_market_coins(self, limit: int = 100) -> list[MarketCoin]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        params = {"limit": limit}
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(self.url, headers=headers, params=params)
            response.raise_for_status()
            return [_parse(item) for item in response.json().get("data", [])]
