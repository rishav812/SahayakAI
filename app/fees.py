from sqlalchemy import MetaData, Table, Column, Text, Integer, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.leads import engine

metadata = MetaData()

course_fees_table = Table(
    "course_fees",
    metadata,
    Column("course", Text, primary_key=True),
    Column("batch", Text, primary_key=True),
    Column("fee", Integer, nullable=False),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=func.now()),
)

# Same values the old static FEE_TABLE held — seeded once so the DB starts
# with today's known fees; from here on, this table is the source of truth.
INITIAL_FEES = [
    {"course": "jee", "batch": "2-year", "fee": 90000},
    {"course": "jee", "batch": "1-year", "fee": 55000},
    {"course": "neet", "batch": "2-year", "fee": 85000},
    {"course": "neet", "batch": "1-year", "fee": 75000},
    {"course": "foundation", "batch": "1-year", "fee": 40000},
]


def setup_course_fees_table():
    metadata.create_all(engine, tables=[course_fees_table])


def seed_course_fees():
    stmt = pg_insert(course_fees_table).values(INITIAL_FEES)
    stmt = stmt.on_conflict_do_nothing(index_elements=["course", "batch"])
    with engine.begin() as conn:
        conn.execute(stmt)


def get_fee_amount(course: str, batch: str):
    with engine.connect() as conn:
        row = conn.execute(
            course_fees_table.select().where(
                course_fees_table.c.course == course.strip().lower(),
                course_fees_table.c.batch == batch.strip().lower(),
            )
        ).mappings().first()
        return row["fee"] if row else None


# One-time setup: creates the course_fees table and seeds it if empty. Safe
# to call on every startup — it only does work the first time.
setup_course_fees_table()
seed_course_fees()
