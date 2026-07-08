"""Tests for transaction extraction basket grouping."""

from datetime import date
from decimal import Decimal
import unittest

from recommendation_engine.services.transaction_extraction_service import (
    TransactionExtractionService,
)


class _FakeTransactionRepository:
    def fetch_sale_item_rows(self, **_kwargs):
        return [
            {
                "sale_id": 10,
                "invoice": "INV-10",
                "customer_id": 5,
                "branch_id": 1,
                "sale_date": date(2026, 7, 1),
                "product_id": 100,
                "qty": Decimal("2.000"),
                "selling_price": Decimal("150.00"),
                "product_name": "Rice",
                "ui_code": "P100",
            },
            {
                "sale_id": 10,
                "invoice": "INV-10",
                "customer_id": 5,
                "branch_id": 1,
                "sale_date": date(2026, 7, 1),
                "product_id": 200,
                "qty": Decimal("1.000"),
                "selling_price": Decimal("90.00"),
                "product_name": "Milk",
                "ui_code": "P200",
            },
            {
                "sale_id": 11,
                "invoice": "INV-11",
                "customer_id": 6,
                "branch_id": 1,
                "sale_date": date(2026, 7, 2),
                "product_id": 100,
                "qty": Decimal("1.000"),
                "selling_price": Decimal("150.00"),
                "product_name": "Rice",
                "ui_code": "P100",
            },
        ]


class TransactionExtractionServiceTest(unittest.TestCase):
    def test_extract_baskets_groups_rows_by_sale(self):
        service = TransactionExtractionService(_FakeTransactionRepository())

        baskets = service.extract_baskets(branch_id=1, months=3)

        self.assertEqual(len(baskets), 2)
        self.assertEqual(baskets[0].sale_id, 10)
        self.assertEqual(baskets[0].product_ids, [100, 200])
        self.assertEqual(baskets[1].sale_id, 11)
        self.assertEqual(baskets[1].product_ids, [100])

    def test_extract_one_hot_dataframe_uses_product_ids_as_columns(self):
        service = TransactionExtractionService(_FakeTransactionRepository())

        dataframe = service.extract_one_hot_dataframe(branch_id=1, months=3)

        self.assertEqual(list(dataframe.columns), [100, 200])
        self.assertEqual(dataframe.shape, (2, 2))
        self.assertTrue(dataframe.loc[0, 100])
        self.assertTrue(dataframe.loc[0, 200])
        self.assertTrue(dataframe.loc[1, 100])
        self.assertFalse(dataframe.loc[1, 200])


if __name__ == "__main__":
    unittest.main()
