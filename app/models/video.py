from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from app.database import Base


class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    body_part = Column(String, nullable=False, index=True)
    gender = Column(String, nullable=False)
    video_url = Column(String, nullable=False)
    thumbnail_url = Column(String, nullable=False)
    duration_seconds = Column(Integer, nullable=True)
    requires_payment = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
