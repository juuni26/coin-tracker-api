from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.coin import CoinResponse


class PortfolioAddRequest(BaseModel):
    coin_id: int = Field(gt=0)


class PortfolioItemResponse(BaseModel):
    coin: CoinResponse
    added_at: datetime
