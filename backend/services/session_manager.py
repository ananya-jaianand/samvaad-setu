"""
Session Manager — Redis-backed session state for voice calls.
Each session maps to a SessionState object, serialized as JSON.
Falls back to in-memory dict if Redis is unavailable (dev mode).
"""
import json
from typing import Optional
from datetime import timedelta
from models.session_model import SessionState
from config import settings

_memory_store: dict[str, dict] = {}  # fallback when Redis is down

try:
    import redis.asyncio as aioredis
    _redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    _use_redis = True
except Exception:
    _redis_client = None
    _use_redis = False

SESSION_TTL = timedelta(minutes=settings.max_session_minutes)


async def create_session(district: str = "default", language: str = "kn") -> SessionState:
    session = SessionState(district=district, detected_language=language)
    await save_session(session)
    return session


async def get_session(session_id: str) -> Optional[SessionState]:
    if _use_redis and _redis_client:
        try:
            data = await _redis_client.get(f"session:{session_id}")
            if data:
                return SessionState(**json.loads(data))
        except Exception:
            pass

    # Fallback to memory
    data = _memory_store.get(session_id)
    return SessionState(**data) if data else None


async def save_session(session: SessionState) -> None:
    serialized = session.model_dump_json()

    if _use_redis and _redis_client:
        try:
            await _redis_client.setex(
                f"session:{session.session_id}",
                int(SESSION_TTL.total_seconds()),
                serialized,
            )
            return
        except Exception:
            pass

    _memory_store[session.session_id] = json.loads(serialized)


async def delete_session(session_id: str) -> None:
    if _use_redis and _redis_client:
        try:
            await _redis_client.delete(f"session:{session_id}")
        except Exception:
            pass
    _memory_store.pop(session_id, None)


async def health_check() -> dict:
    status = {"redis": "disconnected", "memory_sessions": len(_memory_store)}
    if _use_redis and _redis_client:
        try:
            await _redis_client.ping()
            status["redis"] = "connected"
        except Exception:
            pass
    return status
