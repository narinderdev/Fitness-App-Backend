from app.database import Base, engine, SessionLocal
from app.models.user import User

# Ensure all tables exist
Base.metadata.create_all(bind=engine)

def run_seed():
    db = SessionLocal()
    try:
        # If database has no users create default admin
        if db.query(User).count() == 0:
            admin_user = User(
                first_name="Admin",
                last_name="User",
                email="mdkaifeeeminence@gmail.com",
                otp=None,
                phone=None,
                dob=None,
                gender=None,
                photo=None,
                is_active=True
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
