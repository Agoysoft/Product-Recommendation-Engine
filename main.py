"""Entry point for the Product Recommendation Engine."""

from pathlib import Path
import importlib.util
import sys


if __package__ is None or __package__ == "":
    package_dir = Path(__file__).resolve().parent
    package_name = "recommendation_engine"
    if package_name not in sys.modules:
        package_spec = importlib.util.spec_from_file_location(
            package_name,
            package_dir / "__init__.py",
            submodule_search_locations=[str(package_dir)],
        )
        if package_spec is not None and package_spec.loader is not None:
            package = importlib.util.module_from_spec(package_spec)
            sys.modules[package_name] = package
            package_spec.loader.exec_module(package)

from recommendation_engine.config.database import DatabaseConfigFactory
from recommendation_engine.config.settings import SettingsError, get_settings
from recommendation_engine.database.connection import DatabaseError, DatabaseManager
from recommendation_engine.repositories.recommendation_repository import RecommendationRepository
from recommendation_engine.repositories.transaction_repository import TransactionRepository
from recommendation_engine.services.fp_growth_service import FPGrowthService
from recommendation_engine.services.transaction_extraction_service import (
    TransactionExtractionService,
)
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

        transaction_repository = TransactionRepository(
            database_manager=database_manager,
            logger=logger,
        )
        transaction_service = TransactionExtractionService(
            transaction_repository=transaction_repository,
            logger=logger,
        )
        recommendation_repository = RecommendationRepository(
            database_manager=database_manager,
            logger=logger,
        )
        fp_growth_service = FPGrowthService(
            transaction_extraction_service=transaction_service,
            recommendation_repository=recommendation_repository,
            min_support=settings.fp_growth_min_support,
            min_confidence=settings.fp_growth_min_confidence,
            batch_size=settings.recommendation_batch_size,
            logger=logger,
        )

        summary = fp_growth_service.run(
            months=settings.recommendation_months,
            branch_id=settings.recommendation_branch_id,
        )
        print(f"Recommendation generation completed: {summary}")
        logger.info("Recommendation generation completed: %s", summary)
    except (SettingsError, DatabaseError) as exc:
        logger.exception("Recommendation Engine initialization failed: %s", exc)
        raise
    finally:
        if database_manager is not None:
            database_manager.disconnect()


if __name__ == "__main__":
    main()
