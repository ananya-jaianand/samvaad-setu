"""
Agent Queue — manages the escalation priority queue and the registry of
connected agent WebSockets.

Queue storage: Redis sorted set `escalation_queue` (score = sentiment_intensity,
higher = higher priority). Metadata stored in Redis hashes. Falls back to an
in-memory sorted list when Redis is unavailable.

Agent notifications: module-level dict of live agent WebSocket connections.
When a new escalation fires, `broadcast_escalation` fans out to all agents.
"""
import json
import asyncio
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
    """Fan-out an escalation event to all connected agent dashboards."""
    dead: list[str] = []
    for agent_id, ws in list(_agent_connections.items()):
        try:
            await ws.send_json({"type": "new_escalation", "packet": packet})
        except Exception:
            dead.append(agent_id)
    for agent_id in dead:
        _agent_connections.pop(agent_id, None)


def connected_agent_count() -> int:
    return len(_agent_connections)


# ── Escalation queue storage ──────────────────────────────────────────────────

_QUEUE_KEY = "escalation_queue"
_META_PREFIX = "escalation_meta:"

# In-memory fallback (mirrors the Redis sorted set)
_memory_queue: list[dict] = []   # list of meta dicts, maintained sorted


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
    """Add or update an escalated session in the priority queue."""
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
    }

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

    # Memory fallback — keep sorted by (sentiment_intensity DESC, created_at ASC)
    _memory_queue[:] = [e for e in _memory_queue if e["session_id"] != session_id]
    _memory_queue.append(meta)
    _memory_queue.sort(key=lambda e: (-e["sentiment_intensity"], e["created_at"]))


async def remove_from_queue(session_id: str) -> None:
    """Remove a session from the queue when resolved or handled."""
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
    """
    Return escalated sessions sorted by sentiment_intensity DESC, created_at ASC.
    Excludes resolved sessions.
    """
    try:
        from services.session_manager import _redis_client, _use_redis
        if _use_redis and _redis_client:
            # ZREVRANGE gives highest score first
            members = await _redis_client.zrevrange(_QUEUE_KEY, 0, -1, withscores=True)
            metas: list[dict] = []
            for member, score in members:
                raw = await _redis_client.get(_meta_key(member))
                if raw:
                    metas.append(json.loads(raw))

            # Stable sort: score DESC already, break ties by created_at ASC
            metas.sort(key=lambda e: (-e["sentiment_intensity"], e["created_at"]))
            return metas[offset: offset + limit]
    except Exception as exc:
        print(f"[QUEUE] Redis get failed: {exc}")

    return _memory_queue[offset: offset + limit]


async def queue_length() -> int:
    try:
        from services.session_manager import _redis_client, _use_redis
        if _use_redis and _redis_client:
            return await _redis_client.zcard(_QUEUE_KEY)
    except Exception:
        pass
    return len(_memory_queue)
