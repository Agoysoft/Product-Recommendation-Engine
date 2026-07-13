"""FP-Growth recommendation service."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
import logging
import time
import tracemalloc

import pandas as pd
from mlxtend.frequent_patterns import association_rules, fpgrowth

from recommendation_engine.repositories.recommendation_repository import (
    ProductPairRule,
    RecommendationRepository,
)
from recommendation_engine.services.transaction_extraction_service import (
    TransactionExtractionService,
)


class FPGrowthService:
    """Builds one-to-one product recommendations from transaction baskets."""

    def __init__(
        self,
        transaction_extraction_service: TransactionExtractionService,
        recommendation_repository: RecommendationRepository,
        min_support: float = 0.001,
        min_confidence: float = 0.05,
        batch_size: int = 5000,
        logger: logging.Logger | None = None,
    ) -> None:
        if min_support <= 0 or min_support > 1:
            raise ValueError("min_support must be between 0 and 1.")
        if min_confidence < 0 or min_confidence > 1:
            raise ValueError("min_confidence must be between 0 and 1.")
        if batch_size <= 0:
            raise ValueError("batch_size must be greater than zero.")

        self._transaction_extraction_service = transaction_extraction_service
        self._recommendation_repository = recommendation_repository
        self._min_support = min_support
        self._min_confidence = min_confidence
        self._batch_size = batch_size
        self._logger = logger or logging.getLogger(self.__class__.__name__)

    def run(
        self,
        months: int = 3,
        branch_id: int | None = None,
    ) -> dict[str, int | float]:
        """Process transaction baskets in batches and persist product_pair rules."""
        started = time.perf_counter()
        tracemalloc.start()
        total_transactions = 0
        total_pairs = 0
        batch_number = 0
        self._logger.info(
            "Starting FP-Growth months=%s batch_size=%s min_support=%s min_confidence=%s branch_id=%s.",
            months,
            self._batch_size,
            self._min_support,
            self._min_confidence,
            branch_id,
        )

        for batch_number, transactions in enumerate(
            self._transaction_extraction_service.iter_product_id_transaction_batches(
                months=months,
                batch_size=self._batch_size,
                branch_id=branch_id,
            ),
            start=1,
        ):
            batch_started = time.perf_counter()
            self._logger.info(
                "Processing batch=%s baskets=%s.",
                batch_number,
                len(transactions),
            )
            rules = self.generate_rules(transactions)
            self._recommendation_repository.upsert_product_pairs(rules)

            total_transactions += len(transactions)
            total_pairs += len(rules)
            current_memory, peak_memory = tracemalloc.get_traced_memory()
            self._logger.info(
                "Current Batch=%s Transactions Processed=%s Pairs Generated=%s "
                "Execution Time=%.2fs Memory Usage=%.2fMB Peak Memory=%.2fMB",
                batch_number,
                total_transactions,
                total_pairs,
                time.perf_counter() - batch_started,
                current_memory / 1024 / 1024,
                peak_memory / 1024 / 1024,
            )

        current_memory, peak_memory = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        execution_time = time.perf_counter() - started
        self._logger.info(
            "FP-Growth completed. Current Batch=%s Transactions Processed=%s "
            "Pairs Generated=%s Execution Time=%.2fs Memory Usage=%.2fMB Peak Memory=%.2fMB",
            batch_number,
            total_transactions,
            total_pairs,
            execution_time,
            current_memory / 1024 / 1024,
            peak_memory / 1024 / 1024,
        )
        return {
            "batches": batch_number,
            "transactions_processed": total_transactions,
            "pairs_generated": total_pairs,
            "execution_time_seconds": execution_time,
        }

    def generate_rules(self, transactions: list[list[int]]) -> list[ProductPairRule]:
        """Generate one-to-one association rules from a transaction batch."""
        clean_transactions = [
            sorted({product_id for product_id in transaction if product_id > 0})
            for transaction in transactions
        ]
        clean_transactions = [transaction for transaction in clean_transactions if len(transaction) > 1]
        if not clean_transactions:
            return []

        one_hot = self._to_one_hot_dataframe(clean_transactions)
        frequent_itemsets = fpgrowth(
            one_hot,
            min_support=self._min_support,
            use_colnames=True,
        )
        if frequent_itemsets.empty:
            return []

        rules = association_rules(
            frequent_itemsets,
            metric="confidence",
            min_threshold=self._min_confidence,
        )
        if rules.empty:
            return []

        product_counts = self._product_counts(clean_transactions)
        pair_counts = self._pair_counts(clean_transactions)
        transaction_count = len(clean_transactions)
        output: list[ProductPairRule] = []

        for row in rules.itertuples(index=False):
            antecedents = tuple(row.antecedents)
            consequents = tuple(row.consequents)
            if len(antecedents) != 1 or len(consequents) != 1:
                continue

            product = int(antecedents[0])
            pair = int(consequents[0])
            if product == pair:
                continue

            output.append(
                ProductPairRule(
                    product=product,
                    pair=pair,
                    support=float(row.support),
                    confidence=float(row.confidence),
                    lift=float(row.lift),
                    cooccurrence_count=pair_counts.get((product, pair), 0),
                    antecedent_count=product_counts[product],
                    consequent_count=product_counts[pair],
                    transaction_count=transaction_count,
                )
            )

        return output

    @staticmethod
    def _to_one_hot_dataframe(transactions: list[list[int]]) -> pd.DataFrame:
        product_ids = sorted({product_id for transaction in transactions for product_id in transaction})
        rows = [
            {product_id: product_id in transaction for product_id in product_ids}
            for transaction in transactions
        ]
        return pd.DataFrame(rows, columns=product_ids, dtype=bool)

    @staticmethod
    def _product_counts(transactions: Iterable[list[int]]) -> Counter[int]:
        counts: Counter[int] = Counter()
        for transaction in transactions:
            counts.update(transaction)
        return counts

    @staticmethod
    def _pair_counts(transactions: Iterable[list[int]]) -> Counter[tuple[int, int]]:
        counts: Counter[tuple[int, int]] = Counter()
        for transaction in transactions:
            for product in transaction:
                for pair in transaction:
                    if product != pair:
                        counts[(product, pair)] += 1
        return counts
