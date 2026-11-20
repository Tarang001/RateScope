from fastapi import Depends

from app.core.config import Settings, get_settings
from app.core.security import require_api_key


def auth(_: str = Depends(require_api_key)) -> None:
    return None


def settings_dep() -> Settings:
    return get_settings()
