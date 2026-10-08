"""Transaction deletes that keep Current Balance in step.

delete_with_ledger: the Transactions page delete (balance moves only in ledger mode).
delete_payment_transaction: removing the expense an instalment payment logged. Paying an
instalment ALWAYS subtracts it from the balance (whatever the ledger mode), so removing
that logged payment always gives the money back.
"""
from app.db import repo
from app.services import ledger


def is_ledger_mode() -> bool:
    return bool(repo.get_app_state().get("ledger_mode", False))


def delete_with_ledger(transaction_id: str) -> bool:
    apply_ledger = is_ledger_mode()
    before = repo.get_transaction(transaction_id) if apply_ledger else None
    if not repo.delete_transaction(transaction_id):
        return False
    if apply_ledger and before is not None:
        repo.adjust_balance(-ledger.transaction_delta(before))
    return True


def delete_payment_transaction(transaction: dict) -> bool:
    """Delete a logged instalment payment and return its amount to the balance."""
    if not repo.delete_transaction(transaction["id"]):
        return False
    repo.adjust_balance(-ledger.transaction_delta(transaction))
    return True
