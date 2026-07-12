from datetime import date
from sqlalchemy import func
from langchain_core.tools import tool
from app.demo_slots import demo_slots_table
from app.leads import engine

SLOT_TAKEN = "SLOT_TAKEN"


@tool
def book_demo(slot_date: str, slot_time: str, phone: str) -> str:
    """Book a demo class slot for a phone number, only if that slot is
    currently free. slot_date must be 'YYYY-MM-DD'. slot_time must exactly
    match a seeded slot time, e.g. '3:00 PM'. Returns 'SLOT_TAKEN' if the
    slot is already booked or doesn't exist — never overwrites an existing
    booking."""
    parsed_date = date.fromisoformat(slot_date)

    stmt = (
        demo_slots_table.update()
        .where(
            demo_slots_table.c.slot_date == parsed_date,
            demo_slots_table.c.slot_time == slot_time,
            demo_slots_table.c.status == "free",
        )
        .values(status="booked", booked_by=phone, updated_at=func.now())
    )

    with engine.begin() as conn:
        result = conn.execute(stmt)
        if result.rowcount == 1:
            return f"BOOKED: {slot_date} {slot_time}"
        return SLOT_TAKEN
