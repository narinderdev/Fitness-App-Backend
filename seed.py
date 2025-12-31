import os
from dotenv import load_dotenv
from sqlalchemy import inspect, text, func

from app.database import Base, engine, SessionLocal
from app.models.user import User
from app.models.program import Program, ProgramDay
from app.models.nutrition import FoodCategory, FoodItem, FoodLog
from app.models.exercise_library import ExerciseLibraryItem
from app.models.question import Question, AnswerOption

FREE_WEEK_TEMPLATE = [
    {
        "title": "Full Body Ignite",
        "focus": "Strength",
        "summary": "Compound strength circuits to activate every muscle group.",
        "description": "Bodyweight strength work paired with low-impact cardio finishers.",
        "duration": 30,
        "is_rest_day": False,
    },
    {
        "title": "Cardio Core Burn",
        "focus": "Endurance",
        "summary": "Interval work that keeps the heart rate lifted while sculpting the core.",
        "description": "Alternating cardio ladders with core planks keeps training simple but challenging.",
        "duration": 28,
        "is_rest_day": False,
    },
    {
        "title": "Mobility + Balance",
        "focus": "Mobility",
        "summary": "Slow, controlled flows that improve range of motion.",
        "description": "Hinge, twist, and balance drills to offset long work days.",
        "duration": 25,
        "is_rest_day": False,
    },
    {
        "title": "Strength Intervals",
        "focus": "Strength",
        "summary": "Classic interval format focused on lower-body power.",
        "description": "Squat and lunge variations with tempo cues keep things spicy.",
        "duration": 30,
        "is_rest_day": False,
    },
    {
        "title": "Mindful Sweat",
        "focus": "Cardio",
        "summary": "Low-impact cardio session that prioritizes breathing and form.",
        "description": "Perfect for smaller spaces—no equipment and minimal jumping.",
        "duration": 24,
        "is_rest_day": False,
    },
    {
        "title": "Active Recovery",
        "focus": "Recovery",
        "summary": "Guided stretching and mobility to keep joints happy.",
        "description": "Focus on hips, shoulders, and spine with foam rolling prompts.",
        "duration": 20,
        "is_rest_day": True,
    },
    {
        "title": "Complete Rest",
        "focus": "Mindfulness",
        "summary": "Let the body fully recover—hydration and light walking encouraged.",
        "description": "Use this day to reset intentions for the week ahead.",
        "duration": None,
        "is_rest_day": True,
    },
]

PREMIUM_WEEK_TEMPLATE = [
    {
        "title": "Power Foundations",
        "focus": "Strength",
        "summary": "Progressive overload session alternating tempo and rep schemes.",
        "description": "Each week layers more reps or resistance for measurable gains.",
        "duration": 32,
        "is_rest_day": False,
    },
    {
        "title": "Metabolic Conditioning",
        "focus": "Endurance",
        "summary": "Timed efforts with programmed rest for sustainable pacing.",
        "description": "Includes options for dumbbells or bodyweight only formats.",
        "duration": 30,
        "is_rest_day": False,
    },
    {
        "title": "Core + Mobility Reset",
        "focus": "Mobility",
        "summary": "Integrates Pilates-inspired core work with mobility drills.",
        "description": "Improves posture and reinforces core activation for heavy days.",
        "duration": 26,
        "is_rest_day": False,
    },
    {
        "title": "Athletic Conditioning",
        "focus": "Agility",
        "summary": "Power moves, plyometrics, and agility ladders to stay explosive.",
        "description": "Includes low-impact options so everyone can participate.",
        "duration": 28,
        "is_rest_day": False,
    },
    {
        "title": "Strength Endurance",
        "focus": "Strength",
        "summary": "Longer working sets that challenge stamina and grit.",
        "description": "Alternates unilateral and bilateral moves each week.",
        "duration": 34,
        "is_rest_day": False,
    },
    FREE_WEEK_TEMPLATE[5],  # Active recovery reused
    FREE_WEEK_TEMPLATE[6],  # Complete rest reused
]

DEFAULT_FOOD_CATEGORIES = [
    {"name": "Fruits", "description": "Fresh fruits and berries."},
    {"name": "Vegetables", "description": "Leafy greens and veggies."},
    {"name": "Proteins", "description": "Lean protein sources."},
    {"name": "Grains", "description": "Whole grains and carbs."},
    {"name": "Snacks", "description": "Quick bites."},
]

DEFAULT_EXERCISE_LIBRARY_ITEMS = [
    {"slug": "Core", "title": "Core", "sort_order": 1},
    {"slug": "Arms", "title": "Arm", "sort_order": 2},
    {"slug": "Legs", "title": "Legs", "sort_order": 3},
    {"slug": "FullBody", "title": "Full Body", "sort_order": 4},
]

DEFAULT_GOAL_QUESTIONS = [
    {
        "question": "What is your current weight?",
        "description": "Enter your current weight.",
        "answer_type": "weight",
        "is_required": True,
        "options": [
            {"option_text": "kg", "value": "kg"},
            {"option_text": "lb", "value": "lb"},
        ],
    },
    {
        "question": "What is your goal weight?",
        "description": "Enter the weight you want to reach.",
        "answer_type": "number",
        "is_required": True,
        "options": [
            {"option_text": "kg", "value": "kg"},
            {"option_text": "lb", "value": "lb"},
        ],
    },
    {
        "question": "How long do you want to reach your goal?",
        "description": "Enter the number of weeks or months.",
        "answer_type": "number",
        "is_required": True,
        "options": [
            {"option_text": "Weeks", "value": "weeks"},
            {"option_text": "Months", "value": "months"},
        ],
    },
]

DEFAULT_FOODS = [
    {
        "name": "Apple",
        "category_name": "Fruits",
        "calories": 95,
        "protein": 0.5,
        "carbs": 25,
        "fat": 0.3,
        "serving_quantity": 1,
        "serving_unit": "medium (182g)",
    },
    {
        "name": "Banana",
        "category_name": "Fruits",
        "calories": 105,
        "protein": 1.3,
        "carbs": 27,
        "fat": 0.3,
        "serving_quantity": 1,
        "serving_unit": "medium (118g)",
    },
    {
        "name": "Baby Spinach",
        "category_name": "Vegetables",
        "calories": 20,
        "protein": 2.0,
        "carbs": 3.4,
        "fat": 0.3,
        "serving_quantity": 2,
        "serving_unit": "cups (raw)",
    },
    {
        "name": "Grilled Chicken Breast",
        "category_name": "Proteins",
        "calories": 165,
        "protein": 31,
        "carbs": 0,
        "fat": 3.6,
        "serving_quantity": 1,
        "serving_unit": "serving (113g)",
    },
    {
        "name": "Quinoa (cooked)",
        "category_name": "Grains",
        "calories": 222,
        "protein": 8,
        "carbs": 39,
        "fat": 3.6,
        "serving_quantity": 1,
        "serving_unit": "cup",
    },
    {
        "name": "Almond Butter",
        "category_name": "Snacks",
        "calories": 98,
        "fat": 9,
        "protein": 3.4,
        "carbs": 3.4,
        "serving_quantity": 1,
        "serving_unit": "tablespoon",
    },
]

# Load environment variables
load_dotenv()

# Ensure all tables exist
Base.metadata.create_all(bind=engine)


def _ensure_bmi_columns():
    """Add new BMI columns for legacy databases that predate the schema change."""
    inspector = inspect(engine)
    column_names = {col["name"] for col in inspector.get_columns("users")}
    statements = []
    if "bmi_value" not in column_names:
        statements.append("ALTER TABLE users ADD COLUMN bmi_value DOUBLE PRECISION")
    if "bmi_category" not in column_names:
        statements.append("ALTER TABLE users ADD COLUMN bmi_category TEXT")
    if not statements:
        return
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
            print(f"✔ Applied migration: {statement}")


_ensure_bmi_columns()


def _ensure_food_schema():
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    if "food_categories" not in tables:
        FoodCategory.__table__.create(engine)
        print("✔ Created food_categories table")

    statements = []
    food_columns = {col["name"] for col in inspector.get_columns("food_items")}
    if "description" not in food_columns:
        statements.append("ALTER TABLE food_items ADD COLUMN description TEXT")
    if "category_id" not in food_columns:
        statements.append("ALTER TABLE food_items ADD COLUMN category_id INTEGER REFERENCES food_categories(id) ON DELETE SET NULL")
    if "is_active" not in food_columns:
        statements.append("ALTER TABLE food_items ADD COLUMN is_active BOOLEAN DEFAULT TRUE")
    # allow manual foods without barcodes
    with engine.begin() as connection:
        if "barcode" in food_columns:
            connection.execute(text("ALTER TABLE food_items ALTER COLUMN barcode DROP NOT NULL"))
        for statement in statements:
            connection.execute(text(statement))
            print(f"✔ Applied migration: {statement}")


_ensure_food_schema()


def _backfill_manual_log_macros(db):
    """Populate missing macro totals for existing manual food logs."""
    logs = (
        db.query(FoodLog)
        .join(FoodItem, FoodLog.food_item_id == FoodItem.id)
        .filter(FoodItem.source == "manual")
        .all()
    )
    updates = 0

    for log in logs:
        item = log.food_item
        if not item:
            continue
        servings = log.serving_multiplier or 1.0
        changed = False

        def update_field(field: str, item_value: float | None):
            nonlocal changed
            if item_value is None:
                return
            current_value = getattr(log, field)
            if current_value is None or current_value == 0:
                setattr(log, field, item_value * servings)
                changed = True

        update_field("calories", item.calories)
        update_field("protein", item.protein)
        update_field("carbs", item.carbs)
        update_field("fat", item.fat)

        if changed:
            updates += 1

    if updates:
        db.commit()
        print(f"✔ Backfilled macros for {updates} manual food logs")
def _build_days(program: Program, template: list[dict]):
    days = []
    total_days = program.duration_days
    pattern_length = len(template)
    for index in range(total_days):
        config = template[index % pattern_length]
        week = index // pattern_length + 1
        ordinal = index + 1
        description = config.get("description")
        if description:
            description = f"Week {week}: {description}"
        day = ProgramDay(
            program_id=program.id,
            day_number=ordinal,
            title=f"Day {ordinal}: {config['title']}",
            focus=config.get("focus"),
            description=description,
            is_rest_day=config.get("is_rest_day", False),
            workout_summary=config.get("summary"),
            duration_minutes=config.get("duration"),
            tips=config.get("tips"),
        )
        days.append(day)
    return days


def seed_programs(db):
    return


def seed_food_catalog(db):
    name_to_category = {}
    for config in DEFAULT_FOOD_CATEGORIES:
        name = config["name"]
        existing = (
            db.query(FoodCategory)
            .filter(func.lower(FoodCategory.name) == name.lower())
            .first()
        )
        if existing:
            name_to_category[name.lower()] = existing
            continue
        category = FoodCategory(
            name=name,
            description=config.get("description"),
            is_active=True,
        )
        db.add(category)
        db.flush()
        name_to_category[name.lower()] = category
        print(f"✔ Seeded food category '{category.name}'")

    for entry in DEFAULT_FOODS:
        name = entry["name"]
        existing = (
            db.query(FoodItem)
            .filter(
                func.lower(FoodItem.product_name) == name.lower(),
                FoodItem.source == "manual",
            )
            .first()
        )
        category_name = (entry.get("category_name") or "").strip().lower()
        category = name_to_category.get(category_name)
        if existing:
            updated = False

            def maybe_set(field: str):
                nonlocal updated
                value = entry.get(field)
                if value is None:
                    return
                current = getattr(existing, field)
                if current is None:
                    setattr(existing, field, value)
                    updated = True

            maybe_set("calories")
            maybe_set("protein")
            maybe_set("carbs")
            maybe_set("fat")
            maybe_set("serving_quantity")
            maybe_set("serving_unit")
            if category and existing.category_id is None:
                existing.category_id = category.id
                updated = True
            if updated:
                print(f"✔ Updated nutrition facts for '{existing.product_name}'")
            continue
        food = FoodItem(
            product_name=name,
            calories=entry.get("calories"),
            protein=entry.get("protein"),
            carbs=entry.get("carbs"),
            fat=entry.get("fat"),
            serving_quantity=entry.get("serving_quantity", 1.0),
            serving_unit=entry.get("serving_unit", "serving"),
            source="manual",
            category_id=category.id if category else None,
            is_active=True,
        )
        db.add(food)
        print(f"✔ Seeded food '{name}'")
    db.commit()


def seed_exercise_library(db):
    for config in DEFAULT_EXERCISE_LIBRARY_ITEMS:
        slug = config["slug"]
        existing = (
            db.query(ExerciseLibraryItem)
            .filter(func.lower(ExerciseLibraryItem.slug) == slug.lower())
            .first()
        )
        if existing:
            continue
        item = ExerciseLibraryItem(
            slug=slug,
            title=config["title"],
            sort_order=config.get("sort_order", 0),
            is_active=True,
        )
        db.add(item)
        print(f"✔ Seeded exercise library item '{item.title}'")
    db.commit()


def seed_goal_questions(db):
    for config in DEFAULT_GOAL_QUESTIONS:
        question_text = config["question"]
        existing = db.query(Question).filter(Question.question == question_text).first()
        if existing:
            question = existing
            updated = False
            if question.description != config.get("description"):
                question.description = config.get("description")
                updated = True
            if question.answer_type != config["answer_type"]:
                question.answer_type = config["answer_type"]
                updated = True
            if question.is_required != config.get("is_required", False):
                question.is_required = config.get("is_required", False)
                updated = True
            if updated:
                db.flush()
        else:
            question = Question(
                question=question_text,
                description=config.get("description"),
                answer_type=config["answer_type"],
                gender=None,
                is_required=config.get("is_required", False),
                is_active=True,
            )
            db.add(question)
            db.flush()
            print(f"✔ Seeded goal question '{question.question}'")

        options = config.get("options") or []
        if options:
            existing_options = {opt.option_text.lower(): opt for opt in question.options}
            for option in options:
                option_text = option["option_text"].strip()
                if option_text.lower() in existing_options:
                    continue
                db.add(
                    AnswerOption(
                        question_id=question.id,
                        option_text=option_text,
                        value=option.get("value"),
                        is_active=True,
                    )
                )
            db.flush()
    db.commit()


def run_seed():
    db = SessionLocal()
    try:
        # Read values from .env
        first_name = os.getenv("SEED_FIRST_NAME", "Test")
        last_name = os.getenv("SEED_LAST_NAME", "User")
        email = os.getenv("SEED_EMAIL", "test@yopmail.com")
        gender = os.getenv("SEED_GENDER", "Male")

        # If database has no users create default admin
        if db.query(User).count() == 0:
            admin_user = User(
                first_name=first_name,
                last_name=last_name,
                email=email,
                otp=None,
                phone=None,
                dob=None,
                gender=gender,
                photo=None,
                is_active=True,
                is_admin=True,
            )

            db.add(admin_user)
            db.commit()
            print("✔ Default admin user seeded!")
        else:
            print("✔ Users already present, skipping seeding.")

        seed_programs(db)
        seed_food_catalog(db)
        seed_exercise_library(db)
        seed_goal_questions(db)
        _backfill_manual_log_macros(db)
        db.commit()
    except Exception as e:
        print("❌ Seeding error:", e)
    finally:
        db.close()

if __name__ == "__main__":
    run_seed()
