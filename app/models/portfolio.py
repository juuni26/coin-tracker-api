from datetime import datetime

from sqlalchemy import ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.coin import Coin
from app.models.user import User


class PortfolioItem(Base):
    __tablename__ = "portfolio"
    __table_args__ = (UniqueConstraint("user_id", "coin_id", name="uq_portfolio_user_coin"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    coin_id: Mapped[int] = mapped_column(
        ForeignKey("coins.id", ondelete="CASCADE"), nullable=False
    )
    added_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="portfolio_items")
    coin: Mapped["Coin"] = relationship()
