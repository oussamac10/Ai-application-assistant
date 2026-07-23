import logging

from fastapi import APIRouter, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

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
