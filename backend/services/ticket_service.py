"""
Ticket creation and retrieval for citizen grievance submissions.

A ticket is created at one of three moments:
  "confirmed"  — citizen confirmed the AI's understanding via the verification loop
  "escalated"  — call was handed off to a human agent
  "call_ended" — WebSocket closed without prior confirmation or escalation

Ticket IDs are derived deterministically from the session_id:
  SS-XXXXXXXX  (SS- prefix + first 8 hex chars of session_id, uppercased)

Every write is fire-and-forget — pipeline latency is never blocked.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel

from services.intent_taxonomy import IntentTaxonomy

_taxonomy = IntentTaxonomy()

_PRIORITY_SLA: dict[int, int] = {
    1: 1,   # emergency / always-escalate
    2: 3,   # high priority
    3: 5,   # normal
    4: 7,   # low priority
    5: 10,  # very low
}


class TicketInfo(BaseModel):
    ticket_id: str
    session_id: str
    trigger: str          # "confirmed" | "escalated" | "call_ended"
    intent: str
    department: str
    district: str
    language: str
    status: str           # "submitted" | "in_review" | "resolved"
    sla_days: int
    summary: str
    created_at: str


def _ticket_id(session_id: str) -> str:
    return "SS-" + session_id.replace("-", "")[:8].upper()


def _build_info(session, trigger: str) -> TicketInfo:
    from models.session_model import SessionState  # local import to avoid circular
    intent = (session.final_intent or "other_grievance")
    dept = _taxonomy.get_responsible_department(intent)
    priority = _taxonomy.get_escalation_priority(intent)
    sla = _PRIORITY_SLA.get(priority, 5)
    summary = (
        session.escalation_summary
        or f"Grievance regarding: {intent.replace('_', ' ').title()}"
    )
    return TicketInfo(
        ticket_id=_ticket_id(session.session_id),
        session_id=session.session_id,
        trigger=trigger,
        intent=intent,
        department=dept,
        district=session.district,
        language=session.detected_language,
        status="submitted",
        sla_days=sla,
        summary=summary,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


async def create_ticket(session, trigger: str) -> TicketInfo:
    """
    Build a TicketInfo and persist it to Postgres.
    Idempotent: if a row already exists for this session_id the existing
    record is returned without modification.
    """
    info = _build_info(session, trigger)
    try:
        await _persist(info)
    except Exception as exc:
        print(f"[TICKET] DB write failed (non-fatal): {exc}")
    return info


async def get_ticket(session_id: str) -> Optional[TicketInfo]:
    """Return the ticket for a session, or None if not yet created."""
    try:
        from db import get_session_factory
        from models.audit_model import Ticket
        from sqlalchemy import select

        factory = get_session_factory()
        async with factory() as db:
            result = await db.execute(
                select(Ticket).where(Ticket.session_id == session_id)
            )
            row = result.scalar_one_or_none()
            if row is None:
                return None
            return TicketInfo(
                ticket_id=row.ticket_id,
                session_id=row.session_id,
                trigger=row.trigger,
                intent=row.intent,
                department=row.responsible_department,
                district=row.district,
                language=row.language,
                status=row.status,
                sla_days=row.sla_days,
                summary=row.summary,
                created_at=row.created_at.isoformat() if row.created_at else "",
            )
    except Exception as exc:
        print(f"[TICKET] DB read failed: {exc}")
        return None


async def list_tickets(
    limit: int = 30,
    offset: int = 0,
    status: Optional[str] = None,
    district: Optional[str] = None,
) -> list[TicketInfo]:
    """Return recent tickets from Postgres, newest first."""
    try:
        from db import get_session_factory
        from models.audit_model import Ticket
        from sqlalchemy import select, desc

        factory = get_session_factory()
        async with factory() as db:
            q = select(Ticket).order_by(desc(Ticket.created_at)).limit(limit).offset(offset)
            if status:
                q = q.where(Ticket.status == status)
            if district:
                q = q.where(Ticket.district == district)
            rows = (await db.execute(q)).scalars().all()
            return [
                TicketInfo(
                    ticket_id=r.ticket_id,
                    session_id=r.session_id,
                    trigger=r.trigger,
                    intent=r.intent,
                    department=r.responsible_department,
                    district=r.district,
                    language=r.language,
                    status=r.status,
                    sla_days=r.sla_days,
                    summary=r.summary,
                    created_at=r.created_at.isoformat() if r.created_at else "",
                )
                for r in rows
            ]
    except Exception as exc:
        print(f"[TICKET] list_tickets failed: {exc}")
        return []


async def update_ticket_status(session_id: str, status: str) -> None:
    """Update a ticket's status (e.g. 'in_review' | 'resolved')."""
    try:
        from db import get_session_factory
        from models.audit_model import Ticket
        from sqlalchemy import update

        factory = get_session_factory()
        async with factory() as db:
            await db.execute(
                update(Ticket).where(Ticket.session_id == session_id).values(status=status)
            )
            await db.commit()
    except Exception as exc:
        print(f"[TICKET] update_ticket_status failed: {exc}")


async def _persist(info: TicketInfo) -> None:
    from db import get_session_factory
    from models.audit_model import Ticket
    from sqlalchemy import select

    factory = get_session_factory()
    async with factory() as db:
        existing = await db.execute(
            select(Ticket).where(Ticket.session_id == info.session_id)
        )
        if existing.scalar_one_or_none() is not None:
            return
        row = Ticket(
            id=str(uuid.uuid4()),
            ticket_id=info.ticket_id,
            session_id=info.session_id,
            trigger=info.trigger,
            intent=info.intent,
            responsible_department=info.department,
            district=info.district,
            language=info.language,
            status=info.status,
            sla_days=info.sla_days,
            summary=info.summary,
        )
        db.add(row)
        await db.commit()
