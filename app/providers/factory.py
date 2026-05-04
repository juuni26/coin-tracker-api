from app.config import settings
from app.providers.base import PriceProvider
from app.providers.coincap import CoinCapProvider
from app.providers.coingecko import CoinGeckoProvider


def get_price_provider() -> PriceProvider:
    """Pick a provider based on configuration.

    If COINCAP_API_KEY is set we prefer CoinCap (paid, more reliable);
    otherwise we use the keyless CoinGecko free tier.
    """
    if settings.COINCAP_API_KEY:
        return CoinCapProvider()
    return CoinGeckoProvider()
