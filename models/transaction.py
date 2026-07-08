"""Transaction extraction data models."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any


@dataclass(frozen=True, slots=True)
class TransactionItem:
    """One product line inside a sale transaction."""

    product_id: int
    product_name: str | None
    ui_code: str | None
    quantity: Decimal | None
    selling_price: Decimal | None


@dataclass(frozen=True, slots=True)
class TransactionBasket:
    """A reconstructed supermarket sale basket."""

    sale_id: int
    invoice: str | None
    customer_id: int | None
    branch_id: int
    sale_date: date | None
    items: tuple[TransactionItem, ...]

    @property
    def product_ids(self) -> list[int]:
        """Return unique product IDs in this basket."""
        return sorted({item.product_id for item in self.items})

    @property
    def product_names(self) -> list[str]:
        """Return unique available product names in this basket."""
        return sorted(
            {
                item.product_name
                for item in self.items
                if item.product_name is not None
            }
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the basket for diagnostics or downstream processing."""
        return {
            "sale_id": self.sale_id,
            "invoice": self.invoice,
            "customer_id": self.customer_id,
            "branch_id": self.branch_id,
            "sale_date": self.sale_date,
            "product_ids": self.product_ids,
            "items": [
                {
                    "product_id": item.product_id,
                    "product_name": item.product_name,
                    "ui_code": item.ui_code,
                    "quantity": item.quantity,
                    "selling_price": item.selling_price,
                }
                for item in self.items
            ],
        }
