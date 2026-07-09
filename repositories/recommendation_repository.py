"""Repository for product-pair recommendation results."""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
import logging

from recommendation_engine.database.base_repository import BaseRepository
from recommendation_engine.database.connection import DatabaseManager


@dataclass(frozen=True, slots=True)
class ProductPairRule:
    """One-to-one product association rule."""

    product: int
    pair: int
    support: float
    confidence: float
    lift: float
    cooccurrence_count: int
    antecedent_count: int
    consequent_count: int
    transaction_count: int


class RecommendationRepository(BaseRepository):
    """Persists product-pair association rules."""

    def __init__(
        self,
        database_manager: DatabaseManager,
        logger: logging.Logger | None = None,
    ) -> None:
        super().__init__(
            database_manager=database_manager,
            table_name="product_pair",
            logger=logger,
        )

    def upsert_product_pairs(self, rules: Sequence[ProductPairRule]) -> int:
        """Bulk upsert product-pair statistics without deleting existing rows."""
        if not rules:
            return 0

        query = f"""
            INSERT INTO `{self._table_name}` (
                product,
                pair_product,
                pair_count,
                confidence,
                lift,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON DUPLICATE KEY UPDATE
                pair_count = pair_count + VALUES(pair_count),
                confidence = VALUES(confidence),
                lift = VALUES(lift),
                updated_at = CURRENT_TIMESTAMP
        """
        params = [
            (
                rule.product,
                rule.pair,
                rule.cooccurrence_count,
                Decimal(str(rule.confidence)),
                Decimal(str(rule.lift)),
            )
            for rule in rules
        ]
        affected_rows = self.execute_many(query, params)
        self._database_manager.commit()
        return affected_rows

    def find_pairs_for_product(self, product_id: int, limit: int | None = None) -> list[dict]:
        """Return recommended pair products for a product ordered by strength."""
        if product_id <= 0:
            raise ValueError("product_id must be greater than zero.")
        params: dict[str, int] = {"product_id": product_id}
        limit_clause = ""
        if limit is not None:
            if limit <= 0:
                raise ValueError("limit must be greater than zero.")
            limit_clause = "LIMIT %(limit)s"
            params["limit"] = limit

        query = f"""
            SELECT
                product,
                pair_product AS pair,
                pair_count,
                confidence,
                lift
            FROM `{self._table_name}`
            WHERE product = %(product_id)s
            ORDER BY lift DESC, confidence DESC, pair_count DESC
            {limit_clause}
        """
        return self.execute_query(query, params)

