"""Pydantic request/response models — validation at the API boundary."""
from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.constants import MAX_INSTALLMENTS, MAX_INTEREST_RATE

TransactionType = Literal["income", "expense", "savings"]


# --- Transactions ---

class TransactionCreate(BaseModel):
    date: date
    amount: float = Field(gt=0)
    type: TransactionType
    category: str = Field(min_length=1)
    description: Optional[str] = None
    account_name: Optional[str] = None
    is_bnpl: bool = False


class TransactionUpdate(BaseModel):
    date: Optional[date] = None
    amount: Optional[float] = Field(default=None, gt=0)
    type: Optional[TransactionType] = None
    category: Optional[str] = Field(default=None, min_length=1)
    description: Optional[str] = None
    account_name: Optional[str] = None
    is_bnpl: Optional[bool] = None


# --- Balance / profile ---

class BalanceUpdate(BaseModel):
    current_balance: float


class ProfileUpdate(BaseModel):
    age: int = Field(ge=18, le=30)
    employment_status: int = Field(ge=0, le=3)


# --- BNPL ---

class PlanCreate(BaseModel):
    item_name: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    total_price: float = Field(gt=0)
    interest_rate: float = Field(ge=0, le=MAX_INTEREST_RATE)
    num_installments: int = Field(ge=1, le=MAX_INSTALLMENTS)
    purchase_date: Optional[date] = None  # defaults to today
    first_payment_date: Optional[date] = None  # overrides the provider's default first due date


class PlanUpdate(BaseModel):
    """The only editable plan field is the item name (cosmetic). Anything else is rejected: price,
    fee, instalments and dates feed the schedule; to change them, delete the plan and create a new one."""
    model_config = ConfigDict(extra="forbid")

    item_name: str = Field(min_length=1)

    @field_validator("item_name")
    @classmethod
    def _name_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("item_name must not be blank")
        return stripped


class PayInstallmentRequest(BaseModel):
    paid_date: Optional[date] = None
    create_transaction: bool = True


# --- Risk ---

class RiskCheckRequest(BaseModel):
    item_name: str = Field(min_length=1)
    total_price: float = Field(gt=0)
    provider: str = Field(min_length=1)
    num_installments: int = Field(ge=1, le=MAX_INSTALLMENTS)
    purchase_date: Optional[date] = None  # defaults to today
    first_payment_date: Optional[date] = None  # overrides the provider's default first due date
    interest_rate: float = Field(ge=0, le=MAX_INTEREST_RATE)  # monthly fee, % per month


class RiskConfirmRequest(BaseModel):
    check_id: str


# --- Imports ---

class ImportRow(BaseModel):
    row: int
    date: date
    amount: float = Field(gt=0)
    type: TransactionType
    category_guess: str
    description: Optional[str] = None
    issues: list[str] = []


class ImportConfirmRequest(BaseModel):
    import_id: str
    rows: list[ImportRow]
