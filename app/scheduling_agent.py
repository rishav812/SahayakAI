from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from app.config import llm
from app.booking_tool import book_demo, SLOT_TAKEN
from app.demo_slots import get_free_slots


@tool
def list_free_slots() -> str:
    """List currently available (free) demo class slots, for suggesting
    alternatives when a requested slot is unavailable."""
    slots = get_free_slots()
    if not slots:
        return "No free slots are currently available."
    return "\n".join(f"{s['slot_date']} {s['slot_time']}" for s in slots)


scheduling_agent = create_react_agent(
    llm,
    tools=[book_demo, list_free_slots],
    prompt=(
        "You are a scheduling assistant for a coaching institute's demo classes. "
        "When a user wants to book a demo, confirm the exact date and time back "
        "to them, then call book_demo with that slot_date ('YYYY-MM-DD'), "
        "slot_time (exact string, e.g. '3:00 PM'), and their phone number. "
        f"If book_demo returns '{SLOT_TAKEN}', that slot is unavailable — do NOT "
        "say the booking succeeded or apologize vaguely. Tell the user plainly "
        "that slot is no longer available, then call list_free_slots and suggest "
        "a few of those alternatives for them to choose from. "
        "If book_demo returns a message starting with 'BOOKED', confirm the "
        "booking clearly, restating the exact date and time."
    ),
)
