from fastapi import Header, HTTPException, Request

from app.core.config import get_settings

PUBLIC_PATHS = {"/api/v1/health/live", "/api/v1/health/ready", "/metrics", "/docs", "/openapi.json", "/redoc"}


def require_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> str:
    settings = get_settings()
    provided = x_api_key or request.query_params.get("api_key")
    if provided != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return provided


def is_public_path(path: str) -> bool:
    return path in PUBLIC_PATHS or path.startswith("/docs") or path.startswith("/redoc")


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
