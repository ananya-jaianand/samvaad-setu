"""
Feedback Loop Service — writes verified interactions and agent corrections
to Postgres for use as a retraining corpus.

All writes are fire-and-forget. Export yields JSONL lines for streaming.
"""
import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import AsyncIterator, Optional

from models.audit_model import VerifiedInteraction
from models.session_model import SessionState


def _audio_hash(audio_bytes: bytes | None) -> Optional[str]:
    if not audio_bytes:
        return None
    return hashlib.sha256(audio_bytes).hexdigest()[:16]


async def write_verified_interaction(
    session: SessionState,
    audio_bytes: bytes | None = None,
) -> Optional[str]:
    """
    Called when verification_state becomes 'confirmed'. Returns the row ID,
    or None if the write failed.
    """
    try:
        from db import get_session_factory

        last_citizen = next(
            (t for t in reversed(session.turns) if t.speaker == "citizen"), None
        )
        last_sentiment = (
            session.sentiment_timeline[-1] if session.sentiment_timeline else {}
        )

        row = VerifiedInteraction(
            id=str(uuid.uuid4()),
            session_id=session.session_id,
            created_at=datetime.now(timezone.utc),
            audio_hash=_audio_hash(audio_bytes),
            asr_text=last_citizen.raw_transcript if last_citizen else "",
            intent=session.final_intent or "other_grievance",
            dialect=None,  # populated from session.district via dialect_context if needed
            district=session.district,
            verification_state=session.verification_state,
            agent_corrections_json="[]",
            final_intent=session.final_intent,
            composite_confidence=session.composite_confidence,
            sentiment_label=last_sentiment.get("label"),
            language=session.detected_language,
            clarification_count=session.clarification_count,
            is_escalated=session.is_escalated,
        )

        factory = get_session_factory()
        async with factory() as db:
            db.add(row)
            await db.commit()
            await db.refresh(row)
            return row.id

    except Exception as exc:
        print(f"[FEEDBACK] write_verified_interaction failed: {exc}")
        return None


async def record_agent_correction(
    session_id: str,
    field: str,
    value: str,
    agent_id: str = "agent",
) -> bool:
    """
    Append one agent correction to the verified_interactions row for this session.
    Creates a placeholder row if none exists yet (e.g. escalated without confirmation).
    Returns True on success.
    """
    try:
        from sqlalchemy import select
        from db import get_session_factory

        factory = get_session_factory()
        async with factory() as db:
            result = await db.execute(
                select(VerifiedInteraction)
                .where(VerifiedInteraction.session_id == session_id)
                .order_by(VerifiedInteraction.created_at.desc())
                .limit(1)
            )
            row = result.scalar_one_or_none()

            if row is None:
                row = VerifiedInteraction(
                    id=str(uuid.uuid4()),
                    session_id=session_id,
                    created_at=datetime.now(timezone.utc),
                    verification_state="escalated",
                )
                db.add(row)

            corrections: list[dict] = json.loads(row.agent_corrections_json or "[]")
            corrections.append({
                "field": field,
                "value": value,
                "agent_id": agent_id,
                "ts": datetime.now(timezone.utc).isoformat(),
            })
            row.agent_corrections_json = json.dumps(corrections)

            if field == "intent":
                row.final_intent = value

            await db.commit()
            return True

    except Exception as exc:
        print(f"[FEEDBACK] record_agent_correction failed: {exc}")
        return False


async def export_jsonl(since: Optional[datetime] = None) -> AsyncIterator[str]:
    """
    Yield verified interactions as JSONL lines, optionally filtered by created_at.
    Used by GET /training-data/export for streaming responses.
    """
    try:
        from sqlalchemy import select
        from db import get_session_factory

        factory = get_session_factory()
        async with factory() as db:
            query = select(VerifiedInteraction).order_by(VerifiedInteraction.created_at)
            if since:
                query = query.where(VerifiedInteraction.created_at >= since)

            result = await db.execute(query)
            rows = result.scalars().all()

        for row in rows:
            record = {
                "id": row.id,
                "session_id": row.session_id,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "audio_hash": row.audio_hash,
                "asr_text": row.asr_text,
                "intent": row.intent,
                "final_intent": row.final_intent,
                "dialect": row.dialect,
                "district": row.district,
                "language": row.language,
                "verification_state": row.verification_state,
                "clarification_count": row.clarification_count,
                "is_escalated": row.is_escalated,
                "composite_confidence": row.composite_confidence,
                "sentiment_label": row.sentiment_label,
                "agent_corrections": json.loads(row.agent_corrections_json or "[]"),
            }
            yield json.dumps(record, ensure_ascii=False) + "\n"

    except Exception as exc:
        print(f"[FEEDBACK] export_jsonl failed: {exc}")
        return
