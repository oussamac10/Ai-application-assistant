import logging

from fastapi import APIRouter, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.ai.factory import get_provider
from app.database.session import engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health")


@router.get("", status_code=status.HTTP_200_OK)
def check_health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/database")
def check_database_health() -> Response:
    try:
        # Try to obtain a connection and execute SELECT 1
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return JSONResponse(
            content={"status": "ok", "database": "connected"},
            status_code=status.HTTP_200_OK,
        )
    except Exception as e:
        logger.error("Database connection failure check: %s", str(e))
        return JSONResponse(
            content={"status": "error", "database": "unavailable"},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


@router.get("/ai")
async def check_ai_health() -> Response:
    """Check whether the configured AI provider is reachable.

    Returns 200 when healthy, 503 when unavailable.
    The provider name is included in the response but no sensitive
    configuration values (URLs, tokens, model internals) are exposed.
    """
    try:
        provider = get_provider()
        healthy = await provider.health_check()
        provider_name = type(provider).__name__

        if healthy:
            return JSONResponse(
                content={"status": "ok", "provider": provider_name},
                status_code=status.HTTP_200_OK,
            )
        return JSONResponse(
            content={"status": "unavailable", "provider": provider_name},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except Exception:
        logger.exception("AI health check failed")
        return JSONResponse(
            content={"status": "error", "provider": "unknown"},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
