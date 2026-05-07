"""
Tests for Prompt 7 — agent dashboard backend support:
  - GET /agent/queue ordering and pagination
  - WS /ws/agent/{agent_id} real-time notifications
  - POST /sessions/{id}/resolve
  - Correction propagation to feedback loop
  - GET /sessions/{id}/full-context shape
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import pytest_asyncio

import db as _db
from db import Base
from models.session_model import SessionState, Turn, TurnSentiment
from services import agent_queue as aq
from services.audit_log import get_audit_trail


# ── Shared DB fixture (SQLite in-memory) ─────────────────────────────────────

@pytest_asyncio.fixture(scope="function")
async def clean_queue():
    """Reset both in-memory and Redis queue state before and after each test."""
    aq._memory_queue.clear()
    try:
        from services.session_manager import _redis_client, _use_redis
        if _use_redis and _redis_client:
            await _redis_client.delete("escalation_queue")
    except Exception:
        pass
    yield
    aq._memory_queue.clear()
    try:
        from services.session_manager import _redis_client, _use_redis
        if _use_redis and _redis_client:
            await _redis_client.delete("escalation_queue")
    except Exception:
        pass


@pytest_asyncio.fixture(scope="function")
async def sqlite_db():
    _db.init_db("sqlite:///")
    engine = _db._engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    _db._engine = None
    _db._session_factory = None


# ── Shared FastAPI test-client fixture ───────────────────────────────────────

@pytest_asyncio.fixture(scope="function")
async def client(sqlite_db):
    """httpx async client wired to the FastAPI app."""
    import httpx
    from main import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_session(
    session_id: str = "sess-001",
    district: str = "mangaluru",
    intent: str = "water_supply_complaint",
    sentiment_intensity: float = 0.5,
    is_escalated: bool = True,
) -> SessionState:
    session = SessionState(
        session_id=session_id,
        district=district,
        detected_language="kn",
        is_escalated=is_escalated,
        final_intent=intent,
        composite_confidence=0.75,
        escalation_reason="high_distress",
        escalation_summary="Citizen reports water cut for 3 days.",
    )
    session.sentiment_timeline.append({
        "turn_id": "t1",
        "timestamp": session.created_at.isoformat(),
        "label": "distress",
        "intensity": sentiment_intensity,
    })
    return session


# ── GET /agent/queue ─────────────────────────────────────────────────────────

class TestAgentQueue:
    @pytest.mark.asyncio
    async def test_queue_ordering_by_sentiment_desc(self, clean_queue):
        """Higher sentiment intensity must appear first."""
        await aq.push_escalation("high-prio", 0.9, "high_distress", "Urgent", "bengaluru_urban", "kn", "distress_emergency")
        await aq.push_escalation("low-prio",  0.2, "low_confidence", "Routine", "mysuru", "kn", "road_damage")
        await aq.push_escalation("mid-prio",  0.6, "high_distress", "Moderate", "mangaluru", "kn", "sanitation_garbage")

        result = await aq.get_queue(limit=10, offset=0)
        ids = [r["session_id"] for r in result]
        assert ids.index("high-prio") < ids.index("mid-prio") < ids.index("low-prio")

    @pytest.mark.asyncio
    async def test_queue_pagination_limit(self, clean_queue):
        for i in range(5):
            await aq.push_escalation(f"page-sess-{i}", float(i) / 10, "low_confidence", "", "bengaluru_urban", "kn", None)

        total = await aq.queue_length()
        assert total == 5

        page1 = await aq.get_queue(limit=3, offset=0)
        page2 = await aq.get_queue(limit=3, offset=3)
        assert len(page1) == 3
        assert len(page2) == 2
        ids_p1 = {r["session_id"] for r in page1}
        ids_p2 = {r["session_id"] for r in page2}
        assert ids_p1.isdisjoint(ids_p2)

    @pytest.mark.asyncio
    async def test_remove_from_queue(self, clean_queue):
        await aq.push_escalation("to-remove", 0.8, "high_distress", "", "bengaluru_urban", "kn", None)
        assert await aq.queue_length() == 1

        await aq.remove_from_queue("to-remove")
        assert await aq.queue_length() == 0

    @pytest.mark.asyncio
    async def test_queue_endpoint_returns_expected_shape(self, client, clean_queue):
        await aq.push_escalation("e1", 0.7, "high_distress", "Test", "bengaluru_urban", "kn", "water_supply_complaint")

        resp = await client.get("/agent/queue")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert "connected_agents" in body
        assert body["total"] >= 1

    @pytest.mark.asyncio
    async def test_queue_endpoint_invalid_limit(self, client, clean_queue):
        resp = await client.get("/agent/queue?limit=0")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_queue_endpoint_invalid_offset(self, client, clean_queue):
        resp = await client.get("/agent/queue?offset=-1")
        assert resp.status_code == 400


# ── Agent WebSocket — real-time notifications ─────────────────────────────────

class TestAgentBroadcast:
    """Test broadcast_escalation directly with mock WebSocket objects."""

    @pytest.mark.asyncio
    async def test_broadcast_reaches_all_connected_agents(self):
        received: dict[str, list] = {}

        class _MockWS:
            def __init__(self, agent_id):
                self._id = agent_id
                received[agent_id] = []

            async def send_json(self, data):
                received[self._id].append(data)

        ws_a = _MockWS("agent-A")
        ws_b = _MockWS("agent-B")
        aq.register_agent("agent-A", ws_a)
        aq.register_agent("agent-B", ws_b)

        try:
            packet = {"session_id": "sess-broadcast", "reason": "high_distress"}
            await aq.broadcast_escalation(packet)

            assert len(received["agent-A"]) == 1
            assert len(received["agent-B"]) == 1
            assert received["agent-A"][0]["type"] == "new_escalation"
            assert received["agent-B"][0]["packet"]["session_id"] == "sess-broadcast"
        finally:
            aq.unregister_agent("agent-A")
            aq.unregister_agent("agent-B")

    @pytest.mark.asyncio
    async def test_broadcast_removes_dead_connections(self):
        dead_called: list[bool] = []

        class _DeadWS:
            async def send_json(self, data):
                dead_called.append(True)
                raise RuntimeError("connection closed")

        aq.register_agent("dead-agent", _DeadWS())
        try:
            await aq.broadcast_escalation({"session_id": "s1"})
            # Dead agent should have been removed
            assert "dead-agent" not in aq._agent_connections
        finally:
            aq._agent_connections.pop("dead-agent", None)

    @pytest.mark.asyncio
    async def test_connected_agent_count(self):
        initial = aq.connected_agent_count()

        class _MockWS:
            async def send_json(self, data): pass

        aq.register_agent("count-test", _MockWS())
        assert aq.connected_agent_count() == initial + 1
        aq.unregister_agent("count-test")
        assert aq.connected_agent_count() == initial


# ── POST /sessions/{id}/resolve ───────────────────────────────────────────────

class TestResolveSession:
    @pytest.mark.asyncio
    async def test_resolve_sets_is_resolved_flag(self, client):
        # Create a session via the API
        resp = await client.post("/sessions?district=bengaluru_urban&language=kn")
        assert resp.status_code == 200
        session_id = resp.json()["session_id"]

        resolve_resp = await client.post(
            f"/sessions/{session_id}/resolve",
            json={"agent_id": "agent-42"},
        )
        assert resolve_resp.status_code == 200
        assert resolve_resp.json()["ok"] is True

        # Fetch session and verify flag
        get_resp = await client.get(f"/sessions/{session_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["is_resolved"] is True

    @pytest.mark.asyncio
    async def test_resolve_audit_logged(self, client):
        resp = await client.post("/sessions?district=mysuru&language=kn")
        session_id = resp.json()["session_id"]

        await client.post(f"/sessions/{session_id}/resolve", json={"agent_id": "agent-5"})

        trail = await get_audit_trail(session_id)
        types = [e["event_type"] for e in trail]
        assert "session_resolved" in types

    @pytest.mark.asyncio
    async def test_resolve_removes_from_queue(self, client, clean_queue):
        resp = await client.post("/sessions?district=bengaluru_urban&language=kn")
        session_id = resp.json()["session_id"]

        # Manually push it onto the queue
        await aq.push_escalation(session_id, 0.8, "high_distress", "test", "bengaluru_urban", "kn", None)
        assert await aq.queue_length() == 1

        await client.post(f"/sessions/{session_id}/resolve", json={})
        result = await aq.get_queue(limit=100, offset=0)
        queued_ids = [r["session_id"] for r in result]
        assert session_id not in queued_ids

    @pytest.mark.asyncio
    async def test_resolve_nonexistent_session_404(self, client):
        resp = await client.post("/sessions/nonexistent-id/resolve", json={})
        assert resp.status_code == 404


# ── GET /sessions/{id}/full-context ──────────────────────────────────────────

class TestFullContext:
    @pytest.mark.asyncio
    async def test_full_context_shape(self, client):
        resp = await client.post("/sessions?district=mangaluru&language=kn")
        session_id = resp.json()["session_id"]

        ctx_resp = await client.get(f"/sessions/{session_id}/full-context")
        assert ctx_resp.status_code == 200
        body = ctx_resp.json()

        for field in (
            "session_id", "district", "dialect_tag", "detected_language",
            "verification_state", "clarification_count", "is_escalated",
            "is_resolved", "composite_confidence", "final_intent",
            "structured_intent", "transcript", "sentiment_timeline",
            "confidence_history", "audit_summary",
        ):
            assert field in body, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_full_context_nonexistent_session_404(self, client):
        resp = await client.get("/sessions/does-not-exist/full-context")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_full_context_structured_intent_when_none(self, client):
        resp = await client.post("/sessions?district=bengaluru_urban&language=kn")
        session_id = resp.json()["session_id"]

        ctx_resp = await client.get(f"/sessions/{session_id}/full-context")
        body = ctx_resp.json()
        # No turns yet → final_intent is None → structured_intent is None
        assert body["structured_intent"] is None


# ── POST /sessions/{id}/agent-correction ─────────────────────────────────────

class TestAgentCorrection:
    @pytest.mark.asyncio
    async def test_correction_returns_ok(self, client):
        resp = await client.post("/sessions?district=mysuru&language=kn")
        session_id = resp.json()["session_id"]

        corr_resp = await client.post(
            f"/sessions/{session_id}/agent-correction",
            json={"field": "intent", "value": "ration_card_status", "agent_id": "ag-1"},
        )
        assert corr_resp.status_code == 200
        body = corr_resp.json()
        assert body["ok"] is True
        assert body["field"] == "intent"

    @pytest.mark.asyncio
    async def test_correction_propagates_to_session_state(self, client):
        resp = await client.post("/sessions?district=mysuru&language=kn")
        session_id = resp.json()["session_id"]

        await client.post(
            f"/sessions/{session_id}/agent-correction",
            json={"field": "intent", "value": "road_damage"},
        )

        sess_resp = await client.get(f"/sessions/{session_id}")
        assert sess_resp.json()["final_intent"] == "road_damage"

    @pytest.mark.asyncio
    async def test_correction_audit_logged(self, client):
        resp = await client.post("/sessions?district=bengaluru_urban&language=kn")
        session_id = resp.json()["session_id"]

        await client.post(
            f"/sessions/{session_id}/agent-correction",
            json={"field": "intent", "value": "pension_issue"},
        )

        trail = await get_audit_trail(session_id)
        types = [e["event_type"] for e in trail]
        assert "agent_correction_applied" in types

    @pytest.mark.asyncio
    async def test_correction_feedback_loop_row_created(self, client):
        """Correction must create / update a VerifiedInteraction row in the DB."""
        from sqlalchemy import select
        from models.audit_model import VerifiedInteraction

        resp = await client.post("/sessions?district=bengaluru_urban&language=kn")
        session_id = resp.json()["session_id"]

        await client.post(
            f"/sessions/{session_id}/agent-correction",
            json={"field": "intent", "value": "water_connection_new"},
        )

        factory = _db.get_session_factory()
        async with factory() as db:
            result = await db.execute(
                select(VerifiedInteraction).where(VerifiedInteraction.session_id == session_id)
            )
            row = result.scalar_one_or_none()

        assert row is not None
        assert row.final_intent == "water_connection_new"

    @pytest.mark.asyncio
    async def test_correction_missing_field_400(self, client):
        resp = await client.post("/sessions?district=bengaluru_urban&language=kn")
        session_id = resp.json()["session_id"]

        bad_resp = await client.post(
            f"/sessions/{session_id}/agent-correction",
            json={"value": "road_damage"},  # missing field
        )
        assert bad_resp.status_code == 400
