"""Repositories for extracting ERP sale transaction rows."""

import logging
from typing import Any

from recommendation_engine.database.connection import DatabaseManager


class TransactionRepository:
    """Reads sales, products_logs, and products rows for basket extraction."""

    def __init__(
        self,
        database_manager: DatabaseManager,
        logger: logging.Logger | None = None,
    ) -> None:
        self._database_manager = database_manager
        self._logger = logger or logging.getLogger(self.__class__.__name__)

    def fetch_sale_item_rows(
        self,
        branch_id: int,
        months: int = 3,
        customer_id: int | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch sale item rows needed to reconstruct transaction baskets."""
        if branch_id <= 0:
            raise ValueError("branch_id must be greater than zero.")
        if months <= 0:
            raise ValueError("months must be greater than zero.")
        if limit is not None and limit <= 0:
            raise ValueError("limit must be greater than zero.")

        filters = [
            "s.branch = %(branch_id)s",
            "s.date >= DATE_SUB(CURDATE(), INTERVAL %(months)s MONTH)",
            "pl.type = 0",
            "pl.product IS NOT NULL",
        ]
        params: dict[str, Any] = {
            "branch_id": branch_id,
            "months": months,
        }

        if customer_id is not None:
            filters.append("s.customer = %(customer_id)s")
            params["customer_id"] = customer_id

        limit_clause = ""
        if limit is not None:
            limit_clause = "LIMIT %(limit)s"
            params["limit"] = limit

        query = f"""
            SELECT
                s.id AS sale_id,
                s.invoice,
                s.customer AS customer_id,
                s.branch AS branch_id,
                s.date AS sale_date,
                pl.product AS product_id,
                pl.qty,
                pl.selling_price,
                p.title AS product_name,
                p.ui_code
            FROM sales s
            JOIN products_logs pl
                ON pl.referrer = s.id
            JOIN products p
                ON p.id = pl.product
            WHERE {" AND ".join(filters)}
            ORDER BY s.id ASC, pl.id ASC
            {limit_clause}
        """

        self._logger.info(
            "Fetching transaction rows for branch_id=%s months=%s customer_id=%s.",
            branch_id,
            months,
            customer_id,
        )
        return self._database_manager.fetch_all(query, params)
