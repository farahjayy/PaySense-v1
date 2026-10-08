"""Renaming a BNPL plan.

The item name is the only editable field (price, fee, instalments and dates feed the
schedule; to change those, delete the plan and create a new one). Renaming is cosmetic: it
never touches amounts, dates, instalments or the balance.

Transactions logged by the plan are linked by bnpl_plan_id, not by text, so a rename cannot
break plan deletion. The linked transactions' descriptions are updated too, so the
Transactions list shows the current name; a description the user rewrote (one that no longer
ends with the old name) is left as they wrote it.
"""
import logging

from app.db import repo
from app.services.plan_transactions import find_plan_transactions

logger = logging.getLogger("paysense")


def rename_plan(plan: dict, new_name: str) -> None:
    old_name = plan["item_name"]
    if new_name == old_name:
        return
    repo.update_plan_fields(plan["id"], {"item_name": new_name})

    old_suffix, new_suffix = f" \u2014 {old_name}", f" \u2014 {new_name}"
    for transaction in find_plan_transactions(plan):
        description = transaction.get("description") or ""
        if not description.endswith(old_suffix):
            continue
        try:
            repo.update_transaction(
                transaction["id"], {"description": description[: -len(old_suffix)] + new_suffix}
            )
        except Exception:
            logger.exception("Couldn't rename transaction %s for plan %s", transaction["id"], plan["id"])
