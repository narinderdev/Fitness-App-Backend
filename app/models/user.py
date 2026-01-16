from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # Registration fields
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    email = Column(String, unique=True, index=True, nullable=False)
    
    # OTP stored temporarily
    otp = Column(String, nullable=True)

    # Profile update fields
    phone = Column(String, nullable=True)     # optional
    dob = Column(String, nullable=True)       # store YYYY-MM-DD
    gender = Column(String, nullable=True)    
    photo = Column(String, nullable=True)     # image URL or base64
    bmi_value = Column(Float, nullable=True)
    bmi_category = Column(String, nullable=True)
    daily_step_goal = Column(Integer, nullable=True, default=7000)
    daily_water_goal_ml = Column(Integer, nullable=True, default=4000)
    health_data_acknowledged = Column(Boolean, default=False, nullable=False)

    # Soft delete flag
    is_active = Column(Boolean, default=True, nullable=False)

    # Admin flag
    is_admin = Column(Boolean, default=False, nullable=False)

    # Purchase flags
    has_pilates_board = Column(Boolean, default=False, nullable=False)
    has_ankle_wrist_weights = Column(Boolean, default=False, nullable=False)
    purchased_plan = Column(Boolean, default=False, nullable=False)
    last_weight_reminder_at = Column(DateTime, nullable=True)
    last_progress_photo_reminder_at = Column(DateTime, nullable=True)
