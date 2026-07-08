"""Database configuration helpers."""

from typing import Any

from recommendation_engine.config.settings import Settings


class DatabaseConfigFactory:
    """Builds mysql-connector compatible database configuration."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def create_pool_config(self) -> dict[str, Any]:
        """Return MySQL connection pool configuration."""
        database = self._settings.database
        return {
            "pool_name": self._settings.mysql_pool_name,
            "pool_size": self._settings.mysql_pool_size,
            "host": database.host,
            "port": database.port,
            "database": database.name,
            "user": database.user,
            "password": database.password,
            "autocommit": False,
            "charset": "utf8mb4",
            "use_unicode": True,
        }

