import logging
import sys

from app.database.session import SessionLocal
from app.sessions.services import SessionService

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def cleanup_expired_sessions() -> None:
    db = SessionLocal()
    service = SessionService(db)
    try:
        logger.info("Starting cleanup of expired form sessions...")
        count = service.cleanup_expired_sessions()
        logger.info(f"Cleanup completed successfully. Expired {count} session(s).")
    except Exception:
        logger.exception("An unexpected error occurred during session cleanup.")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    cleanup_expired_sessions()
