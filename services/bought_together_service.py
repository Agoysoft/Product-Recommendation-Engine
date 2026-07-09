"""Service for building bought-together relationships from sale history."""

from itertools import combinations
import logging

from recommendation_engine.models.bought_together import BoughtTogetherRelationship
from recommendation_engine.repositories.bought_together_repository import (
    BoughtTogetherRepository,
)
from recommendation_engine.services.transaction_extraction_service import (
    TransactionExtractionService,
)


class BoughtTogetherService:
    """Builds and queries product pairs that appeared in the same sale basket."""

    def __init__(
        self,
        transaction_extraction_service: TransactionExtractionService,
        bought_together_repository: BoughtTogetherRepository,
        logger: logging.Logger | None = None,
    ) -> None:
        self._transaction_extraction_service = transaction_extraction_service
        self._bought_together_repository = bought_together_repository
        self._logger = logger or logging.getLogger(self.__class__.__name__)

    def rebuild_relationships(
        self,
        branch_id: int,
        months: int = 3,
        customer_id: int | None = None,
        limit: int | None = None,
    ) -> int:
        """Rebuild stored product pairs from historical sale baskets."""
        transactions = self._transaction_extraction_service.extract_product_id_transactions(
            branch_id=branch_id,
            months=months,
            customer_id=customer_id,
            limit=limit,
        )
        relationships = self.build_relationships_from_transactions(transactions)
        affected_rows = self._bought_together_repository.replace_all(relationships)
        self._logger.info(
            "Rebuilt %s bought-together relationships for branch_id=%s months=%s.",
            len(relationships),
            branch_id,
            months,
        )
        return affected_rows

    def get_bought_together_product_ids(self, product_id: int) -> list[int]:
        """Return all product IDs bought together with product_id."""
        return self._bought_together_repository.find_pair_product_ids(product_id)

    @staticmethod
    def build_relationships_from_transactions(
        transactions: list[list[int]],
    ) -> list[BoughtTogetherRelationship]:
        """Build unique normalized product pairs from product-id baskets."""
        pairs: set[tuple[int, int]] = set()

        for transaction in transactions:
            product_ids = sorted({product_id for product_id in transaction if product_id > 0})
            for product, pair in combinations(product_ids, 2):
                pairs.add((product, pair))

        return [
            BoughtTogetherRelationship(product=product, pair=pair)
            for product, pair in sorted(pairs)
        ]
