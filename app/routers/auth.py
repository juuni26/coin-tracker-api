from fastapi import APIRouter, Response, status

from app.deps import AuthServiceDep, CurrentUserDep
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(payload: RegisterRequest, auth: AuthServiceDep) -> TokenResponse:
    user = auth.register(payload.email, payload.password)
    return TokenResponse(access_token=auth.issue_token(user), email=user.email)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, auth: AuthServiceDep) -> TokenResponse:
    user = auth.authenticate(payload.email, payload.password)
    return TokenResponse(access_token=auth.issue_token(user), email=user.email)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(_: CurrentUserDep) -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)
