"""Repository for bought-together product relationships."""

import logging

from recommendation_engine.database.base_repository import BaseRepository
from recommendation_engine.database.connection import DatabaseManager
from recommendation_engine.models.bought_together import BoughtTogetherRelationship


class BoughtTogetherRepository(BaseRepository):
    """Reads and writes normalized bought-together product pairs."""

    def __init__(
        self,
        database_manager: DatabaseManager,
        logger: logging.Logger | None = None,
    ) -> None:
        super().__init__(
            database_manager=database_manager,
            table_name="bought_together_relationships",
            logger=logger,
        )

    def replace_all(self, relationships: list[BoughtTogetherRelationship]) -> int:
        """Replace all stored bought-together relationships."""
        self._database_manager.execute(f"TRUNCATE TABLE `{self._table_name}`")

        if not relationships:
            self._database_manager.commit()
            return 0

        affected_rows = self.execute_many(
            f"""
            INSERT INTO `{self._table_name}` (product, pair)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE
                product = VALUES(product),
                pair = VALUES(pair)
            """,
            [(relationship.product, relationship.pair) for relationship in relationships],
        )
        self._database_manager.commit()
        return affected_rows

    def find_pair_product_ids(self, product_id: int) -> list[int]:
        """Return all product IDs bought together with the given product."""
        if product_id <= 0:
            raise ValueError("product_id must be greater than zero.")

        rows = self.execute_query(
            f"""
            SELECT
                CASE
                    WHEN product = %(product_id)s THEN pair
                    ELSE product
                END AS pair_product_id
            FROM `{self._table_name}`
            WHERE product = %(product_id)s OR pair = %(product_id)s
            ORDER BY pair_product_id ASC
            """,
            {"product_id": product_id},
        )
        return [int(row["pair_product_id"]) for row in rows]
