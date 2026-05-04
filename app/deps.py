from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.providers import get_price_provider
from app.providers.base import PriceProvider
from app.repositories.coin import CoinRepository
from app.repositories.portfolio import PortfolioRepository
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import UserRepository
from app.security import decode_access_token
from app.services.auth import AuthService
from app.services.coin import CoinService
from app.services.portfolio import PortfolioService


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

DbDep = Annotated[AsyncSession, Depends(get_db)]


class CurrentUser(BaseModel):
    id: int
    email: str


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> CurrentUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
    except ValueError:
        raise credentials_exception

    user_id = payload.get("user_id")
    email = payload.get("sub")
    if user_id is None or email is None:
        raise credentials_exception
    return CurrentUser(id=user_id, email=email)


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


def get_provider() -> PriceProvider:
    return get_price_provider()


def get_auth_service(db: DbDep) -> AuthService:
    return AuthService(db, UserRepository(db), RefreshTokenRepository(db))


def get_coin_service(
    db: DbDep, provider: Annotated[PriceProvider, Depends(get_provider)]
) -> CoinService:
    return CoinService(db, CoinRepository(db), provider)


def get_portfolio_service(db: DbDep) -> PortfolioService:
    return PortfolioService(db, PortfolioRepository(db), CoinRepository(db))


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
CoinServiceDep = Annotated[CoinService, Depends(get_coin_service)]
PortfolioServiceDep = Annotated[PortfolioService, Depends(get_portfolio_service)]
