from fastapi import APIRouter, Request, Response, status

from app.deps import AuthServiceDep
from app.rate_limit import limiter
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)


router = APIRouter(prefix="/auth", tags=["auth"])


def _to_token_response(pair) -> TokenResponse:
    return TokenResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        email=pair.user.email,
    )


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("3/minute")
async def register(
    request: Request, payload: RegisterRequest, auth: AuthServiceDep
) -> TokenResponse:
    pair = await auth.register(payload.email, payload.password)
    return _to_token_response(pair)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request, payload: LoginRequest, auth: AuthServiceDep
) -> TokenResponse:
    pair = await auth.authenticate(payload.email, payload.password)
    return _to_token_response(pair)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
async def refresh(
    request: Request, payload: RefreshRequest, auth: AuthServiceDep
) -> TokenResponse:
    pair = await auth.refresh(payload.refresh_token)
    return _to_token_response(pair)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: LogoutRequest, auth: AuthServiceDep) -> Response:
    await auth.logout(payload.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
