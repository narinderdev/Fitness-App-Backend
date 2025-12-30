from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Program(Base):
    __tablename__ = "programs"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(120), unique=True, nullable=False, index=True)
    title = Column(String(150), nullable=False)
    subtitle = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    duration_days = Column(Integer, nullable=False)
    workouts_per_week = Column(Integer, nullable=False, default=5)
    rest_days_per_week = Column(Integer, nullable=False, default=2)
    level = Column(String(50), nullable=True)
    access_level = Column(String(20), nullable=False, default="free")
    price_usd = Column(Float, nullable=True)
    cta_label = Column(String(120), nullable=True)
    hero_image_url = Column(String, nullable=True)
    cover_image_url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_featured = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    days = relationship(
        "ProgramDay",
        back_populates="program",
        cascade="all, delete-orphan",
        order_by="ProgramDay.day_number",
    )
    enrollments = relationship(
        "ProgramEnrollment",
        back_populates="program",
        cascade="all, delete-orphan",
    )


class ProgramDay(Base):
    __tablename__ = "program_days"
    __table_args__ = (
        UniqueConstraint("program_id", "day_number", name="uq_program_day_number"),
    )

    id = Column(Integer, primary_key=True, index=True)
    program_id = Column(Integer, ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    day_number = Column(Integer, nullable=False)
    title = Column(String(150), nullable=False)
    focus = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    is_rest_day = Column(Boolean, default=False, nullable=False)
    workout_summary = Column(Text, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="SET NULL"), nullable=True)
    tips = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    program = relationship("Program", back_populates="days")
    video = relationship("Video", lazy="joined")


class ProgramDayProgress(Base):
    __tablename__ = "program_day_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "program_day_id", name="uq_user_program_day"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    program_day_id = Column(
        Integer,
        ForeignKey("program_days.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    completed_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ProgramEnrollment(Base):
    __tablename__ = "program_enrollments"
    __table_args__ = (
        UniqueConstraint("user_id", "program_id", name="uq_user_program_enrollment"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    program_id = Column(Integer, ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    start_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    program = relationship("Program", back_populates="enrollments")
