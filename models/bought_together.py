"""Bought-together relationship data models."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BoughtTogetherRelationship:
    """A normalized bought-together product pair."""

    product: int
    pair: int

    def __post_init__(self) -> None:
        if self.product <= 0:
            raise ValueError("product must be greater than zero.")
        if self.pair <= 0:
            raise ValueError("pair must be greater than zero.")
        if self.product == self.pair:
            raise ValueError("product and pair must be different.")
        if self.product > self.pair:
            product = self.product
            pair = self.pair
            object.__setattr__(self, "product", pair)
            object.__setattr__(self, "pair", product)
