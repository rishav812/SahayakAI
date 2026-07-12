from datetime import date, timedelta
from sqlalchemy import (
    MetaData, Table, Column, Integer, Date, Text, TIMESTAMP, UniqueConstraint, func
)
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.leads import engine

metadata = MetaData()

demo_slots_table = Table(
    "demo_slots",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("slot_date", Date, nullable=False),
    Column("slot_time", Text, nullable=False),
    Column("status", Text, nullable=False, server_default="free"),
    Column("booked_by", Text),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("slot_date", "slot_time", name="uq_demo_slots_date_time"),
)


def setup_demo_slots_table():
    metadata.create_all(engine, tables=[demo_slots_table])


def seed_demo_slots():
    slot_times = ["10:00 AM", "1:00 PM", "4:00 PM"]
    days_ahead = 4

    rows = [
        {"slot_date": date.today() + timedelta(days=d), "slot_time": t}
        for d in range(1, days_ahead + 1)
        for t in slot_times
    ]

    stmt = pg_insert(demo_slots_table).values(rows)
    stmt = stmt.on_conflict_do_nothing(index_elements=["slot_date", "slot_time"])

    with engine.begin() as conn:
        conn.execute(stmt)


def get_free_slots():
    with engine.connect() as conn:
        rows = conn.execute(
            demo_slots_table.select()
            .where(demo_slots_table.c.status == "free")
            .order_by(demo_slots_table.c.slot_date, demo_slots_table.c.slot_time)
        ).mappings().all()
        return [dict(row) for row in rows]
    

# One-time setup: creates the demo_slots table if it doesn't exist yet. Safe
# to call on every startup — it only does work the first time.
setup_demo_slots_table()
