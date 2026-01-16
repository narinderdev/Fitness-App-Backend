from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def ensure_program_price_column(engine: Engine) -> None:
    inspector = inspect(engine)
    if "programs" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("programs")}
    pricing_columns = [
        "price_usd",
        "weekly_price_usd",
        "weekly_original_price_usd",
        "monthly_price_usd",
        "monthly_original_price_usd",
        "yearly_price_usd",
        "yearly_original_price_usd",
    ]
    missing_columns = [column for column in pricing_columns if column not in columns]
    if not missing_columns:
        return
    with engine.begin() as connection:
        for column in missing_columns:
            connection.execute(text(f"ALTER TABLE programs ADD COLUMN {column} FLOAT"))


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


def ensure_user_flag_columns(engine: Engine) -> None:
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("users")}
    flag_columns = [
        "has_pilates_board",
        "has_ankle_wrist_weights",
        "purchased_plan",
        "has_library_access",
    ]

    missing_columns = [column for column in flag_columns if column not in columns]
    if not missing_columns:
        return

    with engine.begin() as connection:
        for column in missing_columns:
            if engine.dialect.name == "postgresql":
                connection.execute(
                    text(
                        f"""
                        ALTER TABLE users
                        ADD COLUMN IF NOT EXISTS {column} BOOLEAN DEFAULT FALSE
                        """
                    )
                )
            else:
                # SQLite / others
                connection.execute(
                    text(
                        f"""
                        ALTER TABLE users
                        ADD COLUMN {column} BOOLEAN DEFAULT 0
                        """
                    )
                )


def ensure_user_health_ack_column(engine: Engine) -> None:
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("users")}
    if "health_data_acknowledged" in columns:
        return

    with engine.begin() as connection:
        if engine.dialect.name == "postgresql":
            connection.execute(
                text(
                    """
                    ALTER TABLE users
                    ADD COLUMN IF NOT EXISTS health_data_acknowledged BOOLEAN DEFAULT FALSE
                    """
                )
            )
        else:
            connection.execute(
                text(
                    """
                    ALTER TABLE users
                    ADD COLUMN health_data_acknowledged BOOLEAN DEFAULT 0
                    """
                )
            )


def ensure_user_daily_goal_column(engine: Engine) -> None:
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("users")}
    if "daily_step_goal" in columns:
        return

    with engine.begin() as connection:
        if engine.dialect.name == "postgresql":
            connection.execute(
                text(
                    """
                    ALTER TABLE users
                    ADD COLUMN IF NOT EXISTS daily_step_goal INTEGER DEFAULT 7000
                    """
                )
            )
        else:
            # SQLite / others
            connection.execute(
                text(
                    """
                    ALTER TABLE users
                    ADD COLUMN daily_step_goal INTEGER DEFAULT 7000
                    """
                )
            )


def ensure_user_daily_water_goal_column(engine: Engine) -> None:
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("users")}
    if "daily_water_goal_ml" in columns:
        return

    with engine.begin() as connection:
        if engine.dialect.name == "postgresql":
            connection.execute(
                text(
                    """
                    ALTER TABLE users
                    ADD COLUMN IF NOT EXISTS daily_water_goal_ml INTEGER DEFAULT 4000
                    """
                )
            )
        else:
            # SQLite / others
            connection.execute(
                text(
                    """
                    ALTER TABLE users
                    ADD COLUMN daily_water_goal_ml INTEGER DEFAULT 4000
                    """
                )
            )
        connection.execute(
            text(
                """
                UPDATE users
                SET daily_water_goal_ml = 4000
                WHERE daily_water_goal_ml IS NULL
                """
            )
        )


def ensure_user_tracking_reminder_columns(engine: Engine) -> None:
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("users")}
    reminder_columns = [
        "last_weight_reminder_at",
        "last_progress_photo_reminder_at",
    ]
    missing_columns = [column for column in reminder_columns if column not in columns]
    if not missing_columns:
        return

    with engine.begin() as connection:
        for column in missing_columns:
            if engine.dialect.name == "postgresql":
                connection.execute(
                    text(
                        f"""
                        ALTER TABLE users
                        ADD COLUMN IF NOT EXISTS {column} TIMESTAMP
                        """
                    )
                )
            else:
                connection.execute(
                    text(
                        f"""
                        ALTER TABLE users
                        ADD COLUMN {column} DATETIME
                        """
                    )
                )


def ensure_user_referral_columns(engine: Engine) -> None:
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("users")}
    referral_columns = {
        "referral_code": "VARCHAR",
        "referred_by_id": "INTEGER",
        "referral_reward_sent": "BOOLEAN",
    }
    missing_columns = {
        column: dtype
        for column, dtype in referral_columns.items()
        if column not in columns
    }
    if not missing_columns:
        return

    with engine.begin() as connection:
        for column, dtype in missing_columns.items():
            if column == "referral_reward_sent":
                if engine.dialect.name == "postgresql":
                    connection.execute(
                        text(
                            f"""
                            ALTER TABLE users
                            ADD COLUMN IF NOT EXISTS {column} BOOLEAN DEFAULT FALSE
                            """
                        )
                    )
                else:
                    connection.execute(
                        text(
                            f"""
                            ALTER TABLE users
                            ADD COLUMN {column} BOOLEAN DEFAULT 0
                            """
                        )
                    )
            else:
                if engine.dialect.name == "postgresql":
                    connection.execute(
                        text(
                            f"""
                            ALTER TABLE users
                            ADD COLUMN IF NOT EXISTS {column} {dtype}
                            """
                        )
                    )
                else:
                    connection.execute(
                        text(
                            f"""
                            ALTER TABLE users
                            ADD COLUMN {column} {dtype}
                            """
                        )
                    )


def ensure_food_item_usda_columns(engine: Engine) -> None:
    inspector = inspect(engine)
    if "food_items" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("food_items")}
    float_columns = [
        "serving_grams",
        "calories_per_100g",
        "protein_per_100g",
        "carbs_per_100g",
        "fat_per_100g",
        "default_serving_grams",
        "density_g_per_ml",
        "default_serving_ml",
    ]
    string_columns = ["source_item_id", "food_type", "default_serving_name"]
    datetime_columns = ["last_verified_at"]
    integer_columns = ["fdc_id"]

    with engine.begin() as connection:
        for column in float_columns:
            if column in columns:
                continue
            if engine.dialect.name == "postgresql":
                connection.execute(
                    text(f"ALTER TABLE food_items ADD COLUMN IF NOT EXISTS {column} FLOAT")
                )
            else:
                connection.execute(text(f"ALTER TABLE food_items ADD COLUMN {column} FLOAT"))
        for column in string_columns:
            if column in columns:
                continue
            if engine.dialect.name == "postgresql":
                connection.execute(
                    text(f"ALTER TABLE food_items ADD COLUMN IF NOT EXISTS {column} VARCHAR")
                )
            else:
                connection.execute(text(f"ALTER TABLE food_items ADD COLUMN {column} VARCHAR"))
        for column in datetime_columns:
            if column in columns:
                continue
            if engine.dialect.name == "postgresql":
                connection.execute(
                    text(f"ALTER TABLE food_items ADD COLUMN IF NOT EXISTS {column} TIMESTAMP")
                )
            else:
                connection.execute(text(f"ALTER TABLE food_items ADD COLUMN {column} DATETIME"))
        for column in integer_columns:
            if column in columns:
                continue
            if engine.dialect.name == "postgresql":
                connection.execute(
                    text(f"ALTER TABLE food_items ADD COLUMN IF NOT EXISTS {column} INTEGER")
                )
            else:
                connection.execute(text(f"ALTER TABLE food_items ADD COLUMN {column} INTEGER"))

def migrate_app_settings_to_legal_links(engine: Engine) -> None:
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    if "legal_links" not in tables and "app_settings" not in tables:
        return

    if "legal_links" not in tables and "app_settings" in tables:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE app_settings RENAME TO legal_links"))
        return

    if "legal_links" in tables and "app_settings" in tables:
        with engine.begin() as connection:
            legal_count = connection.execute(text("SELECT COUNT(*) FROM legal_links")).scalar() or 0
            if legal_count == 0:
                connection.execute(
                    text(
                        "INSERT INTO legal_links (terms_url, privacy_url, created_at, updated_at) "
                        "SELECT terms_url, privacy_url, created_at, updated_at "
                        "FROM app_settings ORDER BY id ASC LIMIT 1"
                    )
                )
            try:
                connection.execute(text("DROP TABLE app_settings"))
            except Exception:
                pass


def ensure_legal_links_subscription_column(engine: Engine) -> None:
    inspector = inspect(engine)
    if "legal_links" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("legal_links")}
    if "subscription_url" in columns:
        return

    with engine.begin() as connection:
        if engine.dialect.name == "postgresql":
            connection.execute(
                text(
                    """
                    ALTER TABLE legal_links
                    ADD COLUMN IF NOT EXISTS subscription_url VARCHAR
                    """
                )
            )
        else:
            connection.execute(
                text(
                    """
                    ALTER TABLE legal_links
                    ADD COLUMN subscription_url VARCHAR
                    """
                )
            )


def ensure_video_duration_column(engine: Engine) -> None:
    inspector = inspect(engine)
    if "videos" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("videos")}
    if "duration_seconds" in columns:
        return

    with engine.begin() as connection:
        if engine.dialect.name == "postgresql":
            connection.execute(
                text(
                    """
                    ALTER TABLE videos
                    ADD COLUMN IF NOT EXISTS duration_seconds INTEGER
                    """
                )
            )
        else:
            connection.execute(
                text(
                    """
                    ALTER TABLE videos
                    ADD COLUMN duration_seconds INTEGER
                    """
                )
            )


def ensure_video_payment_column(engine: Engine) -> None:
    inspector = inspect(engine)
    if "videos" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("videos")}
    if "requires_payment" in columns:
        return

    with engine.begin() as connection:
        if engine.dialect.name == "postgresql":
            connection.execute(
                text(
                    """
                    ALTER TABLE videos
                    ADD COLUMN IF NOT EXISTS requires_payment BOOLEAN DEFAULT FALSE
                    """
                )
            )
        else:
            connection.execute(
                text(
                    """
                    ALTER TABLE videos
                    ADD COLUMN requires_payment BOOLEAN DEFAULT 0
                    """
                )
            )


def drop_products_key_column(engine: Engine) -> None:
    inspector = inspect(engine)
    if "products" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("products")}
    if "key" not in columns:
        return

    if engine.dialect.name == "sqlite":
        with engine.connect() as connection:
            connection.execute(text("PRAGMA foreign_keys=OFF"))
            trans = connection.begin()
            try:
                connection.execute(text("ALTER TABLE products RENAME TO products_old"))
                connection.execute(
                    text(
                        "CREATE TABLE products ("
                        "id INTEGER PRIMARY KEY, "
                        "title VARCHAR NOT NULL, "
                        "subtitle VARCHAR, "
                        "badge_text VARCHAR, "
                        "description TEXT, "
                        "image_url VARCHAR, "
                        "link_url VARCHAR, "
                        "is_active BOOLEAN NOT NULL DEFAULT 1, "
                        "sort_order INTEGER NOT NULL DEFAULT 0, "
                        "created_at DATETIME NOT NULL, "
                        "updated_at DATETIME NOT NULL"
                        ")"
                    )
                )
                connection.execute(
                    text(
                        "INSERT INTO products "
                        "(id, title, subtitle, badge_text, description, image_url, link_url, "
                        "is_active, sort_order, created_at, updated_at) "
                        "SELECT id, title, subtitle, badge_text, description, image_url, link_url, "
                        "is_active, sort_order, created_at, updated_at "
                        "FROM products_old"
                    )
                )
                connection.execute(text("DROP TABLE products_old"))
                trans.commit()
            except Exception:
                trans.rollback()
                raise
            finally:
                connection.execute(text("PRAGMA foreign_keys=ON"))
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE products DROP COLUMN IF EXISTS key"))


def ensure_product_link_column(engine: Engine) -> None:
    inspector = inspect(engine)
    if "products" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("products")}
    if "link_url" in columns:
        return

    with engine.begin() as connection:
        if engine.dialect.name == "postgresql":
            connection.execute(
                text(
                    """
                    ALTER TABLE products
                    ADD COLUMN IF NOT EXISTS link_url VARCHAR
                    """
                )
            )
        else:
            connection.execute(
                text(
                    """
                    ALTER TABLE products
                    ADD COLUMN link_url VARCHAR
                    """
                )
            )
