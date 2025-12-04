from datetime import datetime, date

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class HealthStep(Base):
    __tablename__ = "health_steps"
    __table_args__ = (UniqueConstraint("user_id", "step_date", name="uq_user_step_date"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    step_date = Column(Date, nullable=False)
    source = Column(String, nullable=False)
    steps = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", backref="health_steps")
