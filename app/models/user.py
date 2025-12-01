from sqlalchemy import Column, Integer, String
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # Registration fields
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=True)
    email = Column(String, unique=True, index=True, nullable=False)
    
    # OTP stored temporarily
    otp = Column(String, nullable=True)

    # Profile update fields
    phone = Column(String, nullable=True)     # optional
    dob = Column(String, nullable=True)       # store YYYY-MM-DD
    gender = Column(String, nullable=True)    
    photo = Column(String, nullable=True)     # image URL or base64
