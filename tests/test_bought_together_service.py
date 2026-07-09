"""Tests for bought-together relationship generation."""

import unittest

from recommendation_engine.services.bought_together_service import (
    BoughtTogetherService,
)


class BoughtTogetherServiceTest(unittest.TestCase):
    def test_build_relationships_from_transactions_normalizes_unique_pairs(self):
        relationships = BoughtTogetherService.build_relationships_from_transactions(
            [
                [300, 100, 200, 100],
                [200, 300],
                [400],
                [],
            ]
        )

        self.assertEqual(
            [(relationship.product, relationship.pair) for relationship in relationships],
            [(100, 200), (100, 300), (200, 300)],
        )

    def test_build_relationships_from_transactions_ignores_invalid_product_ids(self):
        relationships = BoughtTogetherService.build_relationships_from_transactions(
            [[100, 0, -1, 200]]
        )

        self.assertEqual(
            [(relationship.product, relationship.pair) for relationship in relationships],
            [(100, 200)],
        )


if __name__ == "__main__":
    unittest.main()
