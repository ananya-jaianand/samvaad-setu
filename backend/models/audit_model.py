"""
SQLAlchemy ORM models for the audit trail and feedback loop.

audit_log      — immutable record of every pipeline state transition
verified_interactions — confirmed/corrected interactions for retraining
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Float, Integer, DateTime, Text, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    # "system" | "citizen" | "agent"
    actor: Mapped[str] = mapped_column(String(16), nullable=False, default="system")
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


class VerifiedInteraction(Base):
    __tablename__ = "verified_interactions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    audio_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    asr_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    intent: Mapped[str] = mapped_column(String(64), nullable=False, default="other_grievance")
    dialect: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    district: Mapped[str] = mapped_column(String(64), nullable=False, default="default")
    # "pending" | "confirmed" | "partial" | "rejected" | "escalated"
    verification_state: Mapped[str] = mapped_column(String(16), nullable=False)
    agent_corrections_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    final_intent: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    composite_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sentiment_label: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="kn")
    clarification_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_escalated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
