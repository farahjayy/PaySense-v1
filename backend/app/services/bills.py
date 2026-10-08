"""Monthly bill grouping — instalments due across every tracked plan, by calendar month.

Powers a "My Bills"-style dashboard list: how much is due each month and whether it is
fully paid. Order: the current month first (only if something is actually due in it — no
synthetic RM0 row), then past months going backward, then upcoming months going forward.
"""
from datetime import date


def _month_key(due_date: date) -> str:
    return due_date.strftime("%Y-%m")


def monthly_bills(plans: list[dict], today: date | None = None) -> dict:
    """{months}: one entry per month that has at least one instalment, in display order."""
    today = today or date.today()
    buckets: dict[str, list[dict]] = {}
    for plan in plans:
        for installment in plan["installments"]:
            buckets.setdefault(_month_key(installment["due_date"]), []).append(
                {
                    "plan_id": plan["id"],
                    "item_name": plan["item_name"],
                    "provider": plan["provider"],
                    "seq": installment["seq"],
                    "amount": float(installment["amount"]),
                    "due_date": installment["due_date"].isoformat(),
                    "is_paid": installment["is_paid"],
                }
            )

    current_key = _month_key(today)
    past = sorted(k for k in buckets if k < current_key)
    future = sorted(k for k in buckets if k > current_key)
    ordered_keys = ([current_key] if current_key in buckets else []) + list(reversed(past)) + future

    months = []
    for month in ordered_keys:
        items = sorted(buckets[month], key=lambda i: (i["due_date"], i["item_name"]))
        months.append(
            {
                "month": month,
                "is_current": month == current_key,
                "total_due": round(sum(i["amount"] for i in items), 2),
                "paid_total": round(sum(i["amount"] for i in items if i["is_paid"]), 2),
                "fully_paid": all(i["is_paid"] for i in items),
                "has_overdue": any(not i["is_paid"] and i["due_date"] < today.isoformat() for i in items),
                "items": items,
            }
        )
    return {"months": months}
