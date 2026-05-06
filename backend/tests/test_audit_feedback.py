"""
Tests for audit_log and feedback_loop services.

Uses an in-memory SQLite database (via aiosqlite) to avoid requiring
a running Postgres instance. The engine is patched before each test.
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import pytest_asyncio
import asyncio

import db as _db
from db import Base
from models.audit_model import AuditLog, VerifiedInteraction
from models.session_model import SessionState, Turn, TurnSentiment
from services.audit_log import log_event, get_audit_trail
from services.feedback_loop import (
    write_verified_interaction,
    record_agent_correction,
    export_jsonl,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="function")
async def sqlite_db():
    """Reinitialise the module-level engine with an in-memory SQLite DB."""
    _db.init_db("sqlite:///")  # aiosqlite in-memory
    engine = _db._engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()
    _db._engine = None
    _db._session_factory = None


def _make_session(
    session_id: str = "sess-001",
    intent: str = "water_supply_complaint",
    verification_state: str = "confirmed",
) -> SessionState:
    session = SessionState(
        session_id=session_id,
        district="bengaluru_urban",
        detected_language="kn",
        verification_state=verification_state,
        final_intent=intent,
        composite_confidence=0.82,
        clarification_count=0,
        is_escalated=False,
    )
    session.turns.append(
        Turn(
            speaker="citizen",
            raw_transcript="ನೀರು ಬರ್ತಿಲ್ಲ",
            asr_confidence=0.87,
            intent=intent,
            sentiment=TurnSentiment(label="calm", intensity=0.2),
        )
    )
    return session


# ── audit_log tests ───────────────────────────────────────────────────────────

class TestAuditLog:
    @pytest.mark.asyncio
    async def test_log_event_writes_row(self, sqlite_db):
        await log_event("sess-001", "session_created", actor="system", payload={"k": "v"})
        trail = await get_audit_trail("sess-001")
        assert len(trail) == 1
        assert trail[0]["event_type"] == "session_created"
        assert trail[0]["actor"] == "system"
        assert trail[0]["payload"] == {"k": "v"}

    @pytest.mark.asyncio
    async def test_log_event_multiple_types(self, sqlite_db):
        for event in ("session_created", "verification_confirmed", "escalation_triggered"):
            await log_event("sess-002", event)
        trail = await get_audit_trail("sess-002")
        assert len(trail) == 3
        types = [e["event_type"] for e in trail]
        assert types == ["session_created", "verification_confirmed", "escalation_triggered"]

    @pytest.mark.asyncio
    async def test_get_audit_trail_empty_for_unknown_session(self, sqlite_db):
        trail = await get_audit_trail("nonexistent-session")
        assert trail == []

    @pytest.mark.asyncio
    async def test_get_audit_trail_isolation(self, sqlite_db):
        await log_event("sess-A", "session_created")
        await log_event("sess-B", "session_created")
        trail_a = await get_audit_trail("sess-A")
        trail_b = await get_audit_trail("sess-B")
        assert len(trail_a) == 1
        assert len(trail_b) == 1

    @pytest.mark.asyncio
    async def test_log_event_ordered_oldest_first(self, sqlite_db):
        await log_event("sess-003", "session_created")
        await log_event("sess-003", "verification_partial")
        await log_event("sess-003", "verification_confirmed")
        trail = await get_audit_trail("sess-003")
        types = [e["event_type"] for e in trail]
        assert types.index("session_created") < types.index("verification_confirmed")

    @pytest.mark.asyncio
    async def test_log_event_graceful_without_db(self):
        """log_event must not raise even when DB is not configured."""
        _db._engine = None
        _db._session_factory = None
        # Should complete without exception (prints a warning)
        await log_event("sess-X", "session_created")


# ── feedback_loop tests ───────────────────────────────────────────────────────

class TestWriteVerifiedInteraction:
    @pytest.mark.asyncio
    async def test_write_confirmed_creates_row(self, sqlite_db):
        session = _make_session(verification_state="confirmed")
        row_id = await write_verified_interaction(session)
        assert row_id is not None

        from sqlalchemy import select
        factory = _db.get_session_factory()
        async with factory() as db:
            result = await db.execute(
                select(VerifiedInteraction).where(VerifiedInteraction.id == row_id)
            )
            row = result.scalar_one()

        assert row.session_id == "sess-001"
        assert row.intent == "water_supply_complaint"
        assert row.final_intent == "water_supply_complaint"
        assert row.verification_state == "confirmed"
        assert row.district == "bengaluru_urban"
        assert row.language == "kn"

    @pytest.mark.asyncio
    async def test_write_stores_asr_text(self, sqlite_db):
        session = _make_session()
        row_id = await write_verified_interaction(session)

        from sqlalchemy import select
        factory = _db.get_session_factory()
        async with factory() as db:
            result = await db.execute(
                select(VerifiedInteraction).where(VerifiedInteraction.id == row_id)
            )
            row = result.scalar_one()
        assert "ನೀರು" in row.asr_text

    @pytest.mark.asyncio
    async def test_write_graceful_without_db(self):
        """write_verified_interaction must return None gracefully when DB is down."""
        _db._engine = None
        _db._session_factory = None
        session = _make_session()
        result = await write_verified_interaction(session)
        assert result is None


class TestRecordAgentCorrection:
    @pytest.mark.asyncio
    async def test_correction_appended_to_existing_row(self, sqlite_db):
        session = _make_session()
        row_id = await write_verified_interaction(session)
        assert row_id is not None

        ok = await record_agent_correction("sess-001", field="intent", value="ration_card_status")
        assert ok is True

        from sqlalchemy import select
        factory = _db.get_session_factory()
        async with factory() as db:
            result = await db.execute(
                select(VerifiedInteraction).where(VerifiedInteraction.id == row_id)
            )
            row = result.scalar_one()

        corrections = json.loads(row.agent_corrections_json)
        assert len(corrections) == 1
        assert corrections[0]["field"] == "intent"
        assert corrections[0]["value"] == "ration_card_status"
        assert row.final_intent == "ration_card_status"

    @pytest.mark.asyncio
    async def test_correction_creates_placeholder_row_if_missing(self, sqlite_db):
        """If no VerifiedInteraction row exists, record_agent_correction creates one."""
        ok = await record_agent_correction("sess-no-prior", field="intent", value="road_damage")
        assert ok is True

        from sqlalchemy import select
        factory = _db.get_session_factory()
        async with factory() as db:
            result = await db.execute(
                select(VerifiedInteraction).where(VerifiedInteraction.session_id == "sess-no-prior")
            )
            row = result.scalar_one_or_none()

        assert row is not None
        assert row.final_intent == "road_damage"

    @pytest.mark.asyncio
    async def test_multiple_corrections_accumulate(self, sqlite_db):
        session = _make_session()
        await write_verified_interaction(session)
        await record_agent_correction("sess-001", "intent", "road_damage")
        await record_agent_correction("sess-001", "intent", "ration_card_status")

        from sqlalchemy import select
        factory = _db.get_session_factory()
        async with factory() as db:
            result = await db.execute(
                select(VerifiedInteraction).where(VerifiedInteraction.session_id == "sess-001")
            )
            row = result.scalar_one()

        corrections = json.loads(row.agent_corrections_json)
        assert len(corrections) == 2


class TestExportJsonl:
    @pytest.mark.asyncio
    async def test_export_yields_jsonl_for_each_row(self, sqlite_db):
        for i in range(3):
            session = _make_session(session_id=f"sess-{i:03}")
            await write_verified_interaction(session)

        lines = [line async for line in export_jsonl()]
        assert len(lines) == 3
        for line in lines:
            record = json.loads(line)
            assert "session_id" in record
            assert "intent" in record
            assert "verification_state" in record

    @pytest.mark.asyncio
    async def test_export_filters_by_since(self, sqlite_db):
        from datetime import datetime, timedelta

        session_old = _make_session(session_id="sess-old")
        await write_verified_interaction(session_old)

        # Manually set a future `since` — only rows after it should appear
        future = datetime.utcnow() + timedelta(hours=1)

        lines = [line async for line in export_jsonl(since=future)]
        assert lines == []

        # Past `since` should return the row
        past = datetime.utcnow() - timedelta(hours=1)
        lines = [line async for line in export_jsonl(since=past)]
        assert len(lines) == 1

    @pytest.mark.asyncio
    async def test_export_includes_agent_corrections(self, sqlite_db):
        session = _make_session()
        await write_verified_interaction(session)
        await record_agent_correction("sess-001", "intent", "road_damage")

        lines = [line async for line in export_jsonl()]
        record = json.loads(lines[0])
        assert record["agent_corrections"][0]["field"] == "intent"
        assert record["agent_corrections"][0]["value"] == "road_damage"

    @pytest.mark.asyncio
    async def test_export_empty_when_no_rows(self, sqlite_db):
        lines = [line async for line in export_jsonl()]
        assert lines == []
