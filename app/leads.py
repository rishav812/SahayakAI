from sqlalchemy import create_engine, MetaData, Table, Column, Text, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.config import DATABASE_URL

ALLOWED_FIELDS = {"name", "course_interest", "funnel_stage"}

engine = create_engine(DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1))
metadata = MetaData()

leads_table = Table(
    "leads",
    metadata,
    Column("phone", Text, primary_key=True),
    Column("name", Text),
    Column("course_interest", Text),
    Column("funnel_stage", Text, nullable=False, server_default="new"),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=func.now()),
)


def setup_leads_table():
    metadata.create_all(engine, tables=[leads_table])


def upsert_lead(phone: str, **fields):
    unknown = set(fields) - ALLOWED_FIELDS
    if unknown:
        raise ValueError(f"Unknown lead field(s): {unknown}")

    stmt = pg_insert(leads_table).values(phone=phone, **fields)
    stmt = stmt.on_conflict_do_update(
        index_elements=["phone"],
        set_={**fields, "updated_at": func.now()},
    )

    with engine.begin() as conn:
        conn.execute(stmt)


def get_lead(phone: str):
    with engine.connect() as conn:
        row = conn.execute(
            leads_table.select().where(leads_table.c.phone == phone)
        ).mappings().first()
        return dict(row) if row else None


# One-time setup: creates the leads table if it doesn't exist yet. Safe to
# call on every startup — it only does work the first time.
setup_leads_table()
