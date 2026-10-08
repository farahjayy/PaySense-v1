from app.services.categorize import guess_category, guess_type


def test_allowance_from_parents_is_not_rent():
    # Regression: substring matching used to find "rent" inside "parents".
    assert guess_category("Monthly Allowance from Parents") == "Allowance"


def test_prefix_boundary_still_matches_derived_words():
    assert guess_category("Room rental payment") == "Rent"
    assert guess_category("Printing service") == "Education"


def test_common_malaysian_merchants():
    assert guess_category("GrabFood Nasi Lemak") == "Food"
    assert guess_category("TNG eWallet Reload Toll") == "Transport"
    assert guess_category("Shopee - Phone Case") == "Shopping"
    assert guess_category("Unifi Mobile Bill") == "Bills"
    assert guess_category("Something Unrecognisable") == "Other"


def test_guess_type_sign_wins_over_keywords():
    assert guess_type("Salary credited", -1) == "expense"
    assert guess_type("Random purchase", 1) == "income"
    assert guess_type("Monthly salary", 0) == "income"
    assert guess_type("Mamak dinner", 0) == "expense"
