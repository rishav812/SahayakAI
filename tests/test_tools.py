from app.tools import get_fee


def test_known_fee_jee_2year():
    assert get_fee.invoke({"course": "JEE", "batch": "2-year"}) == 90000


def test_known_fee_neet_1year():
    assert get_fee.invoke({"course": "NEET", "batch": "1-year"}) == 75000


def test_unknown_course_returns_not_found():
    assert get_fee.invoke({"course": "UPSC", "batch": "1-year"}) == "NOT_FOUND"
