import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, Text, DateTime
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


class ContactMessage(Base):
    __tablename__ = "contact_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(120), nullable=False)
    email = Column(String(255), nullable=False)
    category = Column(String(40), default="general")
    subject = Column(String(180), default="")
    message = Column(Text, nullable=False)
    session_id = Column(String(100), default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class Report(Base):
    __tablename__ = "reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), default="")
    scorecard_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)


class ToolResult(Base):
    __tablename__ = "tool_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tool = Column(String(50), nullable=False)
    result_json = Column(Text, default="{}")
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


class ConsentLog(Base):
    __tablename__ = "consent_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), default="")
    action = Column(String(100), nullable=False)
    policy_version = Column(String(32), nullable=False)
    source = Column(String(100), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
