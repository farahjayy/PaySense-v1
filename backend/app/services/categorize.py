"""Keyword-rule category guessing for CSV/PDF import previews."""
import re

CATEGORY_KEYWORDS = {
    "Food": ["grab food", "grabfood", "food", "mcd", "mcdonald", "kfc", "mamak", "cafe", "restoran", "restaurant", "nasi", "foodpanda", "starbucks", "tealive", "zus", "bakery", "makan"],
    "Transport": ["tng", "touch n go", "touchngo", "petrol", "petronas", "shell", "grab ride", "grabcar", "rapidkl", "mrt", "lrt", "bus", "toll", "parking", "myrapid"],
    "Rent": ["rent", "sewa", "hostel", "deposit rumah"],
    "Salary": ["salary", "gaji", "payroll", "wage", "stipend"],
    "Allowance": ["allowance", "duit", "parents", "scholarship", "ptptn", "jpa", "mara", "yayasan"],
    "Shopping": ["shopee", "lazada", "zalora", "uniqlo", "mr diy", "mr. diy", "watsons", "guardian", "sephora", "ikea"],
    "Bills": ["bill", "unifi", "maxis", "celcom", "digi", "umobile", "u mobile", "tnb", "electric", "water", "syabas", "indah water", "astro", "netflix", "spotify", "icloud", "yes 5g"],
    "Entertainment": ["cinema", "gsc", "tgv", "movie", "steam", "game", "concert", "karaoke", "bowling"],
    "Education": ["book", "tuition", "course", "udemy", "coursera", "exam", "yuran", "utp", "university", "print", "stationery"],
}

DEFAULT_CATEGORY = "Other"


def _matches(keyword: str, text: str) -> bool:
    # Prefix word-boundary: "rent" matches "rental" but not "parents",
    # "print" still matches "printing".
    return re.search(r"\b" + re.escape(keyword), text) is not None


def guess_category(description: str) -> str:
    text = (description or "").lower()
    if not text:
        return DEFAULT_CATEGORY
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(_matches(keyword, text) for keyword in keywords):
            return category
    return DEFAULT_CATEGORY


def guess_type(description: str, amount_sign: int) -> str:
    """Sign wins when the source provides one; keywords break the tie otherwise."""
    if amount_sign > 0:
        return "income"
    if amount_sign < 0:
        return "expense"
    text = (description or "").lower()
    income_words = CATEGORY_KEYWORDS["Salary"] + CATEGORY_KEYWORDS["Allowance"] + ["refund", "transfer in", "credit"]
    return "income" if any(_matches(w, text) for w in income_words) else "expense"
