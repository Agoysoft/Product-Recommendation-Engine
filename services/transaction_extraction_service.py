"""Transaction basket extraction for FP-Growth preparation."""

from collections.abc import Iterator
import logging
from typing import Any

import pandas as pd

from recommendation_engine.models.transaction import (
    TransactionBasket,
    TransactionItem,
)
from recommendation_engine.repositories.transaction_repository import (
    TransactionRepository,
)


class TransactionExtractionService:
    """Reconstructs ERP products_logs sales into transaction baskets."""

    def __init__(
        self,
        transaction_repository: TransactionRepository,
        logger: logging.Logger | None = None,
    ) -> None:
        self._transaction_repository = transaction_repository
        self._logger = logger or logging.getLogger(self.__class__.__name__)

    def extract_baskets(
        self,
        branch_id: int | None = None,
        months: int = 3,
        customer_id: int | None = None,
        limit: int | None = None,
    ) -> list[TransactionBasket]:
        """Return sale baskets reconstructed from products_logs rows."""
        rows = self._transaction_repository.fetch_sale_item_rows(
            branch_id=branch_id,
            months=months,
            customer_id=customer_id,
            limit=limit,
        )
        baskets = self._build_baskets(rows)
        self._logger.info("Extracted %s transaction baskets.", len(baskets))
        return baskets

    def extract_product_id_transactions(
        self,
        branch_id: int | None = None,
        months: int = 3,
        customer_id: int | None = None,
        limit: int | None = None,
    ) -> list[list[int]]:
        """Return baskets as product ID lists for later FP-Growth processing."""
        baskets = self.extract_baskets(
            branch_id=branch_id,
            months=months,
            customer_id=customer_id,
            limit=limit,
        )
        return [basket.product_ids for basket in baskets if basket.product_ids]

    def extract_one_hot_dataframe(
        self,
        branch_id: int | None = None,
        months: int = 3,
        customer_id: int | None = None,
        limit: int | None = None,
    ) -> pd.DataFrame:
        """Return a one-hot encoded product matrix for later FP-Growth use."""
        transactions = self.extract_product_id_transactions(
            branch_id=branch_id,
            months=months,
            customer_id=customer_id,
            limit=limit,
        )

        if not transactions:
            return pd.DataFrame(dtype=bool)

        product_ids = sorted(
            {product_id for basket in transactions for product_id in basket}
        )
        rows = [
            {product_id: product_id in set(basket) for product_id in product_ids}
            for basket in transactions
        ]
        return pd.DataFrame(rows, columns=product_ids, dtype=bool)

    def iter_product_id_transaction_batches(
        self,
        months: int = 3,
        batch_size: int = 5000,
        branch_id: int | None = None,
    ) -> Iterator[list[list[int]]]:
        """Yield product ID transaction baskets in bounded batches."""
        for rows in self._transaction_repository.iter_sale_item_row_batches(
            months=months,
            batch_size=batch_size,
            branch_id=branch_id,
        ):
            baskets = self._build_baskets(rows)
            yield [basket.product_ids for basket in baskets if len(basket.product_ids) > 1]

    def _build_baskets(
        self,
        rows: list[dict[str, Any]],
    ) -> list[TransactionBasket]:
        grouped: dict[int, dict[str, Any]] = {}

        for row in rows:
            sale_id = int(row["sale_id"])
            basket = grouped.setdefault(
                sale_id,
                {
                    "sale_id": sale_id,
                    "invoice": row.get("invoice"),
                    "customer_id": row.get("customer_id"),
                    "branch_id": int(row.get("branch_id") or 0),
                    "sale_date": row.get("sale_date"),
                    "items": [],
                },
            )
            basket["items"].append(
                TransactionItem(
                    product_id=int(row["product_id"]),
                    product_name=row.get("product_name"),
                    ui_code=row.get("ui_code"),
                    quantity=row.get("qty"),
                    selling_price=row.get("selling_price"),
                )
            )

        return [
            TransactionBasket(
                sale_id=basket["sale_id"],
                invoice=basket["invoice"],
                customer_id=basket["customer_id"],
                branch_id=basket["branch_id"],
                sale_date=basket["sale_date"],
                items=tuple(basket["items"]),
            )
            for basket in grouped.values()
        ]
