"""Tests for pair-count metric calculation and rule generation."""

import unittest

from recommendation_engine.services.pair_count_service import (
    PairCountRecommendationService,
)


class _FakeTransactionExtractionService:
    def iter_product_id_transaction_batches(self, **_kwargs):
        return iter([])


class _FakeRecommendationRepository:
    def upsert_product_pairs(self, _rules):
        return 0


class PairCountRecommendationServiceTest(unittest.TestCase):
    def test_metric_calculations(self):
        self.assertAlmostEqual(PairCountRecommendationService._calculate_support(5, 20), 0.25)
        self.assertAlmostEqual(PairCountRecommendationService._calculate_confidence(5, 10), 0.5)
        self.assertAlmostEqual(
            PairCountRecommendationService._calculate_lift(0.5, consequent_count=10, transaction_count=20),
            1.0,
        )

    def test_generate_rules_calculates_support_confidence_and_lift(self):
        service = PairCountRecommendationService(
            transaction_extraction_service=_FakeTransactionExtractionService(),
            recommendation_repository=_FakeRecommendationRepository(),
            min_support=0.25,
            min_confidence=0.5,
            batch_size=10,
        )

        rules = service.generate_rules(
            [
                [1, 2],
                [1, 2],
                [1, 3],
                [2, 3],
            ]
        )

        forward = next(rule for rule in rules if rule.product == 1 and rule.pair == 2)
        reverse = next(rule for rule in rules if rule.product == 2 and rule.pair == 1)

        self.assertAlmostEqual(forward.support, 0.5)
        self.assertAlmostEqual(forward.confidence, 2 / 3)
        self.assertAlmostEqual(forward.lift, (2 / 3) / (3 / 4))
        self.assertEqual(forward.cooccurrence_count, 2)
        self.assertEqual(forward.antecedent_count, 3)
        self.assertEqual(forward.consequent_count, 3)
        self.assertEqual(forward.transaction_count, 4)

        self.assertAlmostEqual(reverse.support, 0.5)
        self.assertAlmostEqual(reverse.confidence, 2 / 3)
        self.assertAlmostEqual(reverse.lift, (2 / 3) / (3 / 4))

    def test_generate_rules_ignores_single_item_baskets(self):
        service = PairCountRecommendationService(
            transaction_extraction_service=_FakeTransactionExtractionService(),
            recommendation_repository=_FakeRecommendationRepository(),
        )

        rules = service.generate_rules([[1], [2], [3]])

        self.assertEqual(rules, [])


if __name__ == "__main__":
    unittest.main()
