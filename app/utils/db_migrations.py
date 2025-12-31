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


def drop_food_category_slug_and_sort(engine: Engine) -> None:
    inspector = inspect(engine)
    if "food_categories" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("food_categories")}
    columns_to_drop = [column for column in ("slug", "sort_order") if column in columns]
    if not columns_to_drop:
        return

    if engine.dialect.name == "sqlite":
        try:
            with engine.begin() as connection:
                for column in columns_to_drop:
                    connection.execute(text(f"ALTER TABLE food_categories DROP COLUMN {column}"))
            return
        except Exception:
            pass

        with engine.connect() as connection:
            connection.execute(text("PRAGMA foreign_keys=OFF"))
            trans = connection.begin()
            try:
                connection.execute(text("ALTER TABLE food_categories RENAME TO food_categories_old"))
                connection.execute(
                    text(
                        "CREATE TABLE food_categories ("
                        "id INTEGER PRIMARY KEY, "
                        "name VARCHAR NOT NULL, "
                        "description VARCHAR, "
                        "is_active BOOLEAN NOT NULL DEFAULT 1, "
                        "created_at DATETIME NOT NULL, "
                        "updated_at DATETIME NOT NULL"
                        ")"
                    )
                )
                connection.execute(
                    text(
                        "INSERT INTO food_categories "
                        "(id, name, description, is_active, created_at, updated_at) "
                        "SELECT id, name, description, is_active, created_at, updated_at "
                        "FROM food_categories_old"
                    )
                )
                connection.execute(text("DROP TABLE food_categories_old"))
                trans.commit()
            except Exception:
                trans.rollback()
                raise
            finally:
                connection.execute(text("PRAGMA foreign_keys=ON"))
        return

    with engine.begin() as connection:
        for column in columns_to_drop:
            connection.execute(text(f"ALTER TABLE food_categories DROP COLUMN {column}"))
