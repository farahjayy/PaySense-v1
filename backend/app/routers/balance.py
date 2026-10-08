"""Balance sync + profile (Engine 2 demographics)."""
from fastapi import APIRouter

from app.db import repo
from app.schemas import BalanceUpdate, ProfileUpdate

router = APIRouter(prefix="/api", tags=["balance"])


@router.get("/balance")
def get_balance():
    state = repo.get_app_state()
    return {
        "current_balance": float(state["current_balance"]),
        "balance_synced_at": state["balance_synced_at"],
    }


@router.put("/balance")
def update_balance(body: BalanceUpdate):
    state = repo.update_balance(body.current_balance)
    return {
        "current_balance": float(state["current_balance"]),
        "balance_synced_at": state["balance_synced_at"],
    }


@router.get("/profile")
def get_profile():
    state = repo.get_app_state()
    return state["profile"]


@router.put("/profile")
def update_profile(body: ProfileUpdate):
    return repo.update_profile(body.model_dump())
