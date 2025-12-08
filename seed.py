import os
from dotenv import load_dotenv

from app.database import Base, engine, SessionLocal
from app.models.user import User

# Load environment variables
load_dotenv()

# Ensure all tables exist
Base.metadata.create_all(bind=engine)

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
    except Exception as e:
        print("❌ Seeding error:", e)
    finally:
        db.close()

if __name__ == "__main__":
    run_seed()
