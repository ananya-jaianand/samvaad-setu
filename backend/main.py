"""
Samvaad-Setu — FastAPI Backend
WebSocket-driven voice pipeline: ASR → NLU → Sentiment → Verification → Escalation → TTS
"""
import json
import base64
import asyncio
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings, SUPPORTED_LANGUAGES
from models.session_model import SessionState, Turn, TurnSentiment, EscalationPacket
from services import asr, nlu, tts, sentiment, verification, escalation
from services import session_manager

app = FastAPI(
    title="Samvaad-Setu API",
    description="Real-time multilingual voice assistant for Karnataka 1092 helpline",
    version="0.1.0",
)

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


@app.post("/sessions")
async def create_session(district: str = "default", language: str = "kn"):
    """Create a new call session. Returns session_id."""
    if language not in SUPPORTED_LANGUAGES:
        raise HTTPException(400, f"Unsupported language. Use: {list(SUPPORTED_LANGUAGES.keys())}")
    session = await session_manager.create_session(district=district, language=language)
    return {"session_id": session.session_id, "district": district, "language": language}


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

            elif msg_type == "verification":
                print(f"[WS] Processing verification message...")  # Debug log
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

    # Decode audio
    audio_bytes = base64.b64decode(audio_b64) if audio_b64 else b""
    print(f"[AUDIO] Decoded audio bytes: {len(audio_bytes)}")

    # ── 1. ASR ─────────────────────────────────────────────────────────────
    print("[ASR] Starting transcription...")
    asr_result = await asr.transcribe(audio_bytes, hint_language=language, district=district)
    print(f"[ASR] Result: {asr_result.transcript[:50]}... (confidence: {asr_result.confidence})")
    print(f"[ASR] Detected language: {asr_result.language}")
    
    # Update session language based on ASR detection
    if asr_result.language:
        session.detected_language = asr_result.language
        print(f"[SESSION] Updated language to: {asr_result.language}")

    # ── 2. NLU (Gemini) ────────────────────────────────────────────────────
    print(f"[NLU] Starting intent extraction for: {asr_result.transcript[:50]}...")
    nlu_result = await nlu.extract_intent_and_rephrase(asr_result.transcript, session)
    print(f"[NLU] Result - Intent: {nlu_result.get('intent')}, Confidence: {nlu_result.get('intent_confidence')}")

    # ── 3. Sentiment ───────────────────────────────────────────────────────
    print(f"[SENTIMENT] Starting analysis...")
    sentiment_result = await sentiment.analyze(asr_result.transcript, audio_bytes, language)
    print(f"[SENTIMENT] Result - Label: {sentiment_result.label}, Score: {sentiment_result.score}")

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
            score=sentiment_result.score,
            prosodic_score=sentiment_result.prosodic_score,
            text_score=sentiment_result.text_score,
        ),
        ai_rephrasing=nlu_result.get("rephrasing", ""),
    )
    session.add_turn(citizen_turn)
    session.final_intent = citizen_turn.intent
    sentiment_label = citizen_turn.sentiment.label if citizen_turn.sentiment else "unknown"
    print(f"[TURN] Added citizen turn - Intent: {citizen_turn.intent}, Sentiment: {sentiment_label}")

    # ── 5. Escalation check ────────────────────────────────────────────────
    print(f"[ESCALATION] Evaluating escalation...")
    esc_decision = escalation.evaluate(
        session,
        asr_confidence=asr_result.confidence,
        intent_entropy=citizen_turn.intent_entropy,
        sentiment=sentiment_result,
    )
    session.composite_confidence = 1.0 - esc_decision.composite_score
    print(f"[ESCALATION] Should escalate: {esc_decision.should_escalate}, Composite confidence: {session.composite_confidence}")

    # ── 6. Build AI verification turn (or escalation message) ─────────────
    verification_text = (
        nlu_result.get("rephrasing", "") + " " +
        nlu_result.get("verification_prompt", "")
    )
    print(f"[TTS] Synthesizing verification text: {verification_text[:100]}...")
    
    # Try TTS synthesis, but don't fail if it errors (e.g., unsupported language)
    tts_audio = ""
    try:
        tts_audio = await tts.synthesize(
            verification_text, language=language,
            sentiment_label=sentiment_result.label,
        )
        print(f"[TTS] Synthesis successful, audio length: {len(tts_audio)}")
    except Exception as e:
        print(f"[TTS] Synthesis failed: {e}")
        print(f"[TTS] Continuing without audio - text will still be displayed")
        # Continue without audio - the text will still be displayed in UI

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
            "district": session.district,
            "current_language": session.detected_language,
        },
        "nlu": {
            "intent": nlu_result.get("intent"),
            "intent_confidence": nlu_result.get("intent_confidence"),
            "structured_summary": nlu_result.get("structured_summary"),
        },
        "escalation": {
            "composite_score": esc_decision.composite_score,
            "explanation": esc_decision.explanation,
        },
        "mock_mode": settings.environment == "mock",
    })
    print(f"[WS] turn_update sent successfully")
    
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

    # TODO: write (original, correction) pair to labeled dataset for retraining

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

    print(f"[ESCALATION] Sending escalation packet to client...")
    await websocket.send_json({
        "type": "escalation",
        "packet": packet.model_dump(mode="json"),
        "tts_audio_b64": tts_audio,
        "escalation_message": esc_msg,
    })
    print(f"[ESCALATION] Escalation packet sent successfully")
