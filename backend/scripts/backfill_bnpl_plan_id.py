"""Link transactions logged BEFORE bnpl_plan_id existed to the plan whose payment logged them.

Run once after migration 002. Dry run by default (prints what it would link); add --apply to write.

    cd backend && .venv/Scripts/python scripts/backfill_bnpl_plan_id.py            # preview
    cd backend && .venv/Scripts/python scripts/backfill_bnpl_plan_id.py --apply    # link

Old rows can only be matched by the text the pay endpoint used to write, so this is deliberately
strict: an unlinked BNPL expense with EXACTLY the description, amount and paid date of a paid
instalment, one transaction per paid instalment. Anything else stays unlinked (and is then never
offered or deleted by plan deletion). New payments are linked by ID as they are logged.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import repo  # noqa: E402
from app.services.plan_transactions import installment_description  # noqa: E402
from app.services.schedule import to_sen  # noqa: E402

SEARCH_LIMIT = 200


def find_links(plan: dict) -> list[tuple[dict, dict]]:
    """[(instalment, transaction)] for the plan's paid instalments with an unlinked exact-match expense."""
    paid = [i for i in plan["installments"] if i["is_paid"] and i.get("paid_date")]
    if not paid:
        return []
    candidates, _ = repo.list_transactions(search=plan["item_name"], type_="expense", limit=SEARCH_LIMIT)
    used: set[str] = set()
    links = []
    for installment in sorted(paid, key=lambda i: i["seq"]):
        wanted = installment_description(plan, installment["seq"])
        for tx in candidates:
            if (
                tx["id"] not in used
                and not tx.get("bnpl_plan_id")
                and tx.get("is_bnpl")
                and tx.get("description") == wanted
                and to_sen(float(tx["amount"])) == to_sen(float(installment["amount"]))
                and str(tx["date"])[:10] == str(installment["paid_date"])[:10]
            ):
                links.append((installment, tx))
                used.add(tx["id"])
                break
    return links


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--apply", action="store_true", help="write the links (default is a dry run)")
    args = parser.parse_args()

    total = 0
    for plan in repo.list_plans():
        for installment, tx in find_links(plan):
            total += 1
            print(f"{plan['item_name']} #{installment['seq']}: {tx['date']} RM{tx['amount']} ({tx['id']})")
            if args.apply:
                repo.update_transaction(tx["id"], {"bnpl_plan_id": plan["id"]})
    print(f"{'Linked' if args.apply else 'Would link'} {total} transaction(s).")


if __name__ == "__main__":
    main()
