from fastapi import APIRouter, Response, status

from app.deps import CurrentUserDep, PortfolioServiceDep
from app.schemas.coin import CoinResponse
from app.schemas.portfolio import PortfolioAddRequest, PortfolioItemResponse


router = APIRouter(prefix="/portfolio", tags=["portfolio"])


def _to_response(item) -> PortfolioItemResponse:
    return PortfolioItemResponse(
        coin=CoinResponse.model_validate(item.coin, from_attributes=True),
        added_at=item.added_at,
    )


@router.get("", response_model=list[PortfolioItemResponse])
def list_portfolio(
    user: CurrentUserDep, service: PortfolioServiceDep
) -> list[PortfolioItemResponse]:
    return [_to_response(item) for item in service.list_for_user(user.id)]


@router.post(
    "",
    response_model=PortfolioItemResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_to_portfolio(
    payload: PortfolioAddRequest,
    user: CurrentUserDep,
    service: PortfolioServiceDep,
) -> PortfolioItemResponse:
    item = service.add(user.id, payload.coin_id)
    return _to_response(item)


@router.delete("/{coin_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_portfolio(
    coin_id: int, user: CurrentUserDep, service: PortfolioServiceDep
) -> Response:
    service.remove(user.id, coin_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
