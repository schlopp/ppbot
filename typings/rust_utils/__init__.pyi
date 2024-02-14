"""
Utility module written in Rust using PyO3 and Maturin. Typestubs maintained manually.


Type conversions for Rust (PyO3) -> Python: https://pyo3.rs/v0.19.2/conversions/tables
"""

__all__ = [
    "compute_multiplier_item_cost",
    "compute_max_multiplier_item_purchase_amount",
]

def compute_multiplier_item_cost(
    amount: int, current_multiplier: int, item_price: int, item_gain: int
) -> tuple[int, int]:
    """
    Computes the price of buying a certain amount of a multiplier item, along with the gain it'll
    give. Returns tuple `(cost: int, gain: int)`.
    """
    ...

def compute_max_multiplier_item_purchase_amount(
    available_inches: int, current_multiplier: int, item_price: int, item_gain: int
) -> tuple[int, int, int]:
    """
    Computes the maximum purchasable amount of a multiplier item, along with the cost and the gain
    it'll give. Returns tuple `(amount: int, cost: int, gain: int)`.
    """
    ...
