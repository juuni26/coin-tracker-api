from datetime import datetime

from pydantic import BaseModel, Field


class CoinResponse(BaseModel):
    id: int
    external_id: str = Field(description="Provider's slug, e.g. 'bitcoin'")
    name: str
    symbol: str
    market_cap_rank: int | None
    price_usd: float
    image_url: str | None
    last_updated: datetime


class CoinRefreshResponse(BaseModel):
    refreshed_count: int
    source: str
