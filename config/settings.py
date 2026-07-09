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
    recommendation_batch_size: int
    fp_growth_min_support: float
    fp_growth_min_confidence: float
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
            recommendation_batch_size=self._get_positive_int(
                "RECOMMENDATION_BATCH_SIZE",
                5000,
            ),
            fp_growth_min_support=self._get_probability(
                "FP_GROWTH_MIN_SUPPORT",
                0.001,
            ),
            fp_growth_min_confidence=self._get_probability(
                "FP_GROWTH_MIN_CONFIDENCE",
                0.05,
            ),
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

    def _get_positive_int(self, variable: str, default: int) -> int:
        raw_value = os.getenv(variable, str(default))
        try:
            value = int(raw_value)
        except ValueError as exc:
            raise SettingsError(f"{variable} must be a valid integer.") from exc
        if value <= 0:
            raise SettingsError(f"{variable} must be greater than zero.")
        return value

    def _get_probability(self, variable: str, default: float) -> float:
        raw_value = os.getenv(variable, str(default))
        try:
            value = float(raw_value)
        except ValueError as exc:
            raise SettingsError(f"{variable} must be a valid number.") from exc
        if value <= 0 or value > 1:
            raise SettingsError(
                f"{variable} must be greater than 0 and less than or equal to 1."
            )
        return value


def get_settings(env_file: str | Path = ".env") -> Settings:
    """Return the validated application settings."""
    return SettingsLoader(env_file=env_file).load()
