from langchain_core.tools import tool
from app.fees import get_fee_amount

COVERAGE_GATE_REPLY = (
    "I don't have that fee on record — let me connect you with a counsellor."
)


@tool
def get_fee(course: str, batch: str):
    """Look up the exact fee in INR for a course and batch duration. Call this for any fee, cost, price, or charges question. Never state a fee amount yourself."""
    fee = get_fee_amount(course, batch)
    return fee if fee is not None else "NOT_FOUND"
