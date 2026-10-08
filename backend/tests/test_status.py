from datetime import date

from app.services.plans import derive_status, enrich_plan

TODAY = date(2026, 7, 16)


def _inst(seq, due, paid):
    return {"seq": seq, "due_date": due, "is_paid": paid, "amount": 100.0}


def test_all_paid_completed():
    installments = [_inst(1, date(2026, 5, 1), True), _inst(2, date(2026, 6, 1), True)]
    assert derive_status(installments, today=TODAY) == "completed"


def test_unpaid_past_due_overdue():
    installments = [_inst(1, date(2026, 6, 1), True), _inst(2, date(2026, 7, 1), False)]
    assert derive_status(installments, today=TODAY) == "overdue"


def test_unpaid_future_active():
    installments = [_inst(1, date(2026, 7, 1), True), _inst(2, date(2026, 8, 1), False)]
    assert derive_status(installments, today=TODAY) == "active"


def test_enrich_plan_computed_fields():
    plan = {"id": "x", "item_name": "Sneakers", "status": "active"}
    installments = [
        _inst(1, date(2026, 6, 20), True),
        _inst(2, date(2026, 7, 20), False),
        _inst(3, date(2026, 8, 20), False),
    ]
    enriched = enrich_plan(plan, installments, today=TODAY)
    assert enriched["paid_count"] == 1
    assert enriched["remaining_count"] == 2
    assert enriched["next_due_date"] == "2026-07-20"
    assert enriched["installment_amount"] == 100.0
    # Immutability: input dict untouched.
    assert "paid_count" not in plan
