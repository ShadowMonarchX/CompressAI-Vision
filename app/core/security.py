from fastapi import Header

from app.core.config import settings
from app.core.exceptions import UnauthorizedError


async def require_api_key(x_api_key: str | None = Header(default=None)) -> bool:
    """Minimal API-key auth; set API_KEY to enable enforcement."""
    if settings.api_key and x_api_key != settings.api_key:
        raise UnauthorizedError("Invalid API key")
    return True
