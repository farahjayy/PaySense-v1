"""Ledger-mode balance math (app/services/ledger.py)."""
from app.services.ledger import edit_delta, signed_amount, transaction_delta


def test_income_adds():
    assert signed_amount("income", 100.0) == 100.0


def test_expense_subtracts():
    assert signed_amount("expense", 40.0) == -40.0


def test_savings_subtracts_like_expense():
    # Money genuinely leaves the main account when set aside.
    assert signed_amount("savings", 1000.0) == -1000.0


def test_transaction_delta_reads_type_and_amount_from_row():
    row = {"type": "expense", "amount": 25.5}
    assert transaction_delta(row) == -25.5


def test_edit_delta_same_type_amount_increase():
    before = {"type": "expense", "amount": 20.0}
    # RM20 expense edited up to RM30 -> balance should move down another RM10.
    assert edit_delta(before, "expense", 30.0) == -10.0


def test_edit_delta_type_change_reverses_old_and_applies_new():
    before = {"type": "expense", "amount": 100.0}
    # Reclassified expense -> savings, same amount: no net balance change
    # (both directions are -amount).
    assert edit_delta(before, "savings", 100.0) == 0.0


def test_edit_delta_type_change_income_to_expense():
    before = {"type": "income", "amount": 50.0}
    # Was +50, now -50 -> total swing of -100.
    assert edit_delta(before, "expense", 50.0) == -100.0
