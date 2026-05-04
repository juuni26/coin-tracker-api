import sqlite3

from fastapi import APIRouter, HTTPException, Response, status

from app.db import get_connection
from app.deps import CurrentUserDep
from app.schemas.coin import CoinResponse
from app.schemas.portfolio import PortfolioAddRequest, PortfolioItemResponse


router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("", response_model=list[PortfolioItemResponse])
def list_portfolio(user: CurrentUserDep) -> list[PortfolioItemResponse]:
    with get_connection() as con:
        rows = con.execute(
            """
            SELECT
                c.id, c.external_id, c.name, c.symbol, c.market_cap_rank,
                c.price_usd, c.image_url, c.last_updated,
                p.added_at
            FROM portfolio p
            JOIN coins c ON c.id = p.coin_id
            WHERE p.user_id = ?
            ORDER BY p.added_at DESC
            """,
            (user.id,),
        ).fetchall()

    return [
        PortfolioItemResponse(
            coin=CoinResponse(
                id=row["id"],
                external_id=row["external_id"],
                name=row["name"],
                symbol=row["symbol"],
                market_cap_rank=row["market_cap_rank"],
                price_usd=row["price_usd"],
                image_url=row["image_url"],
                last_updated=row["last_updated"],
            ),
            added_at=row["added_at"],
        )
        for row in rows
    ]


@router.post(
    "",
    response_model=PortfolioItemResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_to_portfolio(
    payload: PortfolioAddRequest, user: CurrentUserDep
) -> PortfolioItemResponse:
    with get_connection() as con:
        coin_row = con.execute(
            """
            SELECT id, external_id, name, symbol, market_cap_rank,
                   price_usd, image_url, last_updated
            FROM coins WHERE id = ?
            """,
            (payload.coin_id,),
        ).fetchone()
        if coin_row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Coin not found",
            )

        try:
            con.execute(
                "INSERT INTO portfolio (user_id, coin_id) VALUES (?, ?)",
                (user.id, payload.coin_id),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Coin already in portfolio",
            )

        added_at_row = con.execute(
            "SELECT added_at FROM portfolio WHERE user_id = ? AND coin_id = ?",
            (user.id, payload.coin_id),
        ).fetchone()

    return PortfolioItemResponse(
        coin=CoinResponse(**dict(coin_row)),
        added_at=added_at_row["added_at"],
    )


@router.delete("/{coin_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_portfolio(coin_id: int, user: CurrentUserDep) -> Response:
    with get_connection() as con:
        cur = con.execute(
            "DELETE FROM portfolio WHERE user_id = ? AND coin_id = ?",
            (user.id, coin_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Coin not in portfolio",
            )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
