from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import AlreadyInPortfolio, CoinNotFound, NotInPortfolio
from app.models import PortfolioItem
from app.repositories.coin import CoinRepository
from app.repositories.portfolio import PortfolioRepository


class PortfolioService:
    def __init__(
        self,
        db: Session,
        portfolio: PortfolioRepository,
        coins: CoinRepository,
    ) -> None:
        self.db = db
        self.portfolio = portfolio
        self.coins = coins

    def list_for_user(self, user_id: int) -> list[PortfolioItem]:
        return self.portfolio.list_for_user(user_id)

    def add(self, user_id: int, coin_id: int) -> PortfolioItem:
        if self.coins.get(coin_id) is None:
            raise CoinNotFound()
        if self.portfolio.get(user_id, coin_id) is not None:
            raise AlreadyInPortfolio()
        try:
            item = self.portfolio.add(user_id, coin_id)
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise AlreadyInPortfolio()
        # Reload with coin relationship for the response
        return self.portfolio.get(user_id, coin_id)  # type: ignore[return-value]

    def remove(self, user_id: int, coin_id: int) -> None:
        deleted = self.portfolio.remove(user_id, coin_id)
        if not deleted:
            self.db.rollback()
            raise NotInPortfolio()
        self.db.commit()
