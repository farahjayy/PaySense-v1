"""BNPL provider rules as data — adding a provider means adding one PROVIDERS entry.

Source: docs/BNPL Billing Rules SPayLater, TikTok PayLater, Atome (Malaysia).md.
Mirrored in frontend/lib/providers.ts (the backend is the authority when a plan
is created; the frontend copy only drives live previews).

Fields
  checkout_instalments   leading instalments charged at checkout, i.e. a share
                         (that many / N) of the total paid on the purchase date.
                         Atome: 1 (one-third of a 3-payment plan).
  start_rule             how the first due date is derived from the purchase date:
                           "purchase_date"          the purchase date itself
                           "months_after_purchase"  purchase date + start_offset_months
                         Every later instalment repeats the first date's day-of-month
                         each month, so the start rule also fixes the due-day rule.
  monthly_fee_applies    False forces the fee to 0 whatever the user enters.

Assumptions (see docs/KNOWN_LIMITATIONS.md): SPayLater and TikTok PayLater use one
uniform "next month, same day" first bill. SPayLater's real billing-cycle days and
TikTok's first due date are unconfirmed, so the first payment date is always an
editable estimate.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    checkout_instalments: int = 0
    start_rule: str = "purchase_date"
    start_offset_months: int = 0
    monthly_fee_applies: bool = True


PROVIDERS: dict[str, ProviderConfig] = {
    "SPayLater": ProviderConfig(name="SPayLater", start_rule="months_after_purchase", start_offset_months=1),
    "TikTok PayLater": ProviderConfig(name="TikTok PayLater", start_rule="months_after_purchase", start_offset_months=1),
    "Atome": ProviderConfig(name="Atome", checkout_instalments=1),
    "Other": ProviderConfig(name="Other"),
}

FALLBACK_PROVIDER = "Other"


def get_provider(name: str) -> ProviderConfig:
    """Config for `name`; unknown or retired providers (e.g. old plan rows) behave as Other."""
    return PROVIDERS.get(name, PROVIDERS[FALLBACK_PROVIDER])
