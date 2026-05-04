"""Domain exceptions. Services raise these; the FastAPI layer translates them to HTTP."""


class DomainError(Exception):
    """Base for all domain-level errors."""

    status_code: int = 400
    detail: str = "Domain error"

    def __init__(self, detail: str | None = None) -> None:
        if detail is not None:
            self.detail = detail
        super().__init__(self.detail)


class EmailAlreadyRegistered(DomainError):
    status_code = 409
    detail = "Email already registered"


class InvalidCredentials(DomainError):
    status_code = 401
    detail = "Invalid email or password"


class CoinNotFound(DomainError):
    status_code = 404
    detail = "Coin not found"


class AlreadyInPortfolio(DomainError):
    status_code = 409
    detail = "Coin already in portfolio"


class NotInPortfolio(DomainError):
    status_code = 404
    detail = "Coin not in portfolio"


class ProviderUnavailable(DomainError):
    status_code = 502
    detail = "Upstream price provider failed"
