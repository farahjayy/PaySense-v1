"""Domain constants — single source of truth (mirrored in frontend/lib/constants.ts)."""

from app.providers import PROVIDERS

HEALTH_SAFE_MIN = 70
HEALTH_CAUTION_MIN = 40
LOW_BALANCE_THRESHOLD_RM = 50
ALERT_WINDOW_DAYS = 7
FORECAST_MONTHS = 3
HISTORY_MONTHS_SHOWN = 3
MIN_MONTHS_FOR_ARIMA = 3

DEFAULT_PROFILE = {"age": 22, "employment_status": 0}

# Fixed by Engine 2 training (notebook cell 7) — must never change.
EMPLOYMENT_STATUS_ENCODING = {
    0: "student",
    1: "employed",
    2: "self-employed",
    3: "unemployed",
}

TRANSACTION_CATEGORIES = [
    "Food",
    "Transport",
    "Rent",
    "Salary",
    "Allowance",
    "Shopping",
    "Bills",
    "Entertainment",
    "Education",
    "Saving",
    "Other",
]

# Provider rules (start date, checkout share) live in app/providers.py.
BNPL_PROVIDERS = list(PROVIDERS)

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_INSTALLMENTS = 36
MAX_INTEREST_RATE = 30.0

# Cap for ratio features when the denominator is zero (div-by-zero guard).
RATIO_CAP = 10.0
