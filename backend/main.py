"""
Samvaad-Setu — FastAPI Backend
WebSocket-driven voice pipeline: ASR → NLU → Sentiment → Verification → Escalation → TTS
"""
import json
import base64
import asyncio
from datetime import datetime, timezone
from typing import Optional, AsyncIterator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from config import settings, SUPPORTED_LANGUAGES
from models.session_model import SessionState, Turn, TurnSentiment, EscalationPacket
from services import asr, nlu, tts, sentiment, verification, escalation
from services import session_manager
from services.verification_engine import VerificationEngine
from services.confidence_scorer import build_score
from middleware.latency import LatencyMiddleware, track, get_stats
from services.audit_log import log_event, get_audit_trail
from services.feedback_loop import write_verified_interaction, record_agent_correction, export_jsonl
from services.agent_queue import (
    push_escalation, remove_from_queue, get_queue, queue_length,
    register_agent, unregister_agent, broadcast_escalation, connected_agent_count,
)
from services.intent_taxonomy import IntentTaxonomy

_taxonomy = IntentTaxonomy()

_verification_engine = VerificationEngine()

app = FastAPI(
    title="Samvaad-Setu API",
    description="Real-time multilingual voice assistant for Karnataka 1092 helpline",
    version="0.1.0",
)


@app.on_event("startup")
async def _startup():
    """Initialise DB engine on startup. Failures are non-fatal in mock mode."""
    try:
        import db as _db
        _db.init_db()
    except Exception as exc:
        print(f"[STARTUP] DB init failed (non-fatal in mock mode): {exc}")

app.add_middleware(LatencyMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── REST ENDPOINTS ────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    redis_status = await session_manager.health_check()
    return {"status": "ok", "mode": settings.environment, **redis_status}


@app.get("/health/latency")
async def health_latency():
    """Rolling p50/p95 latency (ms) per pipeline stage and HTTP route."""
    return {"stages": get_stats()}


@app.post("/sessions")
async def create_session(
    district: str = "default",
    language: str = "kn",
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    """Create a new call session. Returns session_id. Idempotent via Idempotency-Key header."""
    if language not in SUPPORTED_LANGUAGES:
        raise HTTPException(400, f"Unsupported language. Use: {list(SUPPORTED_LANGUAGES.keys())}")

    # Idempotency: return cached response for the same key within session TTL
    if idempotency_key:
        cached = await session_manager.get_idempotency(idempotency_key)
        if cached:
            return cached

    session = await session_manager.create_session(district=district, language=language)
    response = {"session_id": session.session_id, "district": district, "language": language}

    if idempotency_key:
        await session_manager.set_idempotency(idempotency_key, response)

    await log_event(
        session.session_id,
        "session_created",
        actor="system",
        payload={"district": district, "language": language},
    )
    return response


@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return session.model_dump()


@app.get("/sessions/{session_id}/escalation-packet")
async def get_escalation_packet(session_id: str):
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if not session.is_escalated:
        raise HTTPException(400, "Session has not been escalated")
    ticket = await nlu.generate_ticket_draft(session)
    return EscalationPacket(
        session_id=session.session_id,
        reason=session.escalation_reason,
        summary=session.escalation_summary,
        district=session.district,
        detected_language=session.detected_language,
        final_intent=session.final_intent,
        composite_confidence=session.composite_confidence,
        transcript=session.to_transcript_text(),
        sentiment_timeline=session.sentiment_timeline,
        ai_interpretation=session.turns[-1].ai_rephrasing if session.turns else "",
        ticket_draft=ticket,
    ).model_dump()


@app.get("/audit/{session_id}")
async def get_audit(session_id: str):
    """Full audit trail for a session — every state transition, oldest-first."""
    trail = await get_audit_trail(session_id)
    return {"session_id": session_id, "events": trail}


@app.post("/sessions/{session_id}/agent-correction")
async def agent_correction(session_id: str, body: dict):
    """
    Agent edits a field on the session record.
    Body: { "field": "intent", "value": "ration_card_status", "agent_id": "agent_42" }
    """
    field = body.get("field")
    value = body.get("value")
    agent_id = body.get("agent_id", "agent")

    if not field or value is None:
        raise HTTPException(400, "field and value are required")

    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    # Apply correction to session state
    if field == "intent":
        session.final_intent = value
        await session_manager.save_session(session)

    ok = await record_agent_correction(session_id, field=field, value=str(value), agent_id=agent_id)
    await log_event(
        session_id,
        "agent_correction_applied",
        actor="agent",
        payload={"field": field, "value": value, "agent_id": agent_id},
    )
    return {"ok": ok, "session_id": session_id, "field": field, "value": value}


@app.get("/sessions/{session_id}/full-context")
async def full_context(session_id: str):
    """Full session context for the agent dashboard."""
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    audit = await get_audit_trail(session_id)

    # Structured intent enriched with taxonomy metadata
    structured_intent = None
    if session.final_intent:
        structured_intent = {
            "intent_id": session.final_intent,
            "label_en": _taxonomy.get_label(session.final_intent, "en"),
            "label_kn": _taxonomy.get_label(session.final_intent, "kn"),
            "responsible_department": _taxonomy.get_responsible_department(session.final_intent),
            "escalation_priority": _taxonomy.get_escalation_priority(session.final_intent),
        }

    # Build structured transcript (turns without TTS audio to keep payload lean)
    transcript = [
        {
            "turn_id": t.turn_id,
            "speaker": t.speaker,
            "timestamp": t.timestamp.isoformat(),
            "raw_transcript": t.raw_transcript,
            "ai_rephrasing": t.ai_rephrasing,
            "intent": t.intent,
            "asr_confidence": t.asr_confidence,
            "sentiment": t.sentiment.model_dump() if t.sentiment else None,
            "verification_state": t.verification_state,
        }
        for t in session.turns
    ]

    return {
        "session_id": session.session_id,
        "created_at": session.created_at.isoformat(),
        "district": session.district,
        "dialect_tag": session.dialect_tag,
        "detected_language": session.detected_language,
        "verification_state": session.verification_state,
        "clarification_count": session.clarification_count,
        "is_escalated": session.is_escalated,
        "is_resolved": session.is_resolved,
        "escalation_reason": session.escalation_reason,
        "escalation_summary": session.escalation_summary,
        "composite_confidence": session.composite_confidence,
        "final_intent": session.final_intent,
        "structured_intent": structured_intent,
        "transcript": transcript,
        "sentiment_timeline": session.sentiment_timeline,
        "confidence_history": session.confidence_history,
        "audit_summary": audit[-10:],
    }


@app.get("/agent/queue")
async def agent_queue(limit: int = 20, offset: int = 0):
    """
    Escalated sessions sorted by priority: sentiment_intensity DESC, created_at ASC.
    Excludes resolved sessions.
    """
    if limit < 1 or limit > 100:
        raise HTTPException(400, "limit must be between 1 and 100")
    if offset < 0:
        raise HTTPException(400, "offset must be >= 0")

    entries = await get_queue(limit=limit, offset=offset)
    total = await queue_length()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": entries,
        "connected_agents": connected_agent_count(),
    }


@app.post("/sessions/{session_id}/resolve")
async def resolve_session(session_id: str, body: dict = {}):
    """Agent marks the session as resolved. Removes from queue and audit-logs."""
    agent_id = body.get("agent_id", "agent")

    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    session.is_resolved = True
    await session_manager.save_session(session)
    await remove_from_queue(session_id)
    await log_event(
        session_id, "session_resolved", actor="agent",
        payload={"agent_id": agent_id},
    )
    return {"ok": True, "session_id": session_id}


@app.get("/training-data/export")
async def export_training_data(format: str = "jsonl", since: Optional[str] = None):
    """Stream verified interactions as JSONL for retraining."""
    if format != "jsonl":
        raise HTTPException(400, "Only format=jsonl is supported")

    since_dt: Optional[datetime] = None
    if since:
        try:
            since_dt = datetime.fromisoformat(since)
        except ValueError:
            raise HTTPException(400, "since must be an ISO-8601 datetime string")

    async def _stream() -> AsyncIterator[str]:
        async for line in export_jsonl(since=since_dt):
            yield line

    return StreamingResponse(
        _stream(),
        media_type="application/x-ndjson",
        headers={"Content-Disposition": "attachment; filename=verified_interactions.jsonl"},
    )


# ─── AGENT WEBSOCKET ──────────────────────────────────────────────────────────

@app.websocket("/ws/agent/{agent_id}")
async def agent_ws(websocket: WebSocket, agent_id: str):
    """
    Real-time feed for the agent dashboard.

    SERVER → AGENT:
      { "type": "new_escalation", "packet": {...} }
      { "type": "queue_update", "total": N, "connected_agents": N }
      { "type": "pong" }

    AGENT → SERVER:
      { "type": "ping" }
    """
    await websocket.accept()
    register_agent(agent_id, websocket)

    # Send current queue snapshot on connect
    entries = await get_queue(limit=20, offset=0)
    total = await queue_length()
    try:
        await websocket.send_json({
            "type": "queue_snapshot",
            "total": total,
            "items": entries,
            "connected_agents": connected_agent_count(),
        })
    except Exception:
        pass

    try:
        async for raw_msg in websocket.iter_text():
            try:
                msg = json.loads(raw_msg)
            except json.JSONDecodeError:
                continue
            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        unregister_agent(agent_id)


# ─── WEBSOCKET VOICE PIPELINE ─────────────────────────────────────────────────

@app.websocket("/ws/{session_id}")
async def voice_pipeline(websocket: WebSocket, session_id: str):
    """
    WebSocket message protocol:
    
    CLIENT → SERVER:
      { "type": "audio", "data": "<base64 WAV>", "language": "kn", "district": "mysuru" }
      { "type": "verification", "data": "<citizen response text>" }
      { "type": "ping" }
    
    SERVER → CLIENT:
      { "type": "turn_update", "turn": {...}, "session": {...} }
      { "type": "escalation", "packet": {...} }
      { "type": "error", "message": "..." }
      { "type": "pong" }
    """
    await websocket.accept()
    session = await session_manager.get_session(session_id)

    if not session:
        await websocket.send_json({"type": "error", "message": "Session not found"})
        await websocket.close()
        return

    try:
        async for raw_msg in websocket.iter_text():
            print(f"[WS] Received message: {raw_msg[:100]}...")  # Debug log
            msg = json.loads(raw_msg)
            msg_type = msg.get("type")
            print(f"[WS] Message type: {msg_type}")  # Debug log

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            elif msg_type == "audio":
                print(f"[WS] Processing audio message...")  # Debug log
                await _handle_audio_turn(websocket, session, msg)
                await session_manager.save_session(session)

            elif msg_type in ("verification", "verification_response"):
                print(f"[WS] Processing verification message...")  # Debug log
                if msg_type == "verification_response":
                    await _handle_verification_response(websocket, session, msg)
                else:
                    await _handle_verification_turn(websocket, session, msg)
                await session_manager.save_session(session)

            elif msg_type == "agent_correction":
                print(f"[WS] Processing agent correction...")  # Debug log
                # Agent edits AI interpretation inline
                await _handle_agent_correction(websocket, session, msg)
                await session_manager.save_session(session)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        await session_manager.save_session(session)


async def _handle_audio_turn(websocket: WebSocket, session: SessionState, msg: dict):
    """Full pipeline: audio → ASR → NLU → Sentiment → Escalation check → TTS → respond."""
    audio_b64: str = msg.get("data", "")
    language:  str = msg.get("language", session.detected_language)
    district:  str = msg.get("district", session.district)

    print(f"[AUDIO] Language: {language}, District: {district}")
    print(f"[AUDIO] Audio data length: {len(audio_b64)}")

    session.detected_language = language
    session.district = district

    # Populate dialect_tag from district if not already set
    if not session.dialect_tag:
        from services.dialect_context import DialectContextProvider
        _dcp = DialectContextProvider()
        try:
            profile = _dcp.get_profile(district)
            session.dialect_tag = profile.dialect_tag
        except Exception:
            session.dialect_tag = district

    # Decode audio
    audio_bytes = base64.b64decode(audio_b64) if audio_b64 else b""
    print(f"[AUDIO] Decoded audio bytes: {len(audio_bytes)}")

    # ── 1. ASR ─────────────────────────────────────────────────────────────
    print("[ASR] Starting transcription...")
    async with track("asr"):
        asr_result = await asr.transcribe(audio_bytes, hint_language=language, district=district)
    print(f"[ASR] Result: {asr_result.transcript[:50]}... (confidence: {asr_result.confidence})")
    print(f"[ASR] Detected language: {asr_result.language}")

    # Update session language based on ASR detection
    if asr_result.language:
        session.detected_language = asr_result.language
        print(f"[SESSION] Updated language to: {asr_result.language}")

    # ── 2. NLU (Gemini) ────────────────────────────────────────────────────
    print(f"[NLU] Starting intent extraction for: {asr_result.transcript[:50]}...")
    async with track("nlu"):
        nlu_result = await nlu.extract_intent_and_rephrase(asr_result.transcript, session)
    print(f"[NLU] Result - Intent: {nlu_result.get('intent')}, Confidence: {nlu_result.get('intent_confidence')}")

    # ── 3. Sentiment ───────────────────────────────────────────────────────
    print(f"[SENTIMENT] Starting analysis...")
    async with track("sentiment"):
        sentiment_result = await sentiment.analyze(asr_result.transcript, audio_bytes, language)
    print(f"[SENTIMENT] Result - Label: {sentiment_result.label}, Intensity: {sentiment_result.intensity}")

    # ── 4. Build citizen turn ──────────────────────────────────────────────
    citizen_turn = Turn(
        speaker="citizen",
        raw_transcript=asr_result.transcript,
        asr_confidence=asr_result.confidence,
        detected_language=asr_result.language,
        intent=nlu_result.get("intent"),
        intent_entropy=nlu_result.get("intent_entropy", 0.0),
        sentiment=TurnSentiment(
            label=sentiment_result.label,
            intensity=sentiment_result.intensity,
            prosodic_component=sentiment_result.prosodic_component,
            text_component=sentiment_result.text_component,
        ),
        ai_rephrasing=nlu_result.get("rephrasing", ""),
    )
    session.add_turn(citizen_turn)
    session.final_intent = citizen_turn.intent
    sentiment_label = citizen_turn.sentiment.label if citizen_turn.sentiment else "unknown"
    print(f"[TURN] Added citizen turn - Intent: {citizen_turn.intent}, Sentiment: {sentiment_label}")

    # ── 5. Verification prompt (citizen must confirm before intent is committed) ──
    print(f"[VERIFICATION] Generating dialect-aware verification prompt...")
    async with track("verification"):
        verification_prompt_text = _verification_engine.generate_verification_prompt(
            intent=citizen_turn.intent or "other_grievance",
            entities=nlu_result.get("entities", {}),
            language=language,
            district=district,
        )
        session.verification_state = "pending"
    print(f"[VERIFICATION] Prompt: {verification_prompt_text}")

    # ── 6. Escalation check ────────────────────────────────────────────────
    print(f"[ESCALATION] Evaluating escalation...")
    esc_decision = escalation.evaluate(
        session,
        asr_confidence=asr_result.confidence,
        intent_entropy=citizen_turn.intent_entropy,
        sentiment=sentiment_result,
    )
    session.composite_confidence = 1.0 - esc_decision.composite_score
    print(f"[ESCALATION] Should escalate: {esc_decision.should_escalate}, Composite confidence: {session.composite_confidence}")

    # ── 7. Build AI verification turn ──────────────────────────────────────
    verification_text = (
        nlu_result.get("rephrasing", "") + " " +
        nlu_result.get("verification_prompt", "")
    )
    print(f"[TTS] Synthesizing verification text: {verification_text[:100]}...")

    tts_audio = ""
    try:
        async with track("tts"):
            tts_audio = await tts.synthesize(
                verification_text, language=language,
                sentiment_label=sentiment_result.label,
            )
        print(f"[TTS] Synthesis successful, audio length: {len(tts_audio)}")
    except Exception as e:
        print(f"[TTS] Synthesis failed: {e}")
        print(f"[TTS] Continuing without audio - text will still be displayed")

    ai_turn = Turn(
        speaker="ai",
        raw_transcript=verification_text,
        ai_rephrasing=nlu_result.get("rephrasing", ""),
        tts_audio_b64=tts_audio,
        intent=citizen_turn.intent,
    )
    session.add_turn(ai_turn)
    print(f"[TURN] Added AI turn")

    # ── 7. Send response to client ─────────────────────────────────────────
    # Build a standalone ConfidenceScore for this turn (independent of the
    # EscalationDecision so the agent dashboard always gets the full breakdown)
    turn_confidence = build_score(
        asr_conf=asr_result.confidence,
        intent_entropy=citizen_turn.intent_entropy,
        sentiment_intensity=sentiment_result.intensity,
        clarification_count=session.clarification_count,
    )

    # Append to per-session confidence history (capped at 20)
    session.confidence_history.append({
        "turn_id": citizen_turn.turn_id,
        "timestamp": citizen_turn.timestamp.isoformat(),
        "composite_score": turn_confidence.composite_score,
        "asr_confidence": turn_confidence.asr_confidence,
        "intent_entropy": turn_confidence.intent_entropy,
        "sentiment_intensity": turn_confidence.sentiment_intensity,
        "clarification_count": turn_confidence.clarification_count,
    })
    if len(session.confidence_history) > 20:
        session.confidence_history = session.confidence_history[-20:]

    print(f"[WS] Sending turn_update to client...")
    await websocket.send_json({
        "type": "turn_update",
        "citizen_turn": citizen_turn.model_dump(mode="json"),
        "ai_turn": ai_turn.model_dump(mode="json"),
        "session": {
            "session_id": session.session_id,
            "composite_confidence": session.composite_confidence,
            "sentiment_timeline": session.sentiment_timeline,
            "is_escalated": session.is_escalated,
            "clarification_count": session.clarification_count,
            "verification_state": session.verification_state,
            "district": session.district,
            "current_language": session.detected_language,
        },
        "nlu": {
            "intent": nlu_result.get("intent"),
            "intent_confidence": nlu_result.get("intent_confidence"),
            "structured_summary": nlu_result.get("structured_summary"),
        },
        "confidence_score": turn_confidence.model_dump(),
        "escalation": {
            "composite_score": esc_decision.composite_score,
            "explanation": esc_decision.explanation,
        },
        "mock_mode": settings.environment == "mock",
    })
    print(f"[WS] turn_update sent successfully")

    # Send dedicated verification_prompt so the UI can render the confirm/deny buttons
    await websocket.send_json({
        "type": "verification_prompt",
        "text": verification_prompt_text,
        "language": language,
        "district": district,
        "session_id": session.session_id,
    })
    print(f"[WS] verification_prompt sent")
    
    # ── 8. Handle escalation if needed ─────────────────────────────────────
    if esc_decision.should_escalate:
        print(f"[ESCALATION] Escalating to human agent after sending turns...")
        await _do_escalation(websocket, session, esc_decision, language)
        return


async def _handle_verification_turn(websocket: WebSocket, session: SessionState, msg: dict):
    """Process citizen's yes/no/partial confirmation of AI rephrasing."""
    response_text: str = msg.get("data", "")
    language = session.detected_language

    state = verification.classify_verification_response(response_text, language)

    # Update last citizen turn's verification state
    citizen_turns = session.citizen_turns()
    if citizen_turns:
        citizen_turns[-1].verification_state = state

    if state == "correct":
        # Confirmed — acknowledge and move to ticket creation
        last_intent = session.final_intent or "other_grievance"
        ack_text = verification.get_acknowledgment(language, last_intent)
        tts_audio = await tts.synthesize(ack_text, language=language)

        ai_turn = Turn(speaker="ai", raw_transcript=ack_text, tts_audio_b64=tts_audio)
        session.add_turn(ai_turn)

        await websocket.send_json({
            "type": "verification_result",
            "state": state,
            "ai_response": ack_text,
            "tts_audio_b64": tts_audio,
            "session_id": session.session_id,
        })

    elif state in ("partially_correct", "incorrect"):
        session.clarification_count += 1

        # Check if we've hit max clarifications
        if session.clarification_count >= settings.max_clarification_turns:
            # Escalate via repeated clarification
            class _FakeSentiment:
                label, score = "confusion", 0.5
                prosodic_score = text_score = 0.0

            from services.escalation import EscalationDecision, EscalationReason
            fake_esc = EscalationDecision(
                should_escalate=True,
                reason="repeated_clarification",
                composite_score=0.8,
                explanation=f"Failed to verify after {session.clarification_count} attempts.",
            )
            await _do_escalation(websocket, session, fake_esc, language)
            return

        clarify_text = verification.get_clarification_prompt(language, session.clarification_count)
        tts_audio = await tts.synthesize(clarify_text, language=language)

        ai_turn = Turn(speaker="ai", raw_transcript=clarify_text, tts_audio_b64=tts_audio)
        session.add_turn(ai_turn)

        await websocket.send_json({
            "type": "verification_result",
            "state": state,
            "ai_response": clarify_text,
            "tts_audio_b64": tts_audio,
            "clarification_count": session.clarification_count,
        })


async def _handle_verification_response(websocket: WebSocket, session: SessionState, msg: dict):
    """
    Handle a structured verification_response message from the frontend.
    Uses VerificationEngine to drive the three-branch state machine.
    msg: { "type": "verification_response", "state": "correct"|"partial"|"incorrect", "correction_text": str }
    """
    state: str = msg.get("state", "incorrect")
    correction_text: Optional[str] = msg.get("correction_text")
    language = session.detected_language

    print(f"[VERIFICATION] Response: state={state}, correction_text={correction_text}")

    result = _verification_engine.process_verification_response(session, state, correction_text)
    action = result["action"]

    if action == "confirmed":
        ack_text = verification.get_acknowledgment(language, session.final_intent or "other_grievance")
        tts_audio = ""
        try:
            tts_audio = await tts.synthesize(ack_text, language=language)
        except Exception:
            pass
        ai_turn = Turn(speaker="ai", raw_transcript=ack_text, tts_audio_b64=tts_audio)
        session.add_turn(ai_turn)
        await websocket.send_json({
            "type": "verification_result",
            "state": "confirmed",
            "ai_response": ack_text,
            "tts_audio_b64": tts_audio,
            "session_id": session.session_id,
        })
        print(f"[VERIFICATION] Confirmed — intent committed: {session.final_intent}")
        await log_event(
            session.session_id, "verification_confirmed", actor="citizen",
            payload={"intent": session.final_intent, "clarification_count": session.clarification_count},
        )
        await write_verified_interaction(session)

    elif action == "clarify":
        clarify_text = result["clarification_prompt"]
        tts_audio = ""
        try:
            tts_audio = await tts.synthesize(clarify_text, language=language)
        except Exception:
            pass
        ai_turn = Turn(speaker="ai", raw_transcript=clarify_text, tts_audio_b64=tts_audio)
        session.add_turn(ai_turn)
        await websocket.send_json({
            "type": "verification_result",
            "state": "partial",
            "ai_response": clarify_text,
            "tts_audio_b64": tts_audio,
            "clarification_count": session.clarification_count,
        })
        print(f"[VERIFICATION] Clarification #{session.clarification_count} sent")
        await log_event(
            session.session_id, "verification_partial", actor="citizen",
            payload={"clarification_count": session.clarification_count},
        )

    elif action == "escalate":
        from services.escalation import EscalationDecision
        fake_esc = EscalationDecision(
            should_escalate=True,
            reason="repeated_clarification",
            composite_score=0.8,
            explanation=f"Verification failed after {session.clarification_count} attempts.",
        )
        await _do_escalation(websocket, session, fake_esc, language)
        print(f"[VERIFICATION] Escalated after repeated clarification failures")


async def _handle_agent_correction(websocket: WebSocket, session: SessionState, msg: dict):
    """Agent corrects AI interpretation inline — feeds back to learning loop."""
    turn_id: str = msg.get("turn_id", "")
    correction: str = msg.get("correction", "")
    corrected_intent: Optional[str] = msg.get("intent")

    # Find and update the turn
    for turn in session.turns:
        if turn.turn_id == turn_id:
            turn.ai_rephrasing = correction
            if corrected_intent:
                turn.intent = corrected_intent
                session.final_intent = corrected_intent
            break

    payload: dict = {"turn_id": turn_id, "correction": correction}
    if corrected_intent:
        payload["intent"] = corrected_intent
        await record_agent_correction(session.session_id, field="intent", value=corrected_intent)

    await log_event(session.session_id, "agent_correction_applied", actor="agent", payload=payload)

    await websocket.send_json({
        "type": "agent_correction_ack",
        "turn_id": turn_id,
        "session_id": session.session_id,
    })


async def _do_escalation(websocket: WebSocket, session: SessionState, esc_decision, language: str):
    """Execute escalation: generate summary, build packet, notify client."""
    print(f"[ESCALATION] _do_escalation called - Reason: {esc_decision.reason}")
    session.is_escalated = True
    session.escalation_reason = esc_decision.reason

    # Generate one-line summary for agent
    print(f"[ESCALATION] Generating escalation summary...")
    session.escalation_summary = await nlu.generate_escalation_summary(session)
    print(f"[ESCALATION] Summary: {session.escalation_summary}")

    # Speak escalation message to citizen
    esc_msg = escalation.build_escalation_message(esc_decision.reason, language)
    tts_audio = await tts.synthesize(esc_msg, language=language, sentiment_label="calm")

    ai_turn = Turn(speaker="ai", raw_transcript=esc_msg, tts_audio_b64=tts_audio)
    session.add_turn(ai_turn)

    # Build ticket draft
    ticket = await nlu.generate_ticket_draft(session)

    packet = EscalationPacket(
        session_id=session.session_id,
        reason=session.escalation_reason,
        summary=session.escalation_summary,
        district=session.district,
        detected_language=session.detected_language,
        final_intent=session.final_intent,
        composite_confidence=session.composite_confidence,
        transcript=session.to_transcript_text(),
        sentiment_timeline=session.sentiment_timeline,
        ai_interpretation=session.turns[-2].ai_rephrasing if len(session.turns) >= 2 else "",
        ticket_draft=ticket,
    )

    await log_event(
        session.session_id, "escalation_triggered", actor="system",
        payload={
            "reason": esc_decision.reason,
            "composite_confidence": session.composite_confidence,
            "clarification_count": session.clarification_count,
            "final_intent": session.final_intent,
        },
    )

    # Push to priority queue and notify all connected agent dashboards
    last_sentiment = session.sentiment_timeline[-1] if session.sentiment_timeline else {}
    sentiment_intensity = last_sentiment.get("intensity", 0.5)
    await push_escalation(
        session_id=session.session_id,
        sentiment_intensity=sentiment_intensity,
        reason=session.escalation_reason,
        summary=session.escalation_summary,
        district=session.district,
        language=session.detected_language,
        final_intent=session.final_intent,
        created_at=session.created_at,
    )
    await broadcast_escalation(packet.model_dump(mode="json"))

    print(f"[ESCALATION] Sending escalation packet to client...")
    await websocket.send_json({
        "type": "escalation",
        "packet": packet.model_dump(mode="json"),
        "tts_audio_b64": tts_audio,
        "escalation_message": esc_msg,
    })
    print(f"[ESCALATION] Escalation packet sent successfully")
