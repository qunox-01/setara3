import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime, Float
from app.database import Base


class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False)
    source = Column(String(100), default="")
    tool = Column(String(100), default="")
    utm_source = Column(String(100), default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tool = Column(String(100), default="")
    useful = Column(String(20), default="")  # "yes", "no", "missing"
    comment = Column(Text, default="")
    session_id = Column(String(100), default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class Report(Base):
    __tablename__ = "reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), default="")
    scorecard_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event = Column(String(100), default="")
    tool = Column(String(100), default="")
    session_id = Column(String(100), default="")
    metadata_json = Column(Text, default="{}")
    utm_source = Column(String(100), default="")
    utm_campaign = Column(String(100), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
