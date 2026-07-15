"""Recommendation scheduler for incremental daily updates and weekly rebuilds."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
from typing import Any

from recommendation_engine.config.settings import Settings
from recommendation_engine.database.connection import DatabaseManager
from recommendation_engine.repositories.recommendation_repository import (
    RecommendationRepository,
)
from recommendation_engine.repositories.transaction_repository import (
    TransactionRepository,
)
from recommendation_engine.services.pair_count_service import (
    PairCountRecommendationService,
)
from recommendation_engine.services.transaction_extraction_service import (
    TransactionExtractionService,
)


@dataclass(frozen=True, slots=True)
class SchedulerState:
    """Persisted scheduler state."""

    last_run_at: datetime | None = None
    last_full_rebuild_at: datetime | None = None


class RecommendationScheduler:
    """Runs daily incremental updates and weekly full rebuilds."""

    def __init__(
        self,
        database_manager: DatabaseManager,
        settings: Settings,
        logger: logging.Logger | None = None,
        state_file: str | Path = Path("state/recommendation_scheduler.json"),
        full_rebuild_interval_days: int = 7,
    ) -> None:
        if full_rebuild_interval_days <= 0:
            raise ValueError("full_rebuild_interval_days must be greater than zero.")

        self._database_manager = database_manager
        self._settings = settings
        self._logger = logger or logging.getLogger(self.__class__.__name__)
        self._state_file = Path(state_file)
        self._full_rebuild_interval = timedelta(days=full_rebuild_interval_days)

    def run(self) -> dict[str, Any]:
        """Run either an incremental refresh or a full rebuild."""
        transaction_repository = TransactionRepository(
            database_manager=self._database_manager,
            logger=self._logger,
        )
        transaction_service = TransactionExtractionService(
            transaction_repository=transaction_repository,
            logger=self._logger,
        )
        recommendation_repository = RecommendationRepository(
            database_manager=self._database_manager,
            logger=self._logger,
        )
        recommendation_service = PairCountRecommendationService(
            transaction_extraction_service=transaction_service,
            recommendation_repository=recommendation_repository,
            min_support=self._settings.pair_count_min_support,
            min_confidence=self._settings.pair_count_min_confidence,
            batch_size=self._settings.recommendation_batch_size,
            logger=self._logger,
        )

        now = datetime.now()
        state = self._load_state()
        should_full_rebuild = self._should_full_rebuild(state, now)

        if should_full_rebuild:
            self._logger.info("Running weekly full rebuild of product_pair.")
            recommendation_repository.clear_product_pairs()
            summary = recommendation_service.run(
                months=self._settings.recommendation_months,
                branch_id=self._settings.recommendation_branch_id,
            )
            state.last_full_rebuild_at = now
            mode = "full_rebuild"
        else:
            since = state.last_run_at
            self._logger.info("Running incremental update since=%s.", since)
            summary = recommendation_service.run(
                since=since,
                branch_id=self._settings.recommendation_branch_id,
            )
            mode = "incremental"

        state.last_run_at = now
        self._save_state(state)
        summary["mode"] = mode
        summary["last_run_at"] = now.isoformat(timespec="seconds")
        if state.last_full_rebuild_at is not None:
            summary["last_full_rebuild_at"] = state.last_full_rebuild_at.isoformat(
                timespec="seconds"
            )
        return summary

    def _should_full_rebuild(self, state: SchedulerState, now: datetime) -> bool:
        if state.last_full_rebuild_at is None:
            return True
        return now - state.last_full_rebuild_at >= self._full_rebuild_interval

    def _load_state(self) -> SchedulerState:
        if not self._state_file.exists():
            return SchedulerState()

        try:
            with self._state_file.open("r", encoding="utf-8") as handle:
                raw_state = json.load(handle)
        except (OSError, json.JSONDecodeError):
            self._logger.warning("Failed to load scheduler state; starting fresh.")
            return SchedulerState()

        return SchedulerState(
            last_run_at=self._parse_datetime(raw_state.get("last_run_at")),
            last_full_rebuild_at=self._parse_datetime(raw_state.get("last_full_rebuild_at")),
        )

    def _save_state(self, state: SchedulerState) -> None:
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "last_run_at": state.last_run_at.isoformat(timespec="seconds")
            if state.last_run_at is not None
            else None,
            "last_full_rebuild_at": state.last_full_rebuild_at.isoformat(timespec="seconds")
            if state.last_full_rebuild_at is not None
            else None,
        }
        with self._state_file.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)

    @staticmethod
    def _parse_datetime(raw_value: Any) -> datetime | None:
        if not raw_value:
            return None
        if not isinstance(raw_value, str):
            return None
        try:
            return datetime.fromisoformat(raw_value)
        except ValueError:
            return None
