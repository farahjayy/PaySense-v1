"""API round-trips against the in-memory fake repo (TESTING.md §2)."""
from datetime import date
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "scripts" / "fixtures"


# --- Transactions ---

def test_transaction_crud_round_trip(client):
    created = client.post(
        "/api/transactions",
        json={"date": "2026-07-10", "amount": 25.5, "type": "expense", "category": "Food",
              "description": "Mamak"},
    )
    assert created.status_code == 201
    tx_id = created.json()["id"]

    listed = client.get("/api/transactions", params={"month": "2026-07", "search": "mamak"})
    assert listed.status_code == 200
    assert any(item["id"] == tx_id for item in listed.json()["items"])

    updated = client.put(f"/api/transactions/{tx_id}", json={"amount": 30.0})
    assert updated.status_code == 200
    assert updated.json()["amount"] == 30.0

    deleted = client.delete(f"/api/transactions/{tx_id}")
    assert deleted.status_code == 204

    missing = client.delete(f"/api/transactions/{tx_id}")
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "TRANSACTION_NOT_FOUND"


def test_transaction_validation_rejects_bad_amount(client):
    response = client.post(
        "/api/transactions",
        json={"date": "2026-07-10", "amount": -5, "type": "expense", "category": "Food"},
    )
    assert response.status_code == 422


def test_transaction_filters(client, store):
    income = client.get("/api/transactions", params={"type": "income"}).json()
    assert all(item["type"] == "income" for item in income["items"])
    assert income["total"] == 6  # seeded 6 months × 1 income row


# --- Ledger mode (balance auto-update) ---

def test_ledger_mode_off_by_default_create_does_not_move_balance(client, store):
    assert store.app_state["ledger_mode"] is False
    client.post(
        "/api/transactions",
        json={"date": "2026-07-10", "amount": 500, "type": "income", "category": "Allowance"},
    )
    assert store.app_state["current_balance"] == 1850.00


def test_ledger_mode_on_income_adds_expense_and_savings_subtract(client, store):
    store.app_state["ledger_mode"] = True

    client.post(
        "/api/transactions",
        json={"date": "2026-07-10", "amount": 500, "type": "income", "category": "Allowance"},
    )
    assert store.app_state["current_balance"] == 2350.00

    client.post(
        "/api/transactions",
        json={"date": "2026-07-11", "amount": 100, "type": "expense", "category": "Food"},
    )
    assert store.app_state["current_balance"] == 2250.00

    client.post(
        "/api/transactions",
        json={"date": "2026-07-12", "amount": 1000, "type": "savings", "category": "Saving"},
    )
    assert store.app_state["current_balance"] == 1250.00


def test_ledger_mode_on_edit_adjusts_the_difference(client, store):
    store.app_state["ledger_mode"] = True
    created = client.post(
        "/api/transactions",
        json={"date": "2026-07-10", "amount": 100, "type": "expense", "category": "Food"},
    ).json()
    assert store.app_state["current_balance"] == 1750.00  # 1850 - 100

    client.put(f"/api/transactions/{created['id']}", json={"amount": 150})
    assert store.app_state["current_balance"] == 1700.00  # another -50


def test_ledger_mode_on_delete_reverses_the_effect(client, store):
    store.app_state["ledger_mode"] = True
    created = client.post(
        "/api/transactions",
        json={"date": "2026-07-10", "amount": 1000, "type": "savings", "category": "Saving"},
    ).json()
    assert store.app_state["current_balance"] == 850.00  # 1850 - 1000

    client.delete(f"/api/transactions/{created['id']}")
    assert store.app_state["current_balance"] == 1850.00  # reversed back


def test_ledger_mode_off_edit_and_delete_leave_balance_untouched(client, store):
    assert store.app_state["ledger_mode"] is False
    created = client.post(
        "/api/transactions",
        json={"date": "2026-07-10", "amount": 1000, "type": "savings", "category": "Saving"},
    ).json()
    client.put(f"/api/transactions/{created['id']}", json={"amount": 2000})
    client.delete(f"/api/transactions/{created['id']}")
    assert store.app_state["current_balance"] == 1850.00


def test_savings_type_excluded_from_month_summary(client, store):
    # A month far outside the fixture's rolling 6-month seed window, so the
    # only rows present are the ones this test adds.
    month = "2031-03"
    client.post(
        "/api/transactions",
        json={"date": f"{month}-10", "amount": 1000, "type": "savings", "category": "Saving"},
    )
    client.post(
        "/api/transactions",
        json={"date": f"{month}-11", "amount": 50, "type": "expense", "category": "Food"},
    )
    summary = client.get("/api/transactions/summary", params={"month": month}).json()
    assert summary["expenses"] == 50.0
    assert all(row["category"] != "Saving" for row in summary["by_category"])


# --- BNPL plans ---

def test_create_plan_generates_installments(client):
    response = client.post(
        "/api/bnpl/plans",
        json={
            "item_name": "Sneakers",
            "provider": "Atome",
            "total_price": 429.0,
            "interest_rate": 0,
            "num_installments": 3,
            "first_payment_date": date.today().isoformat(),
        },
    )
    assert response.status_code == 201
    plan = response.json()
    assert len(plan["installments"]) == 3
    assert round(sum(i["amount"] for i in plan["installments"]), 2) == 429.0
    assert plan["status"] == "active"


def test_pay_installment_creates_transaction_and_recomputes(client, store):
    plan = client.post(
        "/api/bnpl/plans",
        json={
            "item_name": "Earbuds",
            "provider": "SPayLater",
            "total_price": 300.0,
            "interest_rate": 0,
            "num_installments": 2,
            "first_payment_date": date.today().isoformat(),
        },
    ).json()

    tx_before = len(store.transactions)
    paid = client.post(f"/api/bnpl/plans/{plan['id']}/installments/1/pay", json={})
    assert paid.status_code == 200
    assert paid.json()["paid_count"] == 1
    assert len(store.transactions) == tx_before + 1
    assert store.transactions[-1]["is_bnpl"] is True

    again = client.post(f"/api/bnpl/plans/{plan['id']}/installments/1/pay", json={})
    assert again.status_code == 400
    assert again.json()["detail"]["code"] == "ALREADY_PAID"


# --- Risk pipeline ---

def test_risk_check_then_confirm_then_conflict(client, store):
    check = client.post(
        "/api/risk/check",
        json={
            "item_name": "iPhone 16e",
            "total_price": 2999.0,
            "provider": "SPayLater",
            "num_installments": 12,
            "first_payment_date": "2026-08-01",
            "interest_rate": 0,
        },
    )
    assert check.status_code == 200
    body = check.json()
    for key in ("check_id", "risk_probability", "score", "label", "top_factors",
                "recommendation", "curves", "proposed_schedule"):
        assert key in body, f"missing key {key}"
    assert body["label"] in ("safe", "caution", "at_risk")
    assert 0 <= body["score"] <= 100
    assert len(body["proposed_schedule"]) == 12
    assert len(body["curves"]["with_purchase"]) == len(body["curves"]["without_purchase"])

    confirmed = client.post("/api/risk/confirm", json={"check_id": body["check_id"]})
    assert confirmed.status_code == 201
    plan = confirmed.json()
    assert plan["risk_score_at_creation"] == body["score"]
    assert len(plan["installments"]) == 12

    second = client.post("/api/risk/confirm", json={"check_id": body["check_id"]})
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "ALREADY_CONFIRMED"


def test_risk_confirm_unknown_check(client):
    response = client.post("/api/risk/confirm", json={"check_id": "no-such-check"})
    assert response.status_code == 404


def test_forecast_endpoint_shape(client):
    response = client.get("/api/forecast")
    assert response.status_code == 200
    body = response.json()
    assert body["method"] in ("arima", "fallback_ma")
    assert len(body["monthly"]) == 3
    assert body["balance_curve"][0]["balance"] == 1850.0


def test_dashboard_aggregate(client):
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert body["current_balance"] == 1850.0
    assert body["health"]["label"] in ("safe", "caution", "at_risk")
    assert len(body["chart"]) == 6
    assert sum(1 for entry in body["chart"] if entry["is_forecast"]) == 3


# --- Imports ---

def test_csv_import_preview_and_confirm(client, store):
    with open(FIXTURES / "sample_statement.csv", "rb") as f:
        preview = client.post(
            "/api/import/csv", files={"file": ("sample_statement.csv", f, "text/csv")}
        )
    assert preview.status_code == 200
    body = preview.json()
    assert len(body["rows"]) == 18
    reasons = [skip["reason"] for skip in body["skipped"]]
    assert "unparseable date" in reasons
    assert any("wrong number of columns" in reason for reason in reasons)

    tx_before = len(store.transactions)
    confirmed = client.post(
        "/api/import/confirm", json={"import_id": body["import_id"], "rows": body["rows"]}
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["inserted"] == 18
    assert len(store.transactions) == tx_before + 18
    assert store.transactions[-1]["source"] == "csv"


def test_csv_import_malformed_file(client):
    files = {"file": ("junk.csv", b"this is not,a real\x00statement", "text/csv")}
    response = client.post("/api/import/csv", files=files)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] in ("CSV_MISSING_COLUMNS", "CSV_PARSE_FAILED", "CSV_NO_ROWS")


def test_pdf_import_rejects_non_pdf(client):
    files = {"file": ("statement.pdf", b"not a pdf at all", "application/pdf")}
    response = client.post("/api/import/pdf", files=files)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "WRONG_FILE_TYPE"


def test_import_confirm_unknown_id(client):
    response = client.post("/api/import/confirm", json={"import_id": "expired", "rows": []})
    assert response.status_code == 404


# --- provider-aware schedules ---

def _plan_body(provider, **overrides):
    body = {
        "item_name": "Earbuds", "provider": provider, "total_price": 300.0,
        "interest_rate": 0, "num_installments": 3, "purchase_date": "2026-09-25",
    }
    body.update(overrides)
    return body


def test_spaylater_plan_starts_next_month_and_nothing_is_paid(client):
    plan = client.post("/api/bnpl/plans", json=_plan_body("SPayLater")).json()
    assert [i["due_date"] for i in plan["installments"]] == ["2026-10-25", "2026-11-25", "2026-12-25"]
    assert plan["first_payment_date"] == "2026-10-25"
    assert plan["paid_count"] == 0


def test_tiktok_paylater_follows_the_same_rule(client):
    plan = client.post("/api/bnpl/plans", json=_plan_body("TikTok PayLater")).json()
    assert plan["installments"][0]["due_date"] == "2026-10-25"


def test_atome_plan_marks_the_checkout_payment_paid(client):
    plan = client.post("/api/bnpl/plans", json=_plan_body("Atome")).json()
    first = plan["installments"][0]
    assert first["due_date"] == "2026-09-25"
    assert first["is_paid"] is True and first["paid_date"] == "2026-09-25"
    assert plan["paid_count"] == 1
    assert not any(i["is_paid"] for i in plan["installments"][1:])


def test_explicit_first_payment_date_is_still_honoured(client):
    plan = client.post("/api/bnpl/plans", json=_plan_body("SPayLater", first_payment_date="2026-10-10")).json()
    assert plan["installments"][0]["due_date"] == "2026-10-10"


def test_risk_check_pay_later_schedule_and_full_outstanding(client, store):
    body = client.post("/api/risk/check", json={
        "item_name": "Phone", "total_price": 300.0, "provider": "SPayLater", "num_installments": 3,
        "purchase_date": date.today().isoformat(), "interest_rate": 0,
    }).json()
    assert body["proposed_schedule"][0]["paid_at_checkout"] is False
    assert store.risk_checks[-1]["feature_vector"]["bnpl_outstanding"] == 300.0


def test_risk_check_atome_counts_only_the_unpaid_part_as_outstanding(client, store):
    body = client.post("/api/risk/check", json={
        "item_name": "Phone", "total_price": 300.0, "provider": "Atome", "num_installments": 3,
        "purchase_date": date.today().isoformat(), "interest_rate": 0,
    }).json()
    assert body["proposed_schedule"][0]["paid_at_checkout"] is True
    assert body["proposed_schedule"][0]["due_date"] == date.today().isoformat()
    assert store.risk_checks[-1]["feature_vector"]["bnpl_outstanding"] == 200.0


def test_confirming_an_atome_check_saves_the_checkout_payment_as_paid(client):
    check = client.post("/api/risk/check", json={
        "item_name": "Phone", "total_price": 300.0, "provider": "Atome", "num_installments": 3,
        "purchase_date": date.today().isoformat(), "interest_rate": 0,
    }).json()
    plan = client.post("/api/risk/confirm", json={"check_id": check["check_id"]}).json()
    assert plan["installments"][0]["is_paid"] is True
    assert plan["paid_count"] == 1


def test_confirming_a_legacy_check_without_purchase_date_still_works(client, store):
    store.risk_checks.append({
        "id": "legacy-1", "risk_score": 60,
        "input": {"item_name": "Old", "provider": "SPayLater", "total_price": 300.0,
                  "interest_rate": 0, "num_installments": 3, "first_payment_date": "2026-11-01"},
    })
    plan = client.post("/api/risk/confirm", json={"check_id": "legacy-1"}).json()
    assert plan["installments"][0]["due_date"] == "2026-11-01"


def test_confirming_a_legacy_whole_plan_fee_check_converts_it_to_a_monthly_rate(client, store):
    store.risk_checks.append({
        "id": "legacy-fee", "risk_score": 60,
        "input": {"item_name": "Old", "provider": "TikTok PayLater", "total_price": 300.0,
                  "interest_rate": 9.0, "num_installments": 3, "first_payment_date": "2026-11-01"},
    })
    plan = client.post("/api/risk/confirm", json={"check_id": "legacy-fee"}).json()
    assert plan["interest_rate"] == 3.0  # 9% whole-plan over 3 instalments = 3% per month
    assert round(sum(i["amount"] for i in plan["installments"]), 2) == 327.0  # 300 x 1.09, unchanged


def test_confirming_a_new_check_keeps_the_monthly_rate(client):
    check = client.post("/api/risk/check", json={
        "item_name": "Phone", "total_price": 300.0, "provider": "TikTok PayLater", "num_installments": 3,
        "purchase_date": date.today().isoformat(), "interest_rate": 1.5,
    }).json()
    plan = client.post("/api/risk/confirm", json={"check_id": check["check_id"]}).json()
    assert plan["interest_rate"] == 1.5
    assert round(sum(i["amount"] for i in plan["installments"]), 2) == 313.5  # 300 x (1 + 0.015 x 3)


def test_risk_check_records_that_the_fee_is_monthly(client, store):
    client.post("/api/risk/check", json={
        "item_name": "Phone", "total_price": 300.0, "provider": "SPayLater", "num_installments": 3,
        "purchase_date": date.today().isoformat(), "interest_rate": 0,
    })
    assert store.risk_checks[-1]["input"]["fee_basis"] == "monthly"


def test_plan_total_payable_matches_the_instalment_schedule_everywhere(client):
    plan = client.post("/api/bnpl/plans", json=_plan_body(
        "SPayLater", total_price=147.62, interest_rate=1.5, num_installments=6)).json()
    assert plan["total_payable"] == 160.91
    assert round(sum(i["amount"] for i in plan["installments"]), 2) == plan["total_payable"]
    assert client.get(f"/api/bnpl/plans/{plan['id']}").json()["total_payable"] == 160.91
    listed = next(p for p in client.get("/api/bnpl/plans").json() if p["id"] == plan["id"])
    assert listed["total_payable"] == 160.91


# --- deleting a plan and the transactions its paid instalments logged ---

def _plan_with_paid(client, item="Earbuds", paid=(1, 2)):
    plan = client.post("/api/bnpl/plans", json=_plan_body("SPayLater", item_name=item)).json()
    for seq in paid:
        client.post(f"/api/bnpl/plans/{plan['id']}/installments/{seq}/pay", json={})
    return plan


def _bnpl_tx(store):
    return [t for t in store.transactions if t.get("is_bnpl")]


def test_plan_transactions_preview_lists_the_transactions_linked_to_the_plan(client, store):
    plan = _plan_with_paid(client)  # 300 over 3 = 100 each, 2 paid
    client.post("/api/transactions", json={"date": "2026-09-25", "amount": 100, "type": "expense", "category": "Food",
                                           "description": "SPayLater instalment 3/3 — Earbuds"})  # hand-typed look-alike
    preview = client.get(f"/api/bnpl/plans/{plan['id']}/transactions").json()
    assert preview["count"] == 2
    assert preview["total"] == 200.0
    assert {i["description"] for i in preview["items"]} == {
        "SPayLater instalment 1/3 — Earbuds", "SPayLater instalment 2/3 — Earbuds"}


def test_plan_without_paid_instalments_has_no_transactions(client):
    plan = client.post("/api/bnpl/plans", json=_plan_body("SPayLater")).json()
    assert client.get(f"/api/bnpl/plans/{plan['id']}/transactions").json() == {"count": 0, "total": 0.0, "items": []}


def test_plan_transactions_of_a_missing_plan_is_404(client):
    assert client.get("/api/bnpl/plans/nope/transactions").status_code == 404


def test_deleting_a_plan_keeps_its_transactions_by_default(client, store):
    plan = _plan_with_paid(client)
    response = client.delete(f"/api/bnpl/plans/{plan['id']}")
    assert response.status_code == 200
    assert response.json() == {"deleted_transactions": 0, "failed_transactions": 0}
    assert len(_bnpl_tx(store)) == 2
    assert client.get(f"/api/bnpl/plans/{plan['id']}").status_code == 404


def test_deleting_a_plan_can_also_delete_exactly_its_transactions(client, store):
    plan = _plan_with_paid(client)
    unrelated = client.post("/api/transactions", json={"date": "2026-09-25", "amount": 100, "type": "expense",
                                                       "category": "Food", "description": "Lunch"}).json()
    response = client.delete(f"/api/bnpl/plans/{plan['id']}", params={"delete_transactions": "true"})
    assert response.json() == {"deleted_transactions": 2, "failed_transactions": 0}
    assert _bnpl_tx(store) == []
    assert any(t["id"] == unrelated["id"] for t in store.transactions)  # nothing else was touched


def test_a_payment_transaction_the_user_edited_is_still_the_plans_and_goes_with_it(client, store):
    plan = _plan_with_paid(client)
    edited = _bnpl_tx(store)[0]
    client.put(f"/api/transactions/{edited['id']}", json={"amount": 99.0, "description": "my own words"})
    assert client.get(f"/api/bnpl/plans/{plan['id']}/transactions").json()["count"] == 2  # linked by ID, not text
    client.delete(f"/api/bnpl/plans/{plan['id']}", params={"delete_transactions": "true"})
    assert _bnpl_tx(store) == []


def test_two_identical_plans_each_lose_only_their_own_transactions(client, store):
    first = _plan_with_paid(client, paid=(1,))
    second = _plan_with_paid(client, paid=(1,))  # same item, provider, amount, date: identical text
    second_tx = next(t for t in _bnpl_tx(store) if t["bnpl_plan_id"] == second["id"])
    client.delete(f"/api/bnpl/plans/{first['id']}", params={"delete_transactions": "true"})
    assert [t["id"] for t in _bnpl_tx(store)] == [second_tx["id"]]


def test_deleting_a_missing_plan_is_404(client):
    assert client.delete("/api/bnpl/plans/nope").status_code == 404


def test_ledger_on_deleting_the_plan_and_transactions_restores_the_balance(client, store):
    store.app_state["ledger_mode"] = True
    start = store.app_state["current_balance"]
    plan = _plan_with_paid(client, paid=(1, 2))
    assert store.app_state["current_balance"] == start - 200.0  # paying moves the balance in ledger mode
    client.delete(f"/api/bnpl/plans/{plan['id']}", params={"delete_transactions": "true"})
    assert store.app_state["current_balance"] == start


def test_ledger_on_keeping_the_transactions_leaves_the_balance_alone(client, store):
    store.app_state["ledger_mode"] = True
    plan = _plan_with_paid(client, paid=(1, 2))
    after_paying = store.app_state["current_balance"]
    client.delete(f"/api/bnpl/plans/{plan['id']}")
    assert store.app_state["current_balance"] == after_paying


def test_paying_an_instalment_subtracts_it_from_the_balance_even_with_ledger_mode_off(client, store):
    assert store.app_state["ledger_mode"] is False
    start = store.app_state["current_balance"]
    _plan_with_paid(client, paid=(1,))  # 100.00 instalment
    assert store.app_state["current_balance"] == start - 100.0


def test_paying_with_ledger_mode_on_subtracts_exactly_once(client, store):
    store.app_state["ledger_mode"] = True
    start = store.app_state["current_balance"]
    _plan_with_paid(client, paid=(1,))
    assert store.app_state["current_balance"] == start - 100.0  # not -200 (transaction + payment)


def test_paying_without_logging_a_transaction_still_subtracts(client, store):
    start = store.app_state["current_balance"]
    plan = client.post("/api/bnpl/plans", json=_plan_body("SPayLater")).json()
    client.post(f"/api/bnpl/plans/{plan['id']}/installments/1/pay", json={"create_transaction": False})
    assert store.app_state["current_balance"] == start - 100.0
    assert _bnpl_tx(store) == []


def test_ledger_off_deleting_the_plan_and_transactions_gives_the_money_back(client, store):
    start = store.app_state["current_balance"]
    plan = _plan_with_paid(client, paid=(1, 2))
    assert store.app_state["current_balance"] == start - 200.0
    client.delete(f"/api/bnpl/plans/{plan['id']}", params={"delete_transactions": "true"})
    assert store.app_state["current_balance"] == start


def test_ledger_off_keeping_the_transactions_leaves_the_payments_subtracted(client, store):
    start = store.app_state["current_balance"]
    plan = _plan_with_paid(client, paid=(1, 2))
    client.delete(f"/api/bnpl/plans/{plan['id']}")
    assert store.app_state["current_balance"] == start - 200.0


# --- Atome: only the checkout payment leaves the balance when the plan is created ---

def test_atome_plan_subtracts_only_the_checkout_third_from_the_balance(client, store):
    start = store.app_state["current_balance"]
    plan = client.post("/api/bnpl/plans", json=_plan_body("Atome", total_price=30.0)).json()  # 10.00 x 3
    assert store.app_state["current_balance"] == start - 10.0  # RM10 charged at checkout, RM20 still to pay
    assert plan["paid_count"] == 1
    client.post(f"/api/bnpl/plans/{plan['id']}/installments/2/pay", json={})
    assert store.app_state["current_balance"] == start - 20.0  # each later instalment leaves when marked paid


def test_atome_checkout_payment_is_subtracted_in_ledger_mode_too(client, store):
    store.app_state["ledger_mode"] = True
    start = store.app_state["current_balance"]
    client.post("/api/bnpl/plans", json=_plan_body("Atome", total_price=30.0))
    assert store.app_state["current_balance"] == start - 10.0


def test_pay_later_plan_creation_does_not_touch_the_balance(client, store):
    start = store.app_state["current_balance"]
    client.post("/api/bnpl/plans", json=_plan_body("SPayLater", total_price=30.0))
    assert store.app_state["current_balance"] == start


def test_atome_plan_whose_first_payment_is_moved_later_charges_nothing_yet(client, store):
    start = store.app_state["current_balance"]
    client.post("/api/bnpl/plans", json=_plan_body("Atome", total_price=30.0, first_payment_date="2026-10-25"))
    assert store.app_state["current_balance"] == start


def test_risk_check_alone_never_moves_the_balance_but_confirming_an_atome_check_does(client, store):
    start = store.app_state["current_balance"]
    check = client.post("/api/risk/check", json={
        "item_name": "Phone", "total_price": 30.0, "provider": "Atome", "num_installments": 3,
        "purchase_date": date.today().isoformat(), "interest_rate": 0,
    }).json()
    assert store.app_state["current_balance"] == start
    client.post("/api/risk/confirm", json={"check_id": check["check_id"]})
    assert store.app_state["current_balance"] == start - 10.0


def test_paying_an_instalment_links_the_logged_transaction_to_the_plan(client, store):
    plan = _plan_with_paid(client, paid=(1,))
    assert _bnpl_tx(store)[0]["bnpl_plan_id"] == plan["id"]


def test_a_manually_typed_bnpl_transaction_has_no_plan_link(client, store):
    created = client.post("/api/transactions", json={"date": "2026-09-25", "amount": 50, "type": "expense",
                                                     "category": "Bills", "is_bnpl": True,
                                                     "description": "SPayLater instalment 1/3 — Earbuds"}).json()
    stored = next(t for t in store.transactions if t["id"] == created["id"])
    assert stored.get("bnpl_plan_id") is None


def test_legacy_unlinked_payments_are_never_offered_or_deleted(client, store):
    """Rows logged before the link existed (bnpl_plan_id null) stay out of plan deletion until
    the backfill script links them: a text look-alike is not proof."""
    plan = client.post("/api/bnpl/plans", json=_plan_body("SPayLater")).json()
    client.post(f"/api/bnpl/plans/{plan['id']}/installments/1/pay", json={"create_transaction": False})
    store.transactions.append({**store.transactions[0], "id": "legacy-1", "amount": 100.0, "type": "expense",
                               "is_bnpl": True, "description": "SPayLater instalment 1/3 — Earbuds",
                               "date": date.today().isoformat(), "bnpl_plan_id": None})
    assert client.get(f"/api/bnpl/plans/{plan['id']}/transactions").json()["count"] == 0
    client.delete(f"/api/bnpl/plans/{plan['id']}", params={"delete_transactions": "true"})
    assert any(t["id"] == "legacy-1" for t in store.transactions)


# --- editing a plan: only the name, any time ---

def _patch(client, plan_id, **body):
    return client.patch(f"/api/bnpl/plans/{plan_id}", json=body)


def test_renaming_a_plan_changes_only_the_name(client, store):
    plan = client.post("/api/bnpl/plans", json=_plan_body("SPayLater")).json()
    balance, tx_count = store.app_state["current_balance"], len(store.transactions)
    response = _patch(client, plan["id"], item_name="  Wireless earbuds  ")
    assert response.status_code == 200
    renamed = response.json()
    assert renamed["item_name"] == "Wireless earbuds"
    assert [(i["due_date"], i["amount"]) for i in renamed["installments"]] == \
        [(i["due_date"], i["amount"]) for i in plan["installments"]]
    assert (renamed["total_price"], renamed["interest_rate"], renamed["provider"]) == \
        (plan["total_price"], plan["interest_rate"], plan["provider"])
    assert store.app_state["current_balance"] == balance and len(store.transactions) == tx_count


def test_renaming_is_allowed_even_when_instalments_are_paid(client):
    plan = _plan_with_paid(client, paid=(1, 2))
    assert _patch(client, plan["id"], item_name="Renamed").status_code == 200


def test_renaming_updates_the_descriptions_of_the_plans_linked_transactions(client, store):
    plan = _plan_with_paid(client, paid=(1, 2))
    unrelated = client.post("/api/transactions", json={"date": "2026-09-25", "amount": 100, "type": "expense",
                                                       "category": "Food", "description": "Earbuds snack"}).json()
    _patch(client, plan["id"], item_name="Wireless earbuds")
    preview = client.get(f"/api/bnpl/plans/{plan['id']}/transactions").json()
    assert preview["count"] == 2
    assert {i["description"] for i in preview["items"]} == {
        "SPayLater instalment 1/3 — Wireless earbuds", "SPayLater instalment 2/3 — Wireless earbuds"}
    assert next(t for t in store.transactions if t["id"] == unrelated["id"])["description"] == "Earbuds snack"


def test_renaming_leaves_a_transaction_description_the_user_rewrote_alone_but_it_stays_linked(client, store):
    plan = _plan_with_paid(client, paid=(1, 2))
    rewritten = _bnpl_tx(store)[0]
    client.put(f"/api/transactions/{rewritten['id']}", json={"description": "my own words"})
    _patch(client, plan["id"], item_name="Wireless earbuds")
    assert next(t for t in store.transactions if t["id"] == rewritten["id"])["description"] == "my own words"
    assert client.get(f"/api/bnpl/plans/{plan['id']}/transactions").json()["count"] == 2


def test_deleting_after_a_rename_still_removes_the_plans_transactions(client, store):
    plan = _plan_with_paid(client, paid=(1, 2))
    _patch(client, plan["id"], item_name="Wireless earbuds")
    client.delete(f"/api/bnpl/plans/{plan['id']}", params={"delete_transactions": "true"})
    assert _bnpl_tx(store) == []


def test_a_blank_name_is_rejected(client):
    plan = client.post("/api/bnpl/plans", json=_plan_body("SPayLater")).json()
    assert _patch(client, plan["id"], item_name="").status_code == 422
    assert _patch(client, plan["id"], item_name="   ").status_code == 422


def test_nothing_but_the_name_can_be_edited(client):
    plan = client.post("/api/bnpl/plans", json=_plan_body("SPayLater")).json()
    for field, value in (("provider", "Atome"), ("purchase_date", "2026-10-01"), ("total_price", 999.0),
                         ("interest_rate", 2.0), ("num_installments", 6), ("first_payment_date", "2026-10-10")):
        assert _patch(client, plan["id"], item_name="x", **{field: value}).status_code == 422, field
    assert client.get(f"/api/bnpl/plans/{plan['id']}").json()["item_name"] == "Earbuds"


def test_a_patch_with_no_name_is_rejected(client):
    plan = client.post("/api/bnpl/plans", json=_plan_body("SPayLater")).json()
    assert _patch(client, plan["id"]).status_code == 422


def test_editing_a_missing_plan_is_404(client):
    assert _patch(client, "nope", item_name="x").status_code == 404


# --- dashboard: active plans sorted by due date, with remaining total; bills endpoint ---

def test_dashboard_active_plans_sorted_by_next_due_date_ascending(client):
    client.post("/api/bnpl/plans", json=_plan_body("SPayLater", item_name="Later", first_payment_date="2026-12-01"))
    client.post("/api/bnpl/plans", json=_plan_body("SPayLater", item_name="Sooner", first_payment_date="2026-10-01"))
    plans = client.get("/api/dashboard").json()["active_plans"]
    assert [p["item_name"] for p in plans] == ["Sooner", "Later"]


def test_dashboard_active_plans_include_remaining_total(client):
    plan = _plan_with_paid(client, paid=(1,))  # 300 over 3 = 100 each, 1 paid -> 200 left
    row = next(p for p in client.get("/api/dashboard").json()["active_plans"] if p["id"] == plan["id"])
    assert row["remaining_total"] == 200.0


def test_bills_endpoint_lists_months_current_first(client):
    client.post("/api/bnpl/plans", json=_plan_body("SPayLater", first_payment_date=date.today().isoformat()))
    months = client.get("/api/bnpl/bills").json()["months"]
    assert months[0]["month"] == date.today().strftime("%Y-%m")
    assert months[0]["is_current"] is True
    assert months[0]["total_due"] == 100.0
    assert len(months) == 3  # all 3 instalments, one month apart


def test_dashboard_bnpl_summary_splits_overdue_from_upcoming(client, store):
    # Plan A: 3 instalments, 1 overdue (unpaid, due in the past), 2 upcoming.
    plan_a = client.post("/api/bnpl/plans", json=_plan_body("SPayLater", item_name="A")).json()
    past_due = date.today().isoformat()
    for inst in plan_a["installments"][:1]:
        # Force one instalment into the past directly in the fake store (API has no "backdate").
        for p in store.plans:
            if p["id"] == plan_a["id"]:
                for i in p["installments"]:
                    if i["seq"] == inst["seq"]:
                        i["due_date"] = date(2020, 1, 1)
    summary = client.get("/api/dashboard").json()["bnpl_summary"]
    assert summary["plan_count"] == 1
    assert summary["overdue_total"] == 100.0
    assert summary["upcoming_total"] == 200.0


def test_dashboard_bnpl_summary_excludes_paid_instalments(client):
    _plan_with_paid(client, paid=(1,))  # 300 over 3 = 100 each, 1 paid, 2 unpaid (not overdue)
    summary = client.get("/api/dashboard").json()["bnpl_summary"]
    assert summary["overdue_total"] == 0.0
    assert summary["upcoming_total"] == 200.0


def test_dashboard_bnpl_summary_counts_every_open_plan(client):
    client.post("/api/bnpl/plans", json=_plan_body("SPayLater", item_name="A"))
    client.post("/api/bnpl/plans", json=_plan_body("Atome", item_name="B"))
    assert client.get("/api/dashboard").json()["bnpl_summary"]["plan_count"] == 2


def test_dashboard_bnpl_summary_is_zeroed_with_no_plans(client):
    assert client.get("/api/dashboard").json()["bnpl_summary"] == {
        "plan_count": 0, "overdue_total": 0.0, "upcoming_total": 0.0,
    }


# --- risk report: score on every plan, frozen SHAP snapshot ---

def test_adding_an_existing_plan_runs_a_current_risk_check(client, store):
    plan = client.post("/api/bnpl/plans", json=_plan_body("SPayLater")).json()
    assert plan["risk_score_at_creation"] is not None
    assert 0 <= plan["risk_score_at_creation"] <= 100
    assert plan["risk_check_type"] == "current_state"
    assert plan["risk_check_id"] is not None
    stored_check = next(c for c in store.risk_checks if c["id"] == plan["risk_check_id"])
    assert stored_check["risk_score"] == plan["risk_score_at_creation"]
    assert stored_check["top_factors"] is not None


def test_confirming_a_risk_check_marks_it_before_purchase(client):
    check = client.post("/api/risk/check", json={
        "item_name": "Phone", "total_price": 300.0, "provider": "SPayLater", "num_installments": 3,
        "purchase_date": date.today().isoformat(), "interest_rate": 0,
    }).json()
    plan = client.post("/api/risk/confirm", json={"check_id": check["check_id"]}).json()
    assert plan["risk_check_type"] == "before_purchase"
    assert plan["risk_check_id"] == check["check_id"]
    assert plan["risk_score_at_creation"] == check["score"]


def test_risk_report_returns_the_frozen_check_behind_the_badge(client):
    plan = client.post("/api/bnpl/plans", json=_plan_body("SPayLater")).json()
    report = client.get(f"/api/bnpl/plans/{plan['id']}/risk-report").json()
    assert report["check_id"] == plan["risk_check_id"]
    assert report["check_type"] == "current_state"
    assert report["score"] == plan["risk_score_at_creation"]
    assert 0 <= report["risk_probability"] <= 1
    assert report["label"] in ("safe", "caution", "at_risk")
    assert len(report["top_factors"]) >= 0
    assert isinstance(report["recommendation"], str) and report["recommendation"]


def test_risk_report_never_recomputes_after_the_plan_state_changes(client):
    """The report is a frozen snapshot: it must not change even after later actions
    (e.g. marking an instalment paid) alter what a fresh check would produce."""
    plan = client.post("/api/bnpl/plans", json=_plan_body("SPayLater")).json()
    before = client.get(f"/api/bnpl/plans/{plan['id']}/risk-report").json()
    client.post(f"/api/bnpl/plans/{plan['id']}/installments/1/pay", json={})
    after = client.get(f"/api/bnpl/plans/{plan['id']}/risk-report").json()
    assert after == before


def test_risk_report_404s_when_the_plan_has_none(client, store):
    plan = client.post("/api/bnpl/plans", json=_plan_body("SPayLater")).json()
    for p in store.plans:
        if p["id"] == plan["id"]:
            p["risk_check_id"] = None
    assert client.get(f"/api/bnpl/plans/{plan['id']}/risk-report").status_code == 404


def test_risk_report_404s_for_a_missing_plan(client):
    assert client.get("/api/bnpl/plans/nope/risk-report").status_code == 404


def test_a_current_state_check_cannot_be_confirmed_into_a_plan(client):
    plan = client.post("/api/bnpl/plans", json=_plan_body("SPayLater")).json()
    response = client.post("/api/risk/confirm", json={"check_id": plan["risk_check_id"]})
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "NOT_CONFIRMABLE"


def test_plan_creation_still_succeeds_if_the_risk_check_fails(client, store, monkeypatch):
    from app.services import pipeline

    def boom(*args, **kwargs):
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(pipeline, "run_current_risk_check", boom)
    response = client.post("/api/bnpl/plans", json=_plan_body("SPayLater"))
    assert response.status_code == 201
    assert response.json()["risk_score_at_creation"] is None
    assert response.json()["risk_check_id"] is None


# --- risk report: balance-impact curves, frozen alongside the score ---

def test_before_purchase_check_persists_its_balance_curves(client, store):
    check = client.post("/api/risk/check", json={
        "item_name": "Phone", "total_price": 300.0, "provider": "SPayLater", "num_installments": 3,
        "purchase_date": date.today().isoformat(), "interest_rate": 0,
    }).json()
    stored = next(c for c in store.risk_checks if c["id"] == check["check_id"])
    assert stored["curves"] == check["curves"]
    assert len(stored["curves"]["without_purchase"]) > 0
    assert len(stored["curves"]["with_purchase"]) > 0


def test_current_state_check_curve_shows_the_plans_own_impact(client, store):
    plan = client.post("/api/bnpl/plans", json=_plan_body("SPayLater")).json()
    report = client.get(f"/api/bnpl/plans/{plan['id']}/risk-report").json()
    without = {p["date"]: p["balance"] for p in report["curves"]["without_purchase"]}
    with_ = {p["date"]: p["balance"] for p in report["curves"]["with_purchase"]}
    # This plan's own instalments are excluded from "without" and included in "with", so by
    # the end of the 13-week window the two must differ (an instalment has landed).
    last_date = max(without)
    assert with_[last_date] < without[last_date]


def test_risk_report_curves_are_also_frozen(client):
    plan = client.post("/api/bnpl/plans", json=_plan_body("SPayLater")).json()
    before = client.get(f"/api/bnpl/plans/{plan['id']}/risk-report").json()["curves"]
    client.post(f"/api/bnpl/plans/{plan['id']}/installments/1/pay", json={})
    after = client.get(f"/api/bnpl/plans/{plan['id']}/risk-report").json()["curves"]
    assert after == before


def test_a_report_from_before_this_change_has_no_curves(client, store):
    plan = client.post("/api/bnpl/plans", json=_plan_body("SPayLater")).json()
    for check in store.risk_checks:
        if check["id"] == plan["risk_check_id"]:
            del check["curves"]
    report = client.get(f"/api/bnpl/plans/{plan['id']}/risk-report").json()
    assert report["curves"] is None


# --- risk report: chart annotations need the instalment schedule alongside the curves ---

def test_before_purchase_curves_include_the_full_schedule_for_chart_labels(client, store):
    check = client.post("/api/risk/check", json={
        "item_name": "Phone", "total_price": 300.0, "provider": "SPayLater", "num_installments": 3,
        "purchase_date": date.today().isoformat(), "interest_rate": 0,
    }).json()
    schedule = check["curves"]["schedule"]
    assert [item["seq"] for item in schedule] == [1, 2, 3]
    assert all(item["num_installments"] == 3 for item in schedule)
    assert schedule[0]["amount"] == 100.0
    assert schedule[0]["due_date"] == check["proposed_schedule"][0]["due_date"]


def test_current_state_curves_schedule_is_only_this_plans_unpaid_instalments(client, store):
    """The router only triggers run_current_risk_check at creation (nothing can be paid yet
    at that instant), but the function itself must still filter correctly if ever re-run
    later — call it directly to prove that, rather than relying on router timing."""
    from app.services import pipeline

    client.post("/api/bnpl/plans", json=_plan_body("SPayLater", item_name="Other"))  # 3 unpaid, seq 1-3
    plan = _plan_with_paid(client, item="Earbuds", paid=(1,))  # this plan's own #1 now paid

    check = pipeline.run_current_risk_check(highlight_plan_id=plan["id"])
    schedule = check["curves"]["schedule"]
    assert [item["seq"] for item in schedule] == [2, 3]  # #1 (paid) excluded
    assert all(item["num_installments"] == 3 for item in schedule)


# --- chart schedule must carry paid_at_checkout, so the chart never calls it "nothing charged yet" ---

def test_before_purchase_chart_schedule_flags_the_atome_checkout_instalment(client):
    check = client.post("/api/risk/check", json={
        "item_name": "ramen", "total_price": 30.0, "provider": "Atome", "num_installments": 3,
        "purchase_date": date.today().isoformat(), "interest_rate": 0,
    }).json()
    schedule = check["curves"]["schedule"]
    assert [item["paid_at_checkout"] for item in schedule] == [True, False, False]


def test_before_purchase_chart_schedule_flags_nothing_for_a_pay_later_provider(client):
    check = client.post("/api/risk/check", json={
        "item_name": "Phone", "total_price": 300.0, "provider": "SPayLater", "num_installments": 3,
        "purchase_date": date.today().isoformat(), "interest_rate": 0,
    }).json()
    schedule = check["curves"]["schedule"]
    assert all(item["paid_at_checkout"] is False for item in schedule)


def test_current_state_chart_schedule_never_flags_paid_at_checkout(client):
    """current_state schedules only ever contain still-owed instalments (Atome's checkout
    instalment is already marked paid by the time a plan exists), so this is always False —
    but the field must still be present for the frontend type to be uniform."""
    from app.services import pipeline

    plan = client.post("/api/bnpl/plans", json=_plan_body("Atome", total_price=30.0)).json()
    check = pipeline.run_current_risk_check(highlight_plan_id=plan["id"])
    schedule = check["curves"]["schedule"]
    assert len(schedule) > 0
    assert all(item["paid_at_checkout"] is False for item in schedule)
