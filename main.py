"""Entry point for the Product Recommendation Engine."""

from pathlib import Path
import sys


if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from recommendation_engine.config.database import DatabaseConfigFactory
from recommendation_engine.config.settings import SettingsError, get_settings
from recommendation_engine.database.connection import DatabaseError, DatabaseManager
from recommendation_engine.utils.logger import configure_logger


def main() -> None:
    """Initialize the recommendation engine infrastructure."""
    settings = get_settings()
    logger = configure_logger(
        name="recommendation_engine",
        log_level=settings.log_level,
        log_directory=settings.log_directory,
        log_file_name=settings.log_file_name,
    )

    database_manager: DatabaseManager | None = None

    try:
        logger.info("Starting %s.", settings.app_name)
        database_config = DatabaseConfigFactory(settings).create_pool_config()
        database_manager = DatabaseManager(
            pool_config=database_config,
            logger=logger,
        )
        database_manager.connect()

        if not database_manager.health_check():
            raise DatabaseError("Database health check failed.")

        print("Recommendation Engine initialized successfully.")
        logger.info("Recommendation Engine initialized successfully.")
    except (SettingsError, DatabaseError) as exc:
        logger.exception("Recommendation Engine initialization failed: %s", exc)
        raise
    finally:
        if database_manager is not None:
            database_manager.disconnect()


if __name__ == "__main__":
    main()
