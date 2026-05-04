from fastapi import APIRouter, status

from app.deps import CoinServiceDep
from app.schemas.coin import CoinRefreshResponse, CoinResponse


router = APIRouter(prefix="/coins", tags=["coins"])


@router.get("", response_model=list[CoinResponse])
async def list_coins(service: CoinServiceDep) -> list[CoinResponse]:
    coins = await service.list_coins()
    return [CoinResponse.model_validate(c, from_attributes=True) for c in coins]


@router.post(
    "/refresh",
    response_model=CoinRefreshResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def refresh_coins(service: CoinServiceDep) -> CoinRefreshResponse:
    count, source = await service.refresh_from_provider()
    return CoinRefreshResponse(refreshed_count=count, source=source)
