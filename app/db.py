from sqlalchemy import create_engine, inspect, text
from app.config import DATABASE_URL, MAX_ROWS, QUERY_TIMEOUT_SECONDS

# Application uses a dedicated read-only database account in docker-compose.
engine = create_engine(DATABASE_URL, pool_pre_ping=True)


def get_schema() -> str:
    inspector = inspect(engine)
    parts = []
    for table in inspector.get_table_names():
        cols = inspector.get_columns(table)
        col_text = ", ".join(f"{c['name']} ({c['type']})" for c in cols)
        fks = inspector.get_foreign_keys(table)
        rels = [f"{fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}" for fk in fks]
        parts.append(f"Table {table}: {col_text}" + (f"; Relationships: {'; '.join(rels)}" if rels else ""))
    return "\n".join(parts)


def run_read_query(sql: str):
    # Defense in depth: DB role is read-only; statement timeout and row cap also apply.
    safe_sql = f"SELECT * FROM ({sql.rstrip().rstrip(';')}) AS bounded_result LIMIT {MAX_ROWS}"
    with engine.connect() as conn:
        conn.execute(text(f"SET LOCAL statement_timeout = '{QUERY_TIMEOUT_SECONDS}s'"))
        result = conn.execute(text(safe_sql))
        columns = list(result.keys())
        rows = [dict(row._mapping) for row in result.fetchall()]
    return columns, rows
