"""CSV/PDF statement import: preview (no writes) → user edits → confirm."""
import io
import logging
import re
import uuid
from datetime import date

import pandas as pd
from fastapi import APIRouter, UploadFile

from app.constants import MAX_UPLOAD_BYTES
from app.db import repo
from app.errors import not_found, unprocessable
from app.schemas import ImportConfirmRequest
from app.services import ledger
from app.services.categorize import guess_category, guess_type

logger = logging.getLogger("paysense")
router = APIRouter(prefix="/api/import", tags=["imports"])

# Preview store: in-memory is fine for the single-user demo.
_previews: dict[str, dict] = {}

DATE_COLUMNS = ["date", "transaction date", "txn date", "posting date", "tarikh"]
DESC_COLUMNS = ["description", "details", "transaction details", "item", "narrative", "keterangan"]
AMOUNT_COLUMNS = ["amount", "amount (rm)", "amount(rm)", "amaun"]
DEBIT_COLUMNS = ["debit", "debit (rm)", "withdrawal"]
CREDIT_COLUMNS = ["credit", "credit (rm)", "deposit"]


async def _read_upload(file: UploadFile, expected: str) -> bytes:
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise unprocessable("FILE_TOO_LARGE", "File is over 5 MB — export a shorter date range.")
    name = (file.filename or "").lower()
    if expected == "csv" and not name.endswith(".csv"):
        raise unprocessable("WRONG_FILE_TYPE", "Please upload a .csv file.")
    if expected == "pdf":
        if not name.endswith(".pdf"):
            raise unprocessable("WRONG_FILE_TYPE", "Please upload a .pdf file.")
        if not content.startswith(b"%PDF"):
            raise unprocessable("WRONG_FILE_TYPE", "That file isn't a valid PDF.")
    return content


def _find_column(columns: list[str], candidates: list[str]) -> str | None:
    for candidate in candidates:
        for col in columns:
            if candidate == col or candidate in col:
                return col
    return None


def _rows_from_dataframe(df: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    df.columns = [str(c).strip().lower() for c in df.columns]
    columns = list(df.columns)
    date_col = _find_column(columns, DATE_COLUMNS)
    desc_col = _find_column(columns, DESC_COLUMNS)
    amount_col = _find_column(columns, AMOUNT_COLUMNS)
    debit_col = _find_column(columns, DEBIT_COLUMNS)
    credit_col = _find_column(columns, CREDIT_COLUMNS)

    if date_col is None or (amount_col is None and debit_col is None and credit_col is None):
        raise unprocessable(
            "CSV_MISSING_COLUMNS",
            "Couldn't find date/amount columns — the file needs at least a date and an amount column.",
        )

    rows, skipped = [], []
    for i, record in enumerate(df.to_dict("records"), start=1):
        parsed_date = pd.to_datetime(record.get(date_col), errors="coerce", dayfirst=True)
        if pd.isna(parsed_date):
            skipped.append({"row": i, "reason": "unparseable date"})
            continue

        description = str(record.get(desc_col) or "").strip() if desc_col else ""
        raw_amount, sign = None, 0
        if amount_col is not None and pd.notna(record.get(amount_col)):
            raw_amount = _to_number(record.get(amount_col))
            if raw_amount is not None:
                sign = 1 if raw_amount > 0 else -1 if raw_amount < 0 else 0
        if raw_amount is None and debit_col is not None and _to_number(record.get(debit_col)):
            raw_amount, sign = _to_number(record.get(debit_col)), -1
        if raw_amount is None and credit_col is not None and _to_number(record.get(credit_col)):
            raw_amount, sign = _to_number(record.get(credit_col)), 1
        if raw_amount is None or raw_amount == 0:
            skipped.append({"row": i, "reason": "missing or zero amount"})
            continue

        tx_type = guess_type(description, sign)
        issues = []
        if amount_col is not None and sign == 1 and tx_type == "income" and raw_amount > 0 and debit_col is None:
            # Unsigned single-amount files can't distinguish direction reliably.
            if not any(w in description.lower() for w in ("salary", "gaji", "allowance", "refund")):
                tx_type = "expense"
                issues.append("no sign on amount — assumed expense, please review")

        rows.append(
            {
                "row": i,
                "date": parsed_date.date().isoformat(),
                "amount": round(abs(raw_amount), 2),
                "type": tx_type,
                "category_guess": guess_category(description),
                "description": description or None,
                "issues": issues,
            }
        )
    return rows, skipped


def _to_number(value) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).replace("RM", "").replace(",", "").strip()
    if not text:
        return None
    negative = text.startswith("(") and text.endswith(")")
    try:
        number = float(text.strip("()"))
    except ValueError:
        return None
    return -number if negative else number


def _store_preview(rows: list[dict], skipped: list[dict], source: str) -> dict:
    import_id = str(uuid.uuid4())
    _previews[import_id] = {"source": source}
    return {"import_id": import_id, "rows": rows, "skipped": skipped}


@router.post("/csv")
async def preview_csv(file: UploadFile):
    content = await _read_upload(file, "csv")
    malformed: list[list[str]] = []

    def collect_bad_line(fields: list[str]):
        # Ragged lines (wrong column count) become skipped-row entries
        # instead of failing the whole import.
        malformed.append(fields)
        return None

    try:
        df = pd.read_csv(
            io.BytesIO(content),
            encoding_errors="replace",
            engine="python",
            on_bad_lines=collect_bad_line,
        )
    except Exception:
        raise unprocessable("CSV_PARSE_FAILED", "Couldn't parse this file — is it a valid CSV export?")
    rows, skipped = _rows_from_dataframe(df)
    skipped = skipped + [
        {"row": 0, "reason": f"wrong number of columns (line starting with '{fields[0]}')"}
        for fields in malformed
        if fields
    ]
    if not rows:
        raise unprocessable("CSV_NO_ROWS", "No usable rows found — check the file has date and amount columns.")
    return _store_preview(rows, skipped, "csv")


# Matches statement lines like "01/03/2026 GRABFOOD KUALA LUMPUR 25.90-"
PDF_LINE = re.compile(
    r"^(?P<date>\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+(?P<desc>.+?)\s+(?P<amount>[\d,]+\.\d{2})\s*(?P<sign>[+-]|CR|DR)?\s*$",
    re.IGNORECASE,
)


def _rows_from_pdf(content: bytes) -> tuple[list[dict], list[dict]]:
    import pdfplumber

    rows, skipped, row_number = [], [], 0
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            for line in (page.extract_text() or "").splitlines():
                match = PDF_LINE.match(line.strip())
                if not match:
                    continue
                row_number += 1
                parsed_date = pd.to_datetime(match["date"], errors="coerce", dayfirst=True)
                if pd.isna(parsed_date):
                    skipped.append({"row": row_number, "reason": "unparseable date"})
                    continue
                amount = _to_number(match["amount"])
                sign_token = (match["sign"] or "").upper()
                sign = 1 if sign_token in ("+", "CR") else -1
                description = match["desc"].strip()
                rows.append(
                    {
                        "row": row_number,
                        "date": parsed_date.date().isoformat(),
                        "amount": round(abs(amount), 2),
                        "type": guess_type(description, sign),
                        "category_guess": guess_category(description),
                        "description": description,
                        "issues": [] if sign_token else ["no sign marker — assumed expense, please review"],
                    }
                )
    return rows, skipped


@router.post("/pdf")
async def preview_pdf(file: UploadFile):
    content = await _read_upload(file, "pdf")
    try:
        rows, skipped = _rows_from_pdf(content)
    except Exception:
        logger.warning("PDF parsing crashed", exc_info=True)
        rows = []
        skipped = []
    if not rows:
        raise unprocessable(
            "PDF_PARSE_FAILED",
            "Couldn't read this statement — try CSV export from your bank instead.",
        )
    return _store_preview(rows, skipped, "pdf")


@router.post("/confirm")
def confirm_import(body: ImportConfirmRequest):
    preview = _previews.pop(body.import_id, None)
    if preview is None:
        raise not_found("IMPORT_NOT_FOUND", "This import session expired — upload the file again.")
    if not body.rows:
        raise unprocessable("IMPORT_EMPTY", "No rows selected to import.")

    payloads = [
        {
            "date": row.date.isoformat(),
            "amount": row.amount,
            "type": row.type,
            "category": row.category_guess,
            "description": row.description,
            "source": preview["source"],
        }
        for row in body.rows
    ]
    inserted = repo.insert_transactions(payloads)

    if repo.get_app_state().get("ledger_mode", False):
        total_delta = sum(ledger.signed_amount(p["type"], p["amount"]) for p in payloads)
        if total_delta != 0:
            repo.adjust_balance(total_delta)

    return {"inserted": inserted}
