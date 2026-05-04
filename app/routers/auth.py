import sqlite3

from fastapi import APIRouter, HTTPException, Response, status

from app.db import get_connection
from app.deps import CurrentUserDep
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.security import create_access_token, hash_password, verify_password


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(payload: RegisterRequest) -> TokenResponse:
    with get_connection() as con:
        try:
            cur = con.execute(
                "INSERT INTO users (email, password_hash) VALUES (?, ?)",
                (payload.email, hash_password(payload.password)),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        user_id = cur.lastrowid

    token = create_access_token(user_id=user_id, email=payload.email)
    return TokenResponse(access_token=token, email=payload.email)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    with get_connection() as con:
        row = con.execute(
            "SELECT id, password_hash FROM users WHERE email = ?",
            (payload.email,),
        ).fetchone()

    if row is None or not verify_password(payload.password, row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(user_id=row["id"], email=payload.email)
    return TokenResponse(access_token=token, email=payload.email)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(_: CurrentUserDep) -> Response:
    # Stateless JWT: client discards the token. Server has nothing to revoke at tier 1.
    return Response(status_code=status.HTTP_204_NO_CONTENT)
