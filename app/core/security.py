from fastapi import Header
from app.core.exceptions import AppError
from app.core.config import settings

async def require_api_key(x_api_key: str | None = Header(default=None)):
    """Minimal API-key auth; set API_KEY to enable enforcement."""
    if settings.api_key and x_api_key != settings.api_key:
        error = AppError('Invalid API key')
        error.status_code = 401
        error.error_code = 'unauthorized'
        raise error
    return True
