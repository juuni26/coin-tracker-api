from sqlalchemy import delete, select
from sqlalchemy.orm import Session, joinedload

from app.models import PortfolioItem


class PortfolioRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_user(self, user_id: int) -> list[PortfolioItem]:
        stmt = (
            select(PortfolioItem)
            .options(joinedload(PortfolioItem.coin))
            .where(PortfolioItem.user_id == user_id)
            .order_by(PortfolioItem.added_at.desc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def get(self, user_id: int, coin_id: int) -> PortfolioItem | None:
        stmt = (
            select(PortfolioItem)
            .options(joinedload(PortfolioItem.coin))
            .where(PortfolioItem.user_id == user_id, PortfolioItem.coin_id == coin_id)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def add(self, user_id: int, coin_id: int) -> PortfolioItem:
        item = PortfolioItem(user_id=user_id, coin_id=coin_id)
        self.db.add(item)
        self.db.flush()
        self.db.refresh(item, attribute_names=["coin", "added_at"])
        return item

    def remove(self, user_id: int, coin_id: int) -> bool:
        stmt = delete(PortfolioItem).where(
            PortfolioItem.user_id == user_id, PortfolioItem.coin_id == coin_id
        )
        result = self.db.execute(stmt)
        return result.rowcount > 0
