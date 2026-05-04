from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import (
    EmailAlreadyRegistered,
    InvalidCredentials,
    InvalidRefreshToken,
)
from app.models import RefreshToken, User
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import UserRepository
from app.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    refresh_token_expires_at,
    verify_password,
)


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    user: User


class AuthService:
    def __init__(
        self,
        db: AsyncSession,
        users: UserRepository,
        refresh_tokens: RefreshTokenRepository,
    ) -> None:
        self.db = db
        self.users = users
        self.refresh_tokens = refresh_tokens

    async def register(self, email: str, password: str) -> TokenPair:
        if await self.users.get_by_email(email) is not None:
            raise EmailAlreadyRegistered()
        try:
            user = await self.users.create(
                email=email, password_hash=hash_password(password)
            )
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
            raise EmailAlreadyRegistered()

        pair = await self._issue_pair(user)
        await self.db.commit()
        return pair

    async def authenticate(self, email: str, password: str) -> TokenPair:
        user = await self.users.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentials()
        pair = await self._issue_pair(user)
        await self.db.commit()
        return pair

    async def refresh(self, refresh_token: str) -> TokenPair:
        token_hash = hash_refresh_token(refresh_token)
        existing = await self.refresh_tokens.get_active_by_hash(token_hash)
        if existing is None:
            raise InvalidRefreshToken()

        user = await self.users.get(existing.user_id)
        if user is None:
            raise InvalidRefreshToken()

        # Rotation: revoke the old token, issue a fresh pair.
        await self.refresh_tokens.revoke(existing.id)
        pair = await self._issue_pair(user)
        await self.db.commit()
        return pair

    async def logout(self, refresh_token: str) -> None:
        """Revoke a single refresh token. Idempotent — unknown tokens are a no-op."""
        token_hash = hash_refresh_token(refresh_token)
        existing = await self.refresh_tokens.get_active_by_hash(token_hash)
        if existing is not None:
            await self.refresh_tokens.revoke(existing.id)
            await self.db.commit()

    async def _issue_pair(self, user: User) -> TokenPair:
        access = create_access_token(user_id=user.id, email=user.email)
        refresh = generate_refresh_token()
        await self.refresh_tokens.create(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh),
            expires_at=refresh_token_expires_at(),
        )
        return TokenPair(access_token=access, refresh_token=refresh, user=user)
