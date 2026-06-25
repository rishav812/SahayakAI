from langchain_core.tools import tool

FEE_TABLE = {
    ("jee", "2-year"): 90000,
    ("jee", "1-year"): 55000,
    ("neet", "2-year"): 85000,
    ("neet", "1-year"): 75000,
    ("foundation", "1-year"): 40000,
}

COVERAGE_GATE_REPLY = (
    "I don't have that fee on record — let me connect you with a counsellor."
)


@tool
def get_fee(course: str, batch: str):
    """Look up the exact fee in INR for a course and batch duration. Call this for any fee, cost, price, or charges question. Never state a fee amount yourself."""
    return FEE_TABLE.get((course.strip().lower(), batch.strip().lower()), "NOT_FOUND")
