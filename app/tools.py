from typing import Literal
from langchain_core.tools import tool
from app.fees import get_fee_amount

COVERAGE_GATE_REPLY = (
    "I don't have that fee on record — let me connect you with a counsellor."
)


@tool
def get_fee(course: str, batch: Literal["1-year", "2-year"]):
    """Look up the exact fee in INR for a course and batch duration. `batch` must be
    exactly "1-year" or "2-year" — map any phrasing the user gives (e.g. "2 saal",
    "2 years", "do saal", "ek saal") to one of these two values. Call this for any
    fee, cost, price, or charges question. Never state a fee amount yourself."""
    print("GET_FEE_ARG-->", course, batch)
    fee = get_fee_amount(course, batch)
    return fee if fee is not None else "NOT_FOUND"
