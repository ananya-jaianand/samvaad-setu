"""
Audit Log Service — immutable record of every pipeline state transition.

All writes are fire-and-forget: a DB failure logs a warning but never
stalls the voice pipeline. The audit trail is append-only by convention.
"""
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from models.audit_model import AuditLog


async def log_event(
    session_id: str,
    event_type: str,
    actor: str = "system",
    payload: dict[str, Any] | None = None,
) -> None:
    """
    Write one audit row. Silently no-ops if the DB is unavailable.

    event_type examples:
      session_created, verification_confirmed, verification_partial,
      verification_rejected, escalation_triggered, agent_correction_applied
    """
    try:
        from db import get_session_factory

        entry = AuditLog(
            id=str(uuid.uuid4()),
            session_id=session_id,
            timestamp=datetime.now(timezone.utc),
            event_type=event_type,
            actor=actor,
            payload_json=json.dumps(payload or {}, default=str),
        )

        factory = get_session_factory()
        async with factory() as db:
            db.add(entry)
            await db.commit()

    except Exception as exc:
        print(f"[AUDIT] DB write failed ({event_type}): {exc}")


async def get_audit_trail(session_id: str) -> list[dict]:
    """Return all audit rows for a session, ordered oldest-first."""
    try:
        from sqlalchemy import select
        from db import get_session_factory

        factory = get_session_factory()
        async with factory() as db:
            result = await db.execute(
                select(AuditLog)
                .where(AuditLog.session_id == session_id)
                .order_by(AuditLog.timestamp)
            )
            rows = result.scalars().all()
            return [
                {
                    "id": r.id,
                    "session_id": r.session_id,
                    "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                    "event_type": r.event_type,
                    "actor": r.actor,
                    "payload": json.loads(r.payload_json),
                }
                for r in rows
            ]
    except Exception as exc:
        print(f"[AUDIT] DB read failed: {exc}")
        return []
