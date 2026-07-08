"""Application logging setup."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


class LoggerFactory:
    """Creates configured application loggers."""

    def __init__(
        self,
        log_level: str,
        log_directory: Path,
        log_file_name: str,
    ) -> None:
        self._log_level = log_level.upper()
        self._log_directory = log_directory
        self._log_file_name = log_file_name

    def create_logger(self, name: str) -> logging.Logger:
        """Return a logger configured for console and rotating file output."""
        logger = logging.getLogger(name)
        logger.setLevel(self._resolve_log_level())
        logger.propagate = False

        if logger.handlers:
            return logger

        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(self._resolve_log_level())

        self._log_directory.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            self._log_directory / self._log_file_name,
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(self._resolve_log_level())

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        return logger

    def _resolve_log_level(self) -> int:
        return getattr(logging, self._log_level, logging.INFO)


def configure_logger(
    name: str,
    log_level: str,
    log_directory: Path,
    log_file_name: str,
) -> logging.Logger:
    """Configure and return an application logger."""
    return LoggerFactory(
        log_level=log_level,
        log_directory=log_directory,
        log_file_name=log_file_name,
    ).create_logger(name)

