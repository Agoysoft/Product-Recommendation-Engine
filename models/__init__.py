"""Model package for data transfer models."""

from recommendation_engine.models.transaction import (
    TransactionBasket,
    TransactionItem,
)

__all__ = [
    "TransactionBasket",
    "TransactionItem",
]
