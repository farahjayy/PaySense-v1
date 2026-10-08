"""ML endpoints: forecast, risk check (the flagship flow), risk confirm."""
import logging
from datetime import date

from fastapi import APIRouter

from app.db import repo
from app.errors import conflict, not_found
from app.schemas import RiskCheckRequest, RiskConfirmRequest
from app.services import pipeline
from app.services.plans import create_plan_with_checkout_payment
from app.services.schedule import build_schedule

logger = logging.getLogger("paysense")
router = APIRouter(prefix="/api", tags=["ml"])


def _stored_date(stored_input: dict, key: str) -> date | None:
    """Dates are stored as ISO strings; checks saved before purchase_date existed lack that key."""
    value = stored_input.get(key)
    return date.fromisoformat(value) if value else None


def _stored_monthly_rate(stored_input: dict) -> float:
    """Checks saved before the fee became a monthly rate stored a whole-plan %; convert them."""
    rate = stored_input["interest_rate"]
    if stored_input.get("fee_basis") == "monthly":
        return rate
    return round(rate / stored_input["num_installments"], 2)


@router.get("/forecast")
def get_forecast():
    result = pipeline.run_forecast()
    result.pop("_months", None)
    return result


@router.post("/risk/check")
def risk_check(body: RiskCheckRequest):
    return pipeline.run_risk_check(body.model_dump())


@router.post("/risk/confirm", status_code=201)
def risk_confirm(body: RiskConfirmRequest):
    check = repo.get_risk_check(body.check_id)
    if check is None:
        raise not_found("CHECK_NOT_FOUND", "That risk check doesn't exist — run the check again.")
    stored_input = check["input"]
    if stored_input.get("_confirmed_plan_id"):
        raise conflict("ALREADY_CONFIRMED", "This risk check was already saved as a plan.")

    monthly_rate = _stored_monthly_rate(stored_input)
    schedule = build_schedule(
        stored_input["provider"],
        stored_input["total_price"],
        monthly_rate,
        stored_input["num_installments"],
        _stored_date(stored_input, "purchase_date") or _stored_date(stored_input, "first_payment_date"),
        _stored_date(stored_input, "first_payment_date"),
    )
    plan = create_plan_with_checkout_payment(
        {
            "item_name": stored_input["item_name"],
            "provider": stored_input["provider"],
            "total_price": stored_input["total_price"],
            "interest_rate": monthly_rate,
            "num_installments": stored_input["num_installments"],
            "first_payment_date": schedule[0]["due_date"].isoformat(),
            "risk_score_at_creation": check["risk_score"],
        },
        schedule,
    )
    repo.mark_risk_check_confirmed(check["id"], plan["id"], stored_input)

    from app.routers.bnpl import _serialize

    return _serialize(plan, include_installments=True)
