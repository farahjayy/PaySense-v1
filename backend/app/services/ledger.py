"""Ledger-mode balance math — how a transaction moves Current Balance.

Only used when app_state.ledger_mode is true. When false, Current Balance
changes only via Balance Sync (original, still-default behaviour).
"""

# income adds money to the main account; expense and savings both remove it
# (savings = money genuinely leaving the pile, even though it isn't spending).
_SIGN = {"income": 1, "expense": -1, "savings": -1}


def signed_amount(type_: str, amount: float) -> float:
    return _SIGN[type_] * float(amount)


def transaction_delta(row: dict) -> float:
    """The balance effect of one transaction row (as stored: type + amount)."""
    return signed_amount(row["type"], row["amount"])


def edit_delta(old_row: dict, new_type: str, new_amount: float) -> float:
    """Net balance change when a transaction's type/amount changes on edit."""
    return signed_amount(new_type, new_amount) - transaction_delta(old_row)
