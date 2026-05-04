from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import EmailAlreadyRegistered, InvalidCredentials
from app.models import User
from app.repositories.user import UserRepository
from app.security import create_access_token, hash_password, verify_password


class AuthService:
    def __init__(self, db: Session, users: UserRepository) -> None:
        self.db = db
        self.users = users

    def register(self, email: str, password: str) -> User:
        if self.users.get_by_email(email) is not None:
            raise EmailAlreadyRegistered()
        try:
            user = self.users.create(email=email, password_hash=hash_password(password))
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise EmailAlreadyRegistered()
        self.db.refresh(user)
        return user

    def authenticate(self, email: str, password: str) -> User:
        user = self.users.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentials()
        return user

    def issue_token(self, user: User) -> str:
        return create_access_token(user_id=user.id, email=user.email)
