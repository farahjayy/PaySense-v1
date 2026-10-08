"""Plan read-model: total payable is the sum of the real instalments, never a re-derived formula."""
from datetime import date

from app.services.plans import enrich_plan


def _installments(amounts, paid=0):
    return [
        {"seq": i + 1, "due_date": date(2026, 10 + i, 1) if i < 3 else date(2027, i - 2, 1), "amount": amount, "is_paid": i < paid}
        for i, amount in enumerate(amounts)
    ]


def test_total_payable_is_the_sum_of_the_instalments_on_a_fee_bearing_plan():
    # 147.62 over 6 months at 1.5%/month: 26.81 x 5 then 26.86 = 160.91 (NOT 147.62 x 1.015 = 149.83)
    plan = {"total_price": 147.62, "interest_rate": 1.5, "num_installments": 6}
    enriched = enrich_plan(plan, _installments([26.81] * 5 + [26.86]), today=date(2026, 9, 1))
    assert enriched["total_payable"] == 160.91


def test_total_payable_includes_instalments_already_paid():
    plan = {"total_price": 147.62, "interest_rate": 1.5, "num_installments": 6}
    enriched = enrich_plan(plan, _installments([26.81] * 5 + [26.86], paid=2), today=date(2026, 9, 1))
    assert enriched["total_payable"] == 160.91


def test_total_payable_has_no_float_drift():
    plan = {"total_price": 0.3, "interest_rate": 0, "num_installments": 3}
    enriched = enrich_plan(plan, _installments([0.1, 0.1, 0.1]), today=date(2026, 9, 1))
    assert enriched["total_payable"] == 0.3  # 0.1 + 0.1 + 0.1 == 0.30000000000000004 as floats
