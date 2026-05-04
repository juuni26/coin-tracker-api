from dataclasses import dataclass
from datetime import datetime

import httpx

from app.config import settings


@dataclass(frozen=True)
class MarketCoin:
    external_id: str
    name: str
    symbol: str
    market_cap_rank: int | None
    price_usd: float
    image_url: str | None
    last_updated: datetime


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


def fetch_market_coins(per_page: int = 100, page: int = 1) -> list[MarketCoin]:
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": per_page,
        "page": page,
        "sparkline": "false",
    }
    with httpx.Client(timeout=15.0) as client:
        response = client.get(settings.COINGECKO_URL, params=params)
        response.raise_for_status()
        return [_parse(item) for item in response.json()]
