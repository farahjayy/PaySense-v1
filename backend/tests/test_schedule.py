from datetime import date

import pytest

from app.providers import PROVIDERS, ProviderConfig
from app.services.schedule import (
    add_months,
    build_schedule,
    default_first_payment_date,
    generate_schedule,
    is_paid_at_checkout,
    total_payable,
)


def _sum(schedule):
    return round(sum(item["amount"] for item in schedule), 2)


def test_sum_equals_total_payable_899_x6_zero_interest():
    schedule = generate_schedule(899.00, 0, 6, date(2026, 5, 5))
    assert _sum(schedule) == 899.00
    assert len(schedule) == 6


def test_sum_equals_total_payable_429_x3_with_monthly_fee():
    # 5% per month x 3 months = 15% on top of the price
    schedule = generate_schedule(429.00, 5, 3, date(2026, 6, 20))
    assert _sum(schedule) == total_payable(429.00, 5, 3) == 493.35


def test_awkward_rounding_100_x3():
    schedule = generate_schedule(100.00, 0, 3, date(2026, 1, 15))
    assert _sum(schedule) == 100.00
    assert schedule[0]["amount"] == 33.33
    assert schedule[2]["amount"] == 33.34


def test_due_dates_monthly_from_first_payment():
    schedule = generate_schedule(300.00, 0, 3, date(2026, 3, 10))
    assert [s["due_date"] for s in schedule] == [
        date(2026, 3, 10),
        date(2026, 4, 10),
        date(2026, 5, 10),
    ]


def test_month_end_edge_31_jan():
    schedule = generate_schedule(300.00, 0, 3, date(2026, 1, 31))
    assert [s["due_date"] for s in schedule] == [
        date(2026, 1, 31),
        date(2026, 2, 28),
        date(2026, 3, 31),
    ]


def test_add_months_leap_year():
    assert add_months(date(2024, 1, 31), 1) == date(2024, 2, 29)


def test_zero_interest_sum_equals_price():
    schedule = generate_schedule(1234.56, 0, 12, date(2026, 7, 1))
    assert _sum(schedule) == 1234.56


# --- monthly fee rate, integer-sen maths (Part 1) ---

def _amounts(schedule):
    return [item["amount"] for item in schedule]


def test_monthly_fee_six_instalments_at_1_5_percent():
    schedule = generate_schedule(147.62, 1.5, 6, date(2026, 9, 1))
    assert total_payable(147.62, 1.5, 6) == 160.91
    assert _amounts(schedule) == [26.81, 26.81, 26.81, 26.81, 26.81, 26.86]


def test_zero_fee_three_instalments_leftover_sen_in_last():
    schedule = generate_schedule(147.62, 0, 3, date(2026, 9, 1))
    assert total_payable(147.62, 0, 3) == 147.62
    assert _amounts(schedule) == [49.20, 49.20, 49.22]


def test_monthly_fee_twelve_instalments_at_1_5_percent():
    schedule = generate_schedule(147.62, 1.5, 12, date(2026, 9, 1))
    assert total_payable(147.62, 1.5, 12) == 174.19
    assert _amounts(schedule) == [14.51] * 11 + [14.58]


@pytest.mark.parametrize("price, rate, count", [(147.62, 1.5, 6), (899.99, 1.25, 7), (0.10, 1.5, 12), (5000.0, 0.5, 6)])
def test_instalments_always_sum_to_the_total_exactly(price, rate, count):
    schedule = generate_schedule(price, rate, count, date(2026, 9, 1))
    assert _sum(schedule) == total_payable(price, rate, count)
    assert all(a <= schedule[-1]["amount"] for a in _amounts(schedule))  # remainder never lands early


def test_total_rounds_half_up_to_the_nearest_sen():
    # 0.50 x (1 + 0.015 x 6) = 0.545 exactly half a sen -> rounds up to 0.55
    assert total_payable(0.50, 1.5, 6) == 0.55


# --- provider config + start rules (docs/BNPL Billing Rules ...md) ---

def test_tiktok_first_bill_is_next_month_same_day():
    assert default_first_payment_date("TikTok PayLater", date(2026, 9, 25)) == date(2026, 10, 25)


def test_atome_first_payment_is_the_purchase_date():
    assert default_first_payment_date("Atome", date(2026, 9, 25)) == date(2026, 9, 25)


def test_unknown_provider_keeps_purchase_date_start():
    assert default_first_payment_date("Other", date(2026, 9, 25)) == date(2026, 9, 25)
    assert default_first_payment_date("GrabPayLater", date(2026, 9, 25)) == date(2026, 9, 25)


def test_next_month_start_clamps_at_month_end():
    assert default_first_payment_date("TikTok PayLater", date(2026, 1, 31)) == date(2026, 2, 28)


def test_spaylater_first_bill_is_next_month_same_day():
    assert default_first_payment_date("SPayLater", date(2026, 9, 25)) == date(2026, 10, 25)


def test_spaylater_repeats_the_same_day_each_month():
    schedule = build_schedule("SPayLater", 300.0, 0, 3, date(2026, 9, 26))
    assert [s["due_date"] for s in schedule] == [date(2026, 10, 26), date(2026, 11, 26), date(2026, 12, 26)]


def test_pay_later_schedules_never_start_on_the_purchase_date_and_nothing_is_prepaid():
    purchase = date(2026, 9, 25)
    for provider in ("SPayLater", "TikTok PayLater"):
        schedule = build_schedule(provider, 600.0, 0, 6, purchase)
        assert schedule[0]["due_date"] > purchase
        assert not any(item["paid_at_checkout"] for item in schedule)
        assert _sum(schedule) == 600.0


def test_atome_schedule_charges_the_first_payment_at_checkout():
    schedule = build_schedule("Atome", 300.0, 0, 3, date(2026, 9, 25))
    assert [s["due_date"] for s in schedule] == [date(2026, 9, 25), date(2026, 10, 25), date(2026, 11, 25)]
    assert [s["paid_at_checkout"] for s in schedule] == [True, False, False]
    assert schedule[0]["amount"] == 100.0  # one-third at checkout
    assert is_paid_at_checkout("Atome", date(2026, 9, 25), date(2026, 9, 25))


def test_atome_six_month_plan_still_charges_the_first_payment_at_checkout():
    schedule = build_schedule("Atome", 147.62, 1.5, 6, date(2026, 9, 25))
    assert schedule[0]["paid_at_checkout"] is True
    assert schedule[0]["amount"] == 26.81


def test_explicit_first_payment_date_overrides_the_provider_default():
    schedule = build_schedule("SPayLater", 300.0, 0, 3, date(2026, 9, 25), first_payment_date=date(2026, 10, 10))
    assert schedule[0]["due_date"] == date(2026, 10, 10)


def test_atome_first_payment_moved_off_the_purchase_date_is_not_prepaid():
    schedule = build_schedule("Atome", 300.0, 0, 3, date(2026, 9, 25), first_payment_date=date(2026, 10, 25))
    assert not any(item["paid_at_checkout"] for item in schedule)


def test_adding_a_provider_is_one_config_entry(monkeypatch):
    monkeypatch.setitem(
        PROVIDERS, "TestPay",
        ProviderConfig(name="TestPay", checkout_instalments=1, start_rule="months_after_purchase", start_offset_months=2),
    )
    schedule = build_schedule("TestPay", 300.0, 0, 3, date(2026, 9, 25))
    assert schedule[0]["due_date"] == date(2026, 11, 25)
    assert schedule[0]["paid_at_checkout"] is False  # first due is not the purchase date, so nothing is prepaid


def test_a_provider_without_a_monthly_fee_ignores_the_entered_rate(monkeypatch):
    monkeypatch.setitem(PROVIDERS, "NoFeePay", ProviderConfig(name="NoFeePay", monthly_fee_applies=False))
    schedule = build_schedule("NoFeePay", 300.0, 1.5, 3, date(2026, 9, 25))
    assert _sum(schedule) == 300.0
