import httpx
from fastapi import APIRouter, HTTPException, status

from app.db import get_connection
from app.providers.coingecko import fetch_market_coins
from app.schemas.coin import CoinRefreshResponse, CoinResponse


router = APIRouter(prefix="/coins", tags=["coins"])


@router.get("", response_model=list[CoinResponse])
def list_coins() -> list[CoinResponse]:
    with get_connection() as con:
        rows = con.execute(
            """
            SELECT id, external_id, name, symbol, market_cap_rank,
                   price_usd, image_url, last_updated
            FROM coins
            ORDER BY market_cap_rank IS NULL, market_cap_rank ASC
            """
        ).fetchall()
    return [CoinResponse(**dict(row)) for row in rows]


@router.post(
    "/refresh",
    response_model=CoinRefreshResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def refresh_coins() -> CoinRefreshResponse:
    try:
        coins = fetch_market_coins()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upstream price provider failed: {exc}",
        )

    with get_connection() as con:
        con.executemany(
            """
            INSERT INTO coins (external_id, name, symbol, market_cap_rank,
                               price_usd, image_url, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(external_id) DO UPDATE SET
                name = excluded.name,
                symbol = excluded.symbol,
                market_cap_rank = excluded.market_cap_rank,
                price_usd = excluded.price_usd,
                image_url = excluded.image_url,
                last_updated = excluded.last_updated
            """,
            [
                (
                    c.external_id,
                    c.name,
                    c.symbol,
                    c.market_cap_rank,
                    c.price_usd,
                    c.image_url,
                    c.last_updated.isoformat(),
                )
                for c in coins
            ],
        )

    return CoinRefreshResponse(refreshed_count=len(coins))
