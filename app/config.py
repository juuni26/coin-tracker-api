import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "dev-only-insecure-key")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "40"))
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./tracker_coin.db")
    COINGECKO_URL: str = os.getenv(
        "COINGECKO_URL", "https://api.coingecko.com/api/v3/coins/markets"
    )


settings = Settings()
