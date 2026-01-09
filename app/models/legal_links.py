from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.database import Base


class LegalLinks(Base):
    __tablename__ = "legal_links"

    id = Column(Integer, primary_key=True, index=True)
    terms_url = Column(String, nullable=True)
    privacy_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
