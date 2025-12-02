from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    answer_type = Column(String, nullable=False)
    gender = Column(String, nullable=True)
    is_required = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    options = relationship(
        "AnswerOption",
        back_populates="question",
        cascade="all, delete-orphan",
        lazy="joined",
    )


class AnswerOption(Base):
    __tablename__ = "answer_options"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(
        Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    option_text = Column(String, nullable=False)
    value = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    question = relationship("Question", back_populates="options")


class UserAnswer(Base):
    __tablename__ = "user_answers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    answer_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    question = relationship("Question")
    user = relationship("User", backref="answers")


class UserAnswerOption(Base):
    __tablename__ = "user_answer_options"

    id = Column(Integer, primary_key=True, index=True)
    user_answer_id = Column(
        Integer, ForeignKey("user_answers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    option_id = Column(
        Integer, ForeignKey("answer_options.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user_answer = relationship("UserAnswer", backref="selected_options")
    option = relationship("AnswerOption")
