"""Instalment schedule generation (DATABASE.md §2).

All money maths is done in integer sen (never floats): the fee is a MONTHLY
rate, total = price x (1 + monthly_rate/100 x instalments) rounded to the
nearest sen (half up), each instalment is the total divided by the count
rounded DOWN to the sen, and the leftover sen go in the LAST instalment, so the
instalments always sum to the total exactly.

Start dates follow the provider's rule in app/providers.py.
"""
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.providers import get_provider

SEN_PER_RM = 100
RATE_SCALE = 10_000  # 100% == 10_000 in fee-rate hundredths-of-a-percent maths
RATE_PRECISION = Decimal("0.01")  # fee rates are taken to 0.01% (hundredths of a percent)


def to_sen(amount: float) -> int:
    """RM (float from JSON/DB) -> integer sen, rounding half up."""
    return int((Decimal(str(amount)) * SEN_PER_RM).quantize(Decimal(1), ROUND_HALF_UP))


def from_sen(sen: int) -> float:
    return round(sen / SEN_PER_RM, 2)


def total_payable_sen(price_sen: int, monthly_rate: float, num_installments: int) -> int:
    rate_hundredths = int(
        (Decimal(str(monthly_rate)).quantize(RATE_PRECISION, ROUND_HALF_UP) * 100).to_integral_value()
    )
    numerator = price_sen * (RATE_SCALE + rate_hundredths * num_installments)
    return (numerator + RATE_SCALE // 2) // RATE_SCALE


def total_payable(total_price: float, monthly_rate: float, num_installments: int) -> float:
    """Price plus the monthly fee for every instalment month, to the nearest sen."""
    return from_sen(total_payable_sen(to_sen(total_price), monthly_rate, num_installments))


def split_sen(total_sen: int, num_installments: int) -> list[int]:
    """Equal instalments rounded down to the sen; leftover sen go in the last one."""
    base = total_sen // num_installments
    return [base] * (num_installments - 1) + [total_sen - base * (num_installments - 1)]


def add_months(start: date, months: int) -> date:
    """Month arithmetic that clamps to the last valid day (31 Jan + 1m = 28/29 Feb)."""
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    last_day = _days_in_month(year, month)
    return date(year, month, min(start.day, last_day))


def _days_in_month(year: int, month: int) -> int:
    if month == 12:
        return 31
    return (date(year, month + 1, 1) - date(year, month, 1)).days


def default_first_payment_date(provider: str, purchase_date: date) -> date:
    """First due date implied by the provider's billing rule (see app/providers.py)."""
    config = get_provider(provider)
    if config.start_rule == "months_after_purchase":
        return add_months(purchase_date, config.start_offset_months)
    return purchase_date


def is_paid_at_checkout(provider: str, first_payment_date: date, purchase_date: date) -> bool:
    """True when the first instalment is charged at checkout (e.g. Atome, unless moved later)."""
    return get_provider(provider).checkout_instalments > 0 and first_payment_date == purchase_date


def build_schedule(
    provider: str,
    total_price: float,
    monthly_rate: float,
    num_installments: int,
    purchase_date: date,
    first_payment_date: date | None = None,
) -> list[dict]:
    """Provider-aware schedule: [{seq, due_date, amount, paid_at_checkout}].

    An explicit `first_payment_date` (the user's real due date) overrides the
    provider default. A provider whose config has no monthly fee ignores the rate.
    """
    config = get_provider(provider)
    rate = monthly_rate if config.monthly_fee_applies else 0.0
    first_due = first_payment_date or default_first_payment_date(provider, purchase_date)
    checkout_count = config.checkout_instalments if is_paid_at_checkout(provider, first_due, purchase_date) else 0
    return generate_schedule(total_price, rate, num_installments, first_due, checkout_instalments=checkout_count)


def generate_schedule(
    total_price: float,
    monthly_rate: float,
    num_installments: int,
    first_payment_date: date,
    checkout_instalments: int = 0,
) -> list[dict]:
    """[{seq, due_date, amount, paid_at_checkout}] whose amounts sum to the total exactly."""
    amounts = split_sen(total_payable_sen(to_sen(total_price), monthly_rate, num_installments), num_installments)
    return [
        {
            "seq": seq,
            "due_date": add_months(first_payment_date, seq - 1),
            "amount": from_sen(amounts[seq - 1]),
            "paid_at_checkout": seq <= checkout_instalments,
        }
        for seq in range(1, num_installments + 1)
    ]
