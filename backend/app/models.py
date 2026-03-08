from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.dialects.sqlite import JSON as SQLITE_JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import JSON
from sqlalchemy.orm import relationship
from .db import Base


def json_column():
    # Use JSON/JSONB depending on backend
    return Column(JSON().with_variant(JSONB, "postgresql").with_variant(SQLITE_JSON, "sqlite"))


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    stage = Column(String, nullable=False)
    source = Column(String, nullable=False, default="seed")
    subject = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    skills = relationship("Skill", back_populates="category", cascade="all, delete-orphan")


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    skill_id = Column(String, index=True, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    name = Column(String, nullable=False)
    summary = Column(String, nullable=False)

    category = relationship("Category", back_populates="skills")
    levels = relationship("Level", back_populates="skill", cascade="all, delete-orphan")


class Level(Base):
    __tablename__ = "levels"

    id = Column(Integer, primary_key=True, index=True)
    skill_id = Column(Integer, ForeignKey("skills.id"), nullable=False)
    level = Column(String, nullable=False)
    title = Column(String, nullable=False)
    objective = Column(String, nullable=False)
    points = json_column()
    micro_split = json_column()

    skill = relationship("Skill", back_populates="levels")


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(String, unique=True, index=True, nullable=False)
    skill_ref = Column(String, nullable=True)
    daily_minutes = Column(Integer, nullable=False)
    days_per_week = Column(Integer, nullable=False)
    schedule = json_column()
    flat_tasks = json_column()
    created_at = Column(DateTime(timezone=True), server_default=func.now())
