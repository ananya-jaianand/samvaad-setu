"""
Agent Queue — manages the escalation priority queue, citizen/agent WebSocket
registries, and the all-sessions map (used by the agent dashboard to show
every active call, not just escalated ones).
"""
import json
from datetime import datetime, timezone
from typing import Optional
from fastapi import WebSocket


# ── Agent WebSocket registry ──────────────────────────────────────────────────

_agent_connections: dict[str, WebSocket] = {}


def register_agent(agent_id: str, ws: WebSocket) -> None:
    _agent_connections[agent_id] = ws


def unregister_agent(agent_id: str) -> None:
    _agent_connections.pop(agent_id, None)


async def broadcast_escalation(packet: dict) -> None:
    dead: list[str] = []
    for agent_id, ws in list(_agent_connections.items()):
        try:
            await ws.send_json({"type": "new_escalation", "packet": packet})
        except Exception:
            dead.append(agent_id)
    for agent_id in dead:
        _agent_connections.pop(agent_id, None)


async def broadcast_to_agents(payload: dict) -> None:
    """Generic fan-out to all connected agent dashboards."""
    dead: list[str] = []
    for agent_id, ws in list(_agent_connections.items()):
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(agent_id)
    for agent_id in dead:
        _agent_connections.pop(agent_id, None)


def connected_agent_count() -> int:
    return len(_agent_connections)


# ── Citizen WebSocket registry ────────────────────────────────────────────────

_citizen_connections: dict[str, WebSocket] = {}


def register_citizen(session_id: str, ws: WebSocket) -> None:
    _citizen_connections[session_id] = ws


def unregister_citizen(session_id: str) -> None:
    _citizen_connections.pop(session_id, None)


async def send_to_citizen(session_id: str, payload: dict) -> bool:
    ws = _citizen_connections.get(session_id)
    if not ws:
        return False
    try:
        await ws.send_json(payload)
        return True
    except Exception:
        _citizen_connections.pop(session_id, None)
        return False


# ── Active sessions (all sessions, not just escalated) ───────────────────────

_active_sessions: dict[str, dict] = {}


def push_active_session(
    session_id: str,
    district: str,
    language: str,
    sentiment: str = "calm",
    sentiment_intensity: float = 0.3,
    summary: str = "",
    reason: str = "active",
    final_intent: Optional[str] = None,
    created_at: Optional[datetime] = None,
    is_escalated: bool = False,
) -> None:
    existing = _active_sessions.get(session_id, {})
    _active_sessions[session_id] = {
        "session_id": session_id,
        "district": district,
        "language": language,
        "sentiment": sentiment,
        "sentiment_intensity": sentiment_intensity,
        "summary": summary or existing.get("summary", ""),
        "reason": reason,
        "final_intent": final_intent or existing.get("final_intent", "other_grievance"),
        "created_at": existing.get("created_at") or (created_at or datetime.now(timezone.utc)).isoformat(),
        "is_escalated": is_escalated,
    }


def remove_active_session(session_id: str) -> None:
    _active_sessions.pop(session_id, None)


def get_active_sessions(limit: int = 20, offset: int = 0) -> list[dict]:
    """Escalated sessions first (priority DESC), then active sessions (time ASC)."""
    escalated = sorted(
        [s for s in _active_sessions.values() if s.get("is_escalated")],
        key=lambda s: (-s["sentiment_intensity"], s["created_at"]),
    )
    active = sorted(
        [s for s in _active_sessions.values() if not s.get("is_escalated")],
        key=lambda s: s["created_at"],
    )
    return (escalated + active)[offset: offset + limit]


def total_active_sessions() -> int:
    return len(_active_sessions)


# ── Escalation queue storage ──────────────────────────────────────────────────

_QUEUE_KEY = "escalation_queue"
_META_PREFIX = "escalation_meta:"
_memory_queue: list[dict] = []


def _meta_key(session_id: str) -> str:
    return f"{_META_PREFIX}{session_id}"


async def push_escalation(
    session_id: str,
    sentiment_intensity: float,
    reason: str,
    summary: str,
    district: str,
    language: str,
    final_intent: Optional[str],
    created_at: Optional[datetime] = None,
    sentiment: Optional[str] = None,
) -> None:
    meta = {
        "session_id": session_id,
        "sentiment_intensity": sentiment_intensity,
        "sentiment": sentiment or "calm",
        "reason": reason,
        "summary": summary,
        "district": district,
        "language": language,
        "final_intent": final_intent or "other_grievance",
        "created_at": (created_at or datetime.now(timezone.utc)).isoformat(),
        "is_escalated": True,
    }

    # Keep the all-sessions map in sync
    push_active_session(
        session_id=session_id,
        district=district,
        language=language,
        sentiment=sentiment or "calm",
        sentiment_intensity=sentiment_intensity,
        summary=summary,
        reason=reason,
        final_intent=final_intent,
        is_escalated=True,
    )

    try:
        from services.session_manager import _redis_client, _use_redis
        if _use_redis and _redis_client:
            pipe = _redis_client.pipeline()
            pipe.zadd(_QUEUE_KEY, {session_id: sentiment_intensity})
            pipe.set(_meta_key(session_id), json.dumps(meta))
            await pipe.execute()
            return
    except Exception as exc:
        print(f"[QUEUE] Redis push failed: {exc}")

    _memory_queue[:] = [e for e in _memory_queue if e["session_id"] != session_id]
    _memory_queue.append(meta)
    _memory_queue.sort(key=lambda e: (-e["sentiment_intensity"], e["created_at"]))


async def remove_from_queue(session_id: str) -> None:
    remove_active_session(session_id)
    try:
        from services.session_manager import _redis_client, _use_redis
        if _use_redis and _redis_client:
            pipe = _redis_client.pipeline()
            pipe.zrem(_QUEUE_KEY, session_id)
            pipe.delete(_meta_key(session_id))
            await pipe.execute()
            return
    except Exception as exc:
        print(f"[QUEUE] Redis remove failed: {exc}")

    _memory_queue[:] = [e for e in _memory_queue if e["session_id"] != session_id]


async def get_queue(limit: int = 20, offset: int = 0) -> list[dict]:
    """Return all active sessions (escalated first, then active)."""
    return get_active_sessions(limit=limit, offset=offset)


async def queue_length() -> int:
    return total_active_sessions()
