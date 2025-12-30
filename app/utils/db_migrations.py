from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def ensure_program_price_column(engine: Engine) -> None:
    inspector = inspect(engine)
    if "programs" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("programs")}
    if "price_usd" in columns:
        return
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE programs ADD COLUMN price_usd FLOAT"))
