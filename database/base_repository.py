"""Generic repository primitives for database access."""

from collections.abc import Sequence
import logging
import re
from typing import Any

from recommendation_engine.database.connection import DatabaseManager


class BaseRepository:
    """Base repository with generic database operations."""

    _VALID_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

    def __init__(
        self,
        database_manager: DatabaseManager,
        table_name: str,
        primary_key: str = "id",
        logger: logging.Logger | None = None,
    ) -> None:
        self._database_manager = database_manager
        self._table_name = self._validate_identifier(table_name, "table_name")
        self._primary_key = self._validate_identifier(primary_key, "primary_key")
        self._logger = logger or logging.getLogger(self.__class__.__name__)

    def find_by_id(self, record_id: int) -> dict[str, Any] | None:
        """Find one record by primary key."""
        query = (
            f"SELECT * FROM `{self._table_name}` "
            f"WHERE `{self._primary_key}` = %s LIMIT 1"
        )
        return self._database_manager.fetch_one(query, (record_id,))

    def find_all(self, limit: int | None = None) -> list[dict[str, Any]]:
        """Return all records, optionally limited."""
        query = f"SELECT * FROM `{self._table_name}`"
        params: tuple[int, ...] = ()

        if limit is not None:
            if limit <= 0:
                raise ValueError("limit must be greater than zero.")
            query = f"{query} LIMIT %s"
            params = (limit,)

        return self._database_manager.fetch_all(query, params)

    def execute_query(
        self,
        query: str,
        params: Sequence[Any] | dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a read query and return all rows."""
        self._logger.debug("Executing repository query.")
        return self._database_manager.fetch_all(query, params)

    def execute_many(
        self,
        query: str,
        params: Sequence[Sequence[Any] | dict[str, Any]],
    ) -> int:
        """Execute a write query for multiple parameter sets."""
        self._logger.debug("Executing repository batch query.")
        return self._database_manager.execute_many(query, params)

    @classmethod
    def _validate_identifier(cls, identifier: str, field_name: str) -> str:
        if not cls._VALID_IDENTIFIER.match(identifier):
            raise ValueError(f"Invalid SQL identifier for {field_name}.")
        return identifier

