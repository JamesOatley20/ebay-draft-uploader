"""An OAuth User token for this process only. No credential storage or refresh."""

from . import AppError

SCOPES = "https://api.ebay.com/oauth/api_scope https://api.ebay.com/oauth/api_scope/sell.inventory"


class AuthExpired(AppError):
    """Stop the queue; never replay a write under a replacement identity."""


class Auth:
    def __init__(self, token: str) -> None:
        if not isinstance(token, str) or not token or any(c.isspace() for c in token):
            raise AppError("Enter only the Production OAuth User token, without Bearer or spaces.")
        self._token = token

    def user_token(self) -> str:
        if not self._token:
            raise AuthExpired("This session has ended. A new run needs a User token.")
        return self._token

    def redact(self, message: str) -> str:
        return message.replace(self._token, "[REDACTED]") if self._token else message

    def close(self) -> None:
        # Drop references; do not promise forensic erasure of Python/OS memory.
        self._token = ""
