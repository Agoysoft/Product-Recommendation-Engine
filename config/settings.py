"""Application configuration loading and validation."""

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Final

from dotenv import load_dotenv


class SettingsError(ValueError):
    """Raised when required application settings are missing or invalid."""


@dataclass(frozen=True, slots=True)
class DatabaseSettings:
    """Database connection settings."""

    host: str
    port: int
    name: str
    user: str
    password: str


@dataclass(frozen=True, slots=True)
class Settings:
    """Validated application settings."""

    database: DatabaseSettings
    log_level: str
    app_name: str = "Product Recommendation Engine"
    log_directory: Path = Path("logs")
    log_file_name: str = "recommendation_engine.log"
    mysql_pool_name: str = "recommendation_engine_pool"
    mysql_pool_size: int = 5


class SettingsLoader:
    """Loads and validates settings from environment variables."""

    REQUIRED_VARIABLES: Final[tuple[str, ...]] = (
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
    )

    VALID_LOG_LEVELS: Final[set[str]] = {
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    }

    def __init__(self, env_file: str | Path = ".env") -> None:
        self._env_file = Path(env_file)

    def load(self) -> Settings:
        """Load environment variables and return a validated settings object."""
        load_dotenv(self._env_file)
        self._validate_required_variables()

        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        if log_level not in self.VALID_LOG_LEVELS:
            raise SettingsError(
                "LOG_LEVEL must be one of: "
                f"{', '.join(sorted(self.VALID_LOG_LEVELS))}"
            )

        return Settings(
            database=DatabaseSettings(
                host=self._get_required("DB_HOST"),
                port=self._get_port(),
                name=self._get_required("DB_NAME"),
                user=self._get_required("DB_USER"),
                password=self._get_required("DB_PASSWORD"),
            ),
            log_level=log_level,
        )

    def _validate_required_variables(self) -> None:
        missing = [
            variable
            for variable in self.REQUIRED_VARIABLES
            if not os.getenv(variable)
        ]
        if missing:
            raise SettingsError(
                "Missing required environment variables: "
                f"{', '.join(missing)}"
            )

    def _get_required(self, variable: str) -> str:
        value = os.getenv(variable)
        if value is None or not value.strip():
            raise SettingsError(f"{variable} cannot be empty.")
        return value.strip()

    def _get_port(self) -> int:
        raw_port = self._get_required("DB_PORT")
        try:
            port = int(raw_port)
        except ValueError as exc:
            raise SettingsError("DB_PORT must be a valid integer.") from exc

        if port <= 0 or port > 65535:
            raise SettingsError("DB_PORT must be between 1 and 65535.")
        return port


def get_settings(env_file: str | Path = ".env") -> Settings:
    """Return the validated application settings."""
    return SettingsLoader(env_file=env_file).load()

