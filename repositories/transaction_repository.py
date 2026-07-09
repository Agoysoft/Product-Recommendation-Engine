"""Repositories for extracting ERP sale transaction rows."""

from collections.abc import Iterator
import logging
from typing import Any

from recommendation_engine.database.connection import DatabaseManager


class TransactionRepository:
    """Reads sales transactions from the products_logs inventory ledger."""

    def __init__(
        self,
        database_manager: DatabaseManager,
        logger: logging.Logger | None = None,
    ) -> None:
        self._database_manager = database_manager
        self._logger = logger or logging.getLogger(self.__class__.__name__)

    def fetch_sale_item_rows(
        self,
        branch_id: int | None = None,
        months: int = 3,
        customer_id: int | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch sale ledger rows needed to reconstruct transaction baskets."""
        if branch_id is not None and branch_id <= 0:
            raise ValueError("branch_id must be greater than zero.")
        if months <= 0:
            raise ValueError("months must be greater than zero.")
        if limit is not None and limit <= 0:
            raise ValueError("limit must be greater than zero.")

        filters = [
            "pl.type = 0",
            "pl.added >= DATE_SUB(CURDATE(), INTERVAL %(months)s MONTH)",
            "pl.referrer IS NOT NULL",
            "pl.product IS NOT NULL",
            "pl.product > 0",
        ]
        params: dict[str, Any] = {"months": months}

        if branch_id is not None:
            filters.append("pl.branch = %(branch_id)s")
            params["branch_id"] = branch_id

        if customer_id is not None:
            self._logger.warning(
                "customer_id filter ignored because products_logs is the only transaction source."
            )

        limit_clause = ""
        if limit is not None:
            limit_clause = "LIMIT %(limit)s"
            params["limit"] = limit

        query = f"""
            SELECT
                pl.referrer AS sale_id,
                NULL AS invoice,
                NULL AS customer_id,
                pl.branch AS branch_id,
                DATE(pl.added) AS sale_date,
                pl.product AS product_id,
                pl.qty,
                pl.selling_price,
                NULL AS product_name,
                pl.uic AS ui_code
            FROM products_logs pl
            WHERE {" AND ".join(filters)}
            ORDER BY pl.referrer ASC, pl.id ASC
            {limit_clause}
        """

        self._logger.info(
            "Fetching products_logs sale rows for branch_id=%s months=%s.",
            branch_id,
            months,
        )
        return self._database_manager.fetch_all(query, params)

    def iter_sale_item_row_batches(
        self,
        months: int = 3,
        batch_size: int = 5000,
        branch_id: int | None = None,
    ) -> Iterator[list[dict[str, Any]]]:
        """Yield products_logs sale rows in referrer-based batches."""
        if months <= 0:
            raise ValueError("months must be greater than zero.")
        if batch_size <= 0:
            raise ValueError("batch_size must be greater than zero.")
        if branch_id is not None and branch_id <= 0:
            raise ValueError("branch_id must be greater than zero.")

        last_referrer = 0
        while True:
            referrers = self._fetch_referrer_batch(
                months=months,
                batch_size=batch_size,
                last_referrer=last_referrer,
                branch_id=branch_id,
            )
            if not referrers:
                break

            last_referrer = int(referrers[-1]["referrer"])
            yield self._fetch_rows_for_referrers(
                referrers=[int(row["referrer"]) for row in referrers],
                branch_id=branch_id,
            )

    def _fetch_referrer_batch(
        self,
        months: int,
        batch_size: int,
        last_referrer: int,
        branch_id: int | None,
    ) -> list[dict[str, Any]]:
        filters = [
            "type = 0",
            "added >= DATE_SUB(CURDATE(), INTERVAL %(months)s MONTH)",
            "referrer IS NOT NULL",
            "referrer > %(last_referrer)s",
            "product IS NOT NULL",
            "product > 0",
        ]
        params: dict[str, Any] = {
            "months": months,
            "last_referrer": last_referrer,
            "batch_size": batch_size,
        }
        if branch_id is not None:
            filters.append("branch = %(branch_id)s")
            params["branch_id"] = branch_id

        query = f"""
            SELECT referrer
            FROM products_logs
            WHERE {" AND ".join(filters)}
            GROUP BY referrer
            ORDER BY referrer ASC
            LIMIT %(batch_size)s
        """
        return self._database_manager.fetch_all(query, params)

    def _fetch_rows_for_referrers(
        self,
        referrers: list[int],
        branch_id: int | None,
    ) -> list[dict[str, Any]]:
        if not referrers:
            return []

        placeholders = ", ".join(["%s"] * len(referrers))
        filters = [
            "pl.type = 0",
            f"pl.referrer IN ({placeholders})",
            "pl.product IS NOT NULL",
            "pl.product > 0",
        ]
        params: list[Any] = list(referrers)
        if branch_id is not None:
            filters.append("pl.branch = %s")
            params.append(branch_id)

        query = f"""
            SELECT
                pl.referrer AS sale_id,
                NULL AS invoice,
                NULL AS customer_id,
                pl.branch AS branch_id,
                DATE(pl.added) AS sale_date,
                pl.product AS product_id,
                pl.qty,
                pl.selling_price,
                NULL AS product_name,
                pl.uic AS ui_code
            FROM products_logs pl
            WHERE {" AND ".join(filters)}
            ORDER BY pl.referrer ASC, pl.id ASC
        """
        return self._database_manager.fetch_all(query, tuple(params))
