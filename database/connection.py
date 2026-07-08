"""MySQL database connection manager."""

from collections.abc import Sequence
import logging
from typing import Any

import mysql.connector
from mysql.connector import Error, pooling
from mysql.connector.connection import MySQLConnection
from mysql.connector.cursor import MySQLCursorDict


class DatabaseError(RuntimeError):
    """Raised when database operations fail."""


class DatabaseManager:
    """Singleton-style MySQL connection manager using connection pooling."""

    _instance: "DatabaseManager | None" = None

    def __new__(
        cls,
        pool_config: dict[str, Any] | None = None,
        logger: logging.Logger | None = None,
    ) -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        pool_config: dict[str, Any] | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        if self._initialized:
            return

        if pool_config is None:
            raise DatabaseError("Database pool configuration is required.")

        self._pool_config = pool_config
        self._logger = logger or logging.getLogger(__name__)
        self._pool: pooling.MySQLConnectionPool | None = None
        self._connection: MySQLConnection | None = None
        self._initialized = True

    def connect(self) -> None:
        """Create a connection pool and acquire an initial connection."""
        try:
            if self._pool is None:
                self._pool = pooling.MySQLConnectionPool(**self._pool_config)
                self._logger.info("MySQL connection pool initialized.")

            self._connection = self._pool.get_connection()
            self._logger.info("MySQL database connection established.")
        except Error as exc:
            self._logger.exception("Failed to connect to MySQL database.")
            raise DatabaseError("Failed to connect to MySQL database.") from exc

    def disconnect(self) -> None:
        """Close the active database connection safely."""
        if self._connection is None:
            return

        try:
            if self._connection.is_connected():
                self._connection.close()
                self._logger.info("MySQL database connection closed.")
        except Error as exc:
            self._logger.warning("Error while closing database connection: %s", exc)
        finally:
            self._connection = None

    def execute(
        self,
        query: str,
        params: Sequence[Any] | dict[str, Any] | None = None,
    ) -> int:
        """Execute a SQL statement and return the affected row count."""
        connection = self._get_connection()
        cursor: MySQLCursorDict | None = None
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, params)
            return cursor.rowcount
        except Error as exc:
            self._logger.exception("Database execute operation failed.")
            raise DatabaseError("Database execute operation failed.") from exc
        finally:
            if cursor is not None:
                cursor.close()

    def fetch_one(
        self,
        query: str,
        params: Sequence[Any] | dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Execute a query and return one row."""
        connection = self._get_connection()
        cursor: MySQLCursorDict | None = None
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, params)
            result = cursor.fetchone()
            return dict(result) if result else None
        except Error as exc:
            self._logger.exception("Database fetch_one operation failed.")
            raise DatabaseError("Database fetch_one operation failed.") from exc
        finally:
            if cursor is not None:
                cursor.close()

    def fetch_all(
        self,
        query: str,
        params: Sequence[Any] | dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a query and return all rows."""
        connection = self._get_connection()
        cursor: MySQLCursorDict | None = None
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        except Error as exc:
            self._logger.exception("Database fetch_all operation failed.")
            raise DatabaseError("Database fetch_all operation failed.") from exc
        finally:
            if cursor is not None:
                cursor.close()

    def execute_many(
        self,
        query: str,
        params: Sequence[Sequence[Any] | dict[str, Any]],
    ) -> int:
        """Execute a SQL statement for multiple parameter sets."""
        connection = self._get_connection()
        cursor: MySQLCursorDict | None = None
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.executemany(query, params)
            return cursor.rowcount
        except Error as exc:
            self._logger.exception("Database execute_many operation failed.")
            raise DatabaseError("Database execute_many operation failed.") from exc
        finally:
            if cursor is not None:
                cursor.close()

    def commit(self) -> None:
        """Commit the active transaction."""
        try:
            self._get_connection().commit()
        except Error as exc:
            self._logger.exception("Database commit failed.")
            raise DatabaseError("Database commit failed.") from exc

    def rollback(self) -> None:
        """Rollback the active transaction."""
        try:
            self._get_connection().rollback()
        except Error as exc:
            self._logger.exception("Database rollback failed.")
            raise DatabaseError("Database rollback failed.") from exc

    def health_check(self) -> bool:
        """Return True when the database connection can execute a simple query."""
        try:
            result = self.fetch_one("SELECT 1 AS healthy")
            return result is not None and result.get("healthy") == 1
        except DatabaseError:
            self._logger.exception("Database health check failed.")
            return False

    def _get_connection(self) -> MySQLConnection:
        if self._connection is None or not self._connection.is_connected():
            self._logger.info("MySQL connection unavailable. Reconnecting.")
            self.connect()

        if self._connection is None:
            raise DatabaseError("Database connection is not available.")

        return self._connection

