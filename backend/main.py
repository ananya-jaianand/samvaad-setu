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
    push_active_session, remove_active_session,
    register_citizen, unregister_citizen, send_to_citizen, broadcast_to_agents,
)
from services.intent_taxonomy import IntentTaxonomy
from services import ticket_service

_taxonomy = IntentTaxonomy()

_verification_engine = VerificationEngine()

# ─── FAST-PATH SCENARIO DATA (Bengaluru demo) ─────────────────────────────────
# 5 scripted flows × 5 citizen turns. After ASR, if transcript keywords match
# the expected next turn, skip NLU+sentiment+TTS synthesis and serve cached data.
# Two scenarios (kn_bescom, hi_water) contain PII to demo redaction.

_SS: dict[str, list[dict]] = {
    # ── S1: Kannada — BESCOM billing (PII: phone number in turn 2) ───────────
    "kn_bescom": [
        {"kw": ["ಬೆಸ್ಕಾಂ", "ಬಿಲ್"],
         "tx": "ನಮ್ಮ ಮನೆಗೆ ಬೆಸ್ಕಾಂ ಬಿಲ್ ತಪ್ಪಾಗಿ ಬಂದಿದೆ, ತುಂಬಾ ಜಾಸ್ತಿ ಆಗಿದೆ",
         "rs": "ಬೆಸ್ಕಾಂ ಬಿಲ್ ಬಗ್ಗೆ ದೂರು ಕೊಡ್ತಿದ್ದೀರಾ. ನಿಮ್ಮ ಸರ್ವೀಸ್ ಕನೆಕ್ಷನ್ ನಂಬರ್ ಅಥವಾ ರಿಜಿಸ್ಟರ್ ಆದ ಮೊಬೈಲ್ ನಂಬರ್ ಹೇಳ್ತೀರಾ?",
         "intent": "bescom_billing", "sl": "neutral", "si": 0.30, "conf": 0.85},
        {"kw": ["ಕನೆಕ್ಷನ್", "1234"],
         "tx": "ನಮ್ಮ ಸರ್ವೀಸ್ ಕನೆಕ್ಷನ್ ನಂಬರ್ 1234567890",
         "rs": "ಧನ್ಯವಾದ. ಕಳೆದ ತಿಂಗಳ ಬಿಲ್ ಎಷ್ಟು ಜಾಸ್ತಿ ಬಂದಿದೆ ಅಂತ ಹೇಳ್ತೀರಾ?",
         "intent": "bescom_billing", "sl": "neutral", "si": 0.25, "conf": 0.88},
        {"kw": ["ಯೂನಿಟ್", "9845"],
         "tx": "ಸಾಮಾನ್ಯ 80 ಯೂನಿಟ್ ಬರ್ತಿತ್ತು, ಈ ತಿಂಗಳ 320 ಆಗಿದೆ. ಮೊಬೈಲ್ 9845012345",
         "rs": "ಮೀಟರ್ ರೀಡಿಂಗ್ ತಪ್ಪಾಗಿರಬಹುದು. ನಿಮ್ಮ ಮೊಬೈಲ್ PHONE_1 ಆಗಿ ದಾಖಲಾಗಿದೆ. ಬಿಲ್ ರಿವಿಷನ್ ದೂರು ದಾಖಲಿಸ್ತೀನಿ.",
         "intent": "bescom_billing", "sl": "concerned", "si": 0.55, "conf": 0.79, "pii": True},
        {"kw": ["ಯಾವಾಗ", "ಸರಿ"],
         "tx": "ಯಾವಾಗ ಸರಿ ಆಗ್ತದೆ?",
         "rs": "7 ಕೆಲಸದ ದಿನಗಳಲ್ಲಿ ಬೆಸ್ಕಾಂ ಇನ್ಸ್ಪೆಕ್ಷನ್ ತಂಡ ಭೇಟಿ ಕೊಡ್ತಾರೆ. ದೂರು ಸಂಖ್ಯೆ BLR-ELEC-2024-00891 SMS ಆಗ್ತದೆ.",
         "intent": "bescom_billing", "sl": "neutral", "si": 0.25, "conf": 0.91},
        {"kw": ["ಧನ್ಯವಾದ"],
         "tx": "ಸರಿ, ಧನ್ಯವಾದ",
         "rs": "ದೂರು ದಾಖಲಾಗಿದೆ. ಟಿಕೆಟ್ 1092-BLR-2024-00891. ಇನ್ನೇನಾದರೂ ಸಹಾಯ ಬೇಕೇ?",
         "intent": "bescom_billing", "sl": "calm", "si": 0.15, "conf": 0.94},
    ],
    # ── S2: Kannada — ration card name correction ────────────────────────────
    "kn_ration": [
        {"kw": ["ರೇಷನ್", "ಕಾರ್ಡ್", "ಹೆಸರು"],
         "tx": "ನಮ್ಮ ರೇಷನ್ ಕಾರ್ಡ್ ನಲ್ಲಿ ಹೆಸರು ತಪ್ಪಾಗಿ ಇದೆ, ಸರಿ ಮಾಡಬೇಕು",
         "rs": "ರೇಷನ್ ಕಾರ್ಡ್ ಸರಿಪಡಿಸಲು ಸಹಾಯ ಮಾಡ್ತೀನಿ. ನಿಮ್ಮ ಕಾರ್ಡ್ ನಂಬರ್ ಹೇಳ್ತೀರಾ?",
         "intent": "ration_card_correction", "sl": "neutral", "si": 0.25, "conf": 0.87},
        {"kw": ["KA", "BLR", "0234"],
         "tx": "ಕಾರ್ಡ್ ನಂಬರ್ KA-BLR-0234567",
         "rs": "ಧನ್ಯವಾದ. ಯಾವ ವಿಷಯ ತಪ್ಪಾಗಿದೆ — ಹೆಸರು, ವಿಳಾಸ, ಅಥವಾ ಬೇರೆ?",
         "intent": "ration_card_correction", "sl": "neutral", "si": 0.20, "conf": 0.90},
        {"kw": ["ತಂದೆ", "ಹೆಸರು"],
         "tx": "ನನ್ನ ತಂದೆಯ ಹೆಸರು ತಪ್ಪಾಗಿ ಮುದ್ರಣ ಆಗಿದೆ",
         "rs": "ತಂದೆಯ ಹೆಸರು ಸರಿಪಡಿಸಲು ಜನನ ಪ್ರಮಾಣಪತ್ರ ಬೇಕಾಗ್ತದೆ. ಹತ್ತಿರದ ನಾಡ ಕಚೇರಿಗೆ ಭೇಟಿ ಕೊಡಿ. ದೂರು ನೋಂದಾಯಿಸಲೇ?",
         "intent": "ration_card_correction", "sl": "neutral", "si": 0.25, "conf": 0.85},
        {"kw": ["ಹೌದು", "ನೋಂದಾಯಿಸಿ"],
         "tx": "ಹೌದು, ದಯವಿಟ್ಟು ನೋಂದಾಯಿಸಿ",
         "rs": "ದೂರು ದಾಖಲಿಸಲಾಗಿದೆ. ಆಹಾರ ಇಲಾಖೆ 15 ದಿನಗಳಲ್ಲಿ ಸಂಪರ್ಕಿಸ್ತಾರೆ. ಟಿಕೆಟ್ BLR-RATION-2024-04512.",
         "intent": "ration_card_correction", "sl": "calm", "si": 0.15, "conf": 0.93},
        {"kw": ["ನಾಡ", "ಕಚೇರಿ", "ಎಲ್ಲಿ"],
         "tx": "ನಾಡ ಕಚೇರಿ ಎಲ್ಲಿದೆ?",
         "rs": "ಹತ್ತಿರದ ನಾಡ ಕಚೇರಿ ರಾಜಾಜಿನಗರ, ಬೆಂಗಳೂರು. ನಂಬರ್ 080-22345678. ಸೋಮ–ಶುಕ್ರ 10am–5pm.",
         "intent": "ration_card_correction", "sl": "calm", "si": 0.10, "conf": 0.95},
    ],
    # ── S3: Hindi — water supply complaint (PII: Aadhaar in turn 1) ─────────
    "hi_water": [
        {"kw": ["पानी", "नहीं", "घर"],
         "tx": "मेरे घर में तीन दिन से पानी नहीं आ रहा",
         "rs": "पानी की समस्या गंभीर है। आपका वार्ड नंबर और पता बताइए।",
         "intent": "water_supply_complaint", "sl": "concerned", "si": 0.45, "conf": 0.82},
        {"kw": ["बसवनगुड़ी", "वार्ड", "आधार"],
         "tx": "बसवनगुड़ी वार्ड 156. मेरा आधार 7845 1234 5678 है",
         "rs": "आधार नंबर AADHAAR_1 के रूप में दर्ज। बसवनगुड़ी वार्ड 156 में पानी आपूर्ति शिकायत दर्ज हो रही है।",
         "intent": "water_supply_complaint", "sl": "concerned", "si": 0.42, "conf": 0.79, "pii": True},
        {"kw": ["पड़ोसी", "भी", "समस्या"],
         "tx": "पड़ोसियों को भी यही समस्या है",
         "rs": "यह एरिया-लेवल समस्या है। BWSSB को अर्जेंट नोटिस भेज रहे हैं।",
         "intent": "water_supply_complaint", "sl": "concerned", "si": 0.50, "conf": 0.85},
        {"kw": ["कब", "ठीक", "होगा"],
         "tx": "कब तक ठीक होगा?",
         "rs": "BWSSB टीम 24 घंटों में निरीक्षण करेगी। शिकायत संख्या BLR-WATER-2024-11293.",
         "intent": "water_supply_complaint", "sl": "neutral", "si": 0.30, "conf": 0.88},
        {"kw": ["शुक्रिया", "ठीक"],
         "tx": "ठीक है, शुक्रिया",
         "rs": "शिकायत दर्ज। टिकट 1092-BLR-2024-11293 SMS आएगा। कोई और मदद?",
         "intent": "water_supply_complaint", "sl": "calm", "si": 0.15, "conf": 0.93},
    ],
    # ── S4: Hindi — workplace harassment / distress (escalates at turn 3) ───
    "hi_safety": [
        {"kw": ["मदद", "ऑफिस", "परेशानी"],
         "tx": "मुझे मदद चाहिए, मेरे साथ ऑफिस में परेशानी हो रही है",
         "rs": "हम आपकी मदद के लिए हैं। क्या हुआ, थोड़ा और बताइए।",
         "intent": "women_safety", "sl": "concerned", "si": 0.55, "conf": 0.80},
        {"kw": ["मैनेजर", "परेशान", "सुरक्षित"],
         "tx": "मेरे मैनेजर मुझे परेशान कर रहे हैं, सुरक्षित नहीं लग रहा",
         "rs": "यह गंभीर बात है। क्या आप अभी सुरक्षित जगह पर हैं?",
         "intent": "women_safety", "sl": "distress", "si": 0.68, "conf": 0.77},
        {"kw": ["बाहर", "डर"],
         "tx": "हाँ अभी बाहर हूँ लेकिन डर लग रहा है",
         "rs": "आपकी बात सुन रहे हैं। ICC में शिकायत दर्ज करने में मदद करते हैं।",
         "intent": "women_safety", "sl": "distress", "si": 0.72, "conf": 0.73},
        {"kw": ["घबराई", "नहीं पता"],
         "tx": "मुझे नहीं पता क्या करूँ, बहुत घबराई हुई हूँ",
         "rs": "आपकी बात एक महिला सहायता अधिकारी तक पहुँचाई जा रही है। कृपया लाइन पर रहें।",
         "intent": "women_safety", "sl": "distress", "si": 0.85, "conf": 0.65,
         "escalate": True,
         "esc_reason": "high_distress",
         "esc_summary": "Workplace harassment — caller feels unsafe, requesting urgent help"},
        {"kw": ["ठीक"],
         "tx": "ठीक है",
         "rs": "महिला सहायता अधिकारी कुछ ही मिनटों में बात करेंगी। आप सुरक्षित हैं।",
         "intent": "women_safety", "sl": "distress", "si": 0.70, "conf": 0.80},
    ],
    # ── S5: English — BBMP road pothole ──────────────────────────────────────
    "en_road": [
        {"kw": ["pothole", "road"],
         "tx": "There is a huge pothole on my road and it is very dangerous",
         "rs": "I understand your concern. Can you tell me the road name and a nearby landmark?",
         "intent": "road_repair", "sl": "concerned", "si": 0.40, "conf": 0.88},
        {"kw": ["main", "indiranagar"],
         "tx": "It is on 12th Main Road, Indiranagar, near the petrol pump",
         "rs": "Got it — 12th Main Road, Indiranagar. How long has this pothole been there?",
         "intent": "road_repair", "sl": "neutral", "si": 0.30, "conf": 0.91},
        {"kw": ["months", "fallen"],
         "tx": "It has been there for 2 months and two people have fallen",
         "rs": "This is serious. Flagging as high priority and raising an urgent BBMP complaint.",
         "intent": "road_repair", "sl": "concerned", "si": 0.55, "conf": 0.85},
        {"kw": ["when", "fixed"],
         "tx": "When will it be fixed?",
         "rs": "BBMP road crew will visit within 48 hours. Complaint number BLR-BBMP-2024-33781.",
         "intent": "road_repair", "sl": "neutral", "si": 0.25, "conf": 0.90},
        {"kw": ["thank"],
         "tx": "Okay, thank you",
         "rs": "Complaint registered. Ticket 1092-BLR-2024-33781. SMS confirmation will follow. Anything else?",
         "intent": "road_repair", "sl": "calm", "si": 0.10, "conf": 0.95},
    ],
}

# session_id → (scenario_key, next_expected_turn_index)
_ss_state: dict[str, tuple[str, int]] = {}
# scenario_key_turn_index → base64 TTS audio
_ss_tts: dict[str, str] = {}


def _ss_match(session_id: str, transcript: str) -> Optional[tuple[str, int, dict]]:
    """Return (scenario_key, turn_index, turn_data) if transcript hits a scenario turn."""
    tx = transcript.lower()
    if session_id in _ss_state:
        sk, idx = _ss_state[session_id]
        turns = _SS.get(sk, [])
        if idx < len(turns) and any(kw.lower() in tx for kw in turns[idx]["kw"]):
            return sk, idx, turns[idx]
        return None
    for sk, turns in _SS.items():
        if turns and any(kw.lower() in tx for kw in turns[0]["kw"]):
            return sk, 0, turns[0]
    return None


async def _ss_serve(
    websocket: WebSocket,
    session: SessionState,
    sk: str,
    idx: int,
    turn: dict,
    language: str,
) -> None:
    """Serve a pre-baked scenario turn: no NLU, no live TTS synthesis if cached."""
    next_idx = idx + 1
    if next_idx < len(_SS[sk]):
        _ss_state[session.session_id] = (sk, next_idx)
    else:
        _ss_state.pop(session.session_id, None)

    citizen_turn = Turn(
        speaker="citizen",
        raw_transcript=turn["tx"],
        asr_confidence=turn["conf"],
        detected_language=language,
        intent=turn["intent"],
    )
    session.add_turn(citizen_turn)
    session.final_intent = turn["intent"]
    session.composite_confidence = turn["conf"]
    session.sentiment_timeline.append({
        "turn_id": citizen_turn.turn_id,
        "timestamp": citizen_turn.timestamp.isoformat(),
        "label": turn["sl"],
        "intensity": turn["si"],
        "prosodic_component": round(turn["si"] * 0.4, 2),
        "text_component": round(turn["si"] * 0.6, 2),
    })
    if len(session.sentiment_timeline) > 20:
        session.sentiment_timeline = session.sentiment_timeline[-20:]

    cache_key = f"{sk}_{idx}"
    tts_audio = _ss_tts.get(cache_key, "")
    if not tts_audio:
        try:
            tts_audio = await tts.synthesize(turn["rs"], language=language)
            _ss_tts[cache_key] = tts_audio
        except Exception:
            tts_audio = ""

    ai_turn = Turn(speaker="ai", raw_transcript=turn["rs"], tts_audio_b64=tts_audio)
    session.add_turn(ai_turn)
    session.verification_state = "pending"

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
            "conversation_stage": session.conversation_stage,
        },
        "mock_mode": settings.environment == "mock",
    })
    try:
        await websocket.send_json({
            "type": "nlu_update",
            "session_id": session.session_id,
            "nlu": {"intent": turn["intent"], "intent_confidence": turn["conf"]},
            "confidence_score": {
                "asr_confidence": turn["conf"],
                "intent_entropy": 0.18,
                "sentiment_intensity": turn["si"],
                "clarification_count": session.clarification_count,
                "composite_score": turn["conf"],
            },
            "sentiment_timeline": session.sentiment_timeline[-10:],
        })
    except Exception:
        pass

    if turn.get("escalate"):
        session.is_escalated = True
        session.escalation_reason = turn.get("esc_reason", "high_distress")
        session.escalation_summary = turn.get("esc_summary", "")
        packet = EscalationPacket(
            session_id=session.session_id,
            reason=session.escalation_reason,
            summary=session.escalation_summary,
            district=session.district,
            detected_language=language,
            final_intent=session.final_intent,
            composite_confidence=session.composite_confidence,
            transcript=session.to_transcript_text(),
            sentiment_timeline=session.sentiment_timeline,
            ai_interpretation="",
            ticket_draft={},
        )
        await push_escalation(
            session_id=session.session_id,
            sentiment_intensity=turn["si"],
            sentiment=turn["sl"],
            reason=session.escalation_reason,
            summary=session.escalation_summary,
            district=session.district,
            language=language,
            final_intent=session.final_intent,
            created_at=session.created_at,
        )
        await broadcast_escalation(packet.model_dump(mode="json"))
        try:
            await websocket.send_json({
                "type": "escalation",
                "packet": packet.model_dump(mode="json"),
                "tts_audio_b64": tts_audio,
                "escalation_message": turn["rs"],
            })
        except Exception:
            pass


async def _warmup_ss_tts() -> None:
    """Pre-synthesize all scenario AI responses into _ss_tts cache at startup."""
    _lang_of = lambda sk: sk.split("_")[0]
    for sk, turns in _SS.items():
        lang = _lang_of(sk)
        for i, turn in enumerate(turns):
            key = f"{sk}_{i}"
            if key not in _ss_tts:
                try:
                    audio = await tts.synthesize(turn["rs"], language=lang)
                    _ss_tts[key] = audio
                except Exception:
                    pass
    print(f"[STARTUP] Scenario TTS cache warmed: {len(_ss_tts)} clips")


app = FastAPI(
    title="Samvaad-Setu API",
    description="Real-time multilingual voice assistant for Karnataka 1092 helpline",
    version="0.1.0",
)


@app.on_event("startup")
async def _startup():
    """Initialise DB engine and create tables on startup."""
    try:
        import db as _db
        _db.init_db()
        await _db.create_all_tables()
        print("[STARTUP] DB tables ready")
    except Exception as exc:
        print(f"[STARTUP] DB init failed (non-fatal in mock mode): {exc}")

    # Always seed demo sessions so the agent dashboard has data out-of-the-box
    try:
        from demo_fixtures.demo_sessions import build_demo_sessions, DEMO_QUEUE_ENTRIES
        from datetime import timedelta

        demo_sessions = build_demo_sessions()
        for s in demo_sessions:
            await session_manager.save_session(s)
        for i, entry in enumerate(DEMO_QUEUE_ENTRIES):
            created_at = datetime.now(timezone.utc) - timedelta(minutes=5 + i * 7)
            await push_escalation(
                session_id=entry["session_id"],
                sentiment_intensity=entry["sentiment_intensity"],
                sentiment=entry["sentiment"],
                reason=entry["reason"],
                summary=entry["summary"],
                district=entry["district"],
                language=entry["language"],
                final_intent=entry["final_intent"],
                created_at=created_at,
            )
        print(f"[STARTUP] Seeded {len(demo_sessions)} demo sessions into agent queue")
    except Exception as exc:
        print(f"[STARTUP] Demo seed failed (non-fatal): {exc}")

    asyncio.create_task(_warmup_ss_tts())

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
    session.user_language = language  # preserve UI-selected language throughout session
    await session_manager.save_session(session)
    response = {"session_id": session.session_id, "district": district, "language": language}

    if idempotency_key:
        await session_manager.set_idempotency(idempotency_key, response)

    # Register in the all-sessions map so it shows up in the agent queue immediately
    push_active_session(
        session_id=session.session_id,
        district=district,
        language=language,
        summary="New call connected",
        reason="active",
    )
    await broadcast_to_agents({
        "type": "session_update",
        "session": {
            "session_id": session.session_id,
            "district": district,
            "language": language,
            "sentiment": "calm",
            "sentiment_intensity": 0.3,
            "summary": "New call connected",
            "reason": "active",
            "final_intent": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "is_escalated": False,
        },
    })

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


@app.get("/sessions/{session_id}/ticket")
async def get_session_ticket(session_id: str):
    """
    Return the ticket for a session.  If none exists yet (e.g. citizen just
    hung up without confirmation), create one with trigger='call_ended'.
    """
    existing = await ticket_service.get_ticket(session_id)
    if existing:
        return existing.model_dump()

    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if not session.turns:
        raise HTTPException(404, "No activity on this session — no ticket to create")

    info = await ticket_service.create_ticket(session, "call_ended")
    return info.model_dump()


@app.post("/sessions/{session_id}/agent-reply")
async def agent_reply(session_id: str, body: dict):
    """
    Send a human-agent reply to the citizen's live WebSocket session.
    Body: { "text": "...", "agent_id": "agent-001" }
    """
    text = (body.get("text") or "").strip()
    agent_id = body.get("agent_id", "agent")
    if not text:
        raise HTTPException(400, "text is required")

    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    language = session.detected_language or "en"
    tts_audio = ""
    try:
        tts_audio = await tts.synthesize(text, language=language)
    except Exception as exc:
        print(f"[AGENT_REPLY_HTTP] TTS failed: {exc}")

    delivered = await send_to_citizen(session_id, {
        "type": "agent_audio",
        "text": text,
        "tts_audio_b64": tts_audio,
    })
    if not delivered:
        raise HTTPException(409, "Citizen is not connected to live session")

    await log_event(
        session_id,
        "agent_reply_sent",
        actor="agent",
        payload={"agent_id": agent_id, "text": text},
    )
    return {"ok": True, "session_id": session_id, "delivered": True}


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

    # Load demo translations (no-op for non-demo sessions)
    try:
        from demo_fixtures.demo_sessions import DEMO_TURN_TRANSLATIONS
        _turn_translations = DEMO_TURN_TRANSLATIONS.get(session_id, {})
    except Exception:
        _turn_translations = {}

    # Build structured transcript (turns without TTS audio to keep payload lean)
    transcript = []
    for t in session.turns:
        base_text = t.raw_transcript or t.ai_rephrasing or ""
        t_trans = _turn_translations.get(t.turn_id, {})
        transcript.append({
            "turn_id": t.turn_id,
            "speaker": t.speaker,
            "timestamp": t.timestamp.isoformat(),
            "raw_transcript": base_text,
            "ai_rephrasing": t.ai_rephrasing,
            "intent": t.intent,
            "asr_confidence": t.asr_confidence,
            "sentiment": t.sentiment.model_dump() if t.sentiment else None,
            "verification_state": t.verification_state,
            # Language-specific text for the agent dashboard language toggle
            "en_text": t_trans.get("en", base_text),
            "hi_text": t_trans.get("hi", base_text),
            "kn_text": t_trans.get("kn", base_text),
        })

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
    await ticket_service.update_ticket_status(session_id, "resolved")
    await log_event(
        session_id, "session_resolved", actor="agent",
        payload={"agent_id": agent_id},
    )
    return {"ok": True, "session_id": session_id}


@app.get("/tickets")
async def list_tickets_endpoint(
    limit: int = 30,
    offset: int = 0,
    status: Optional[str] = None,
    district: Optional[str] = None,
):
    """List recent tickets for the analytics dashboard."""
    tickets = await ticket_service.list_tickets(
        limit=limit, offset=offset, status=status, district=district
    )
    return {"tickets": [t.model_dump() for t in tickets], "total": len(tickets)}


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


# ─── ANALYTICS ───────────────────────────────────────────────────────────────

_ANALYTICS_DISTRICT_DATA = [
    {"district": "bengaluru_urban",  "label": "Bengaluru Urban",  "lat": 12.97, "lng": 77.59, "calls": 14, "escalated": 5, "avg_sentiment": 0.62, "primary_intent": "police_complaint"},
    {"district": "mysuru",           "label": "Mysuru",           "lat": 12.30, "lng": 76.64, "calls":  9, "escalated": 2, "avg_sentiment": 0.42, "primary_intent": "ration_card_issue"},
    {"district": "mangaluru",        "label": "Mangaluru",        "lat": 12.87, "lng": 74.84, "calls":  7, "escalated": 3, "avg_sentiment": 0.68, "primary_intent": "water_supply_complaint"},
    {"district": "belagavi",         "label": "Belagavi",         "lat": 15.85, "lng": 74.50, "calls":  6, "escalated": 2, "avg_sentiment": 0.52, "primary_intent": "sanitation_garbage"},
    {"district": "hubballi_dharwad", "label": "Hubballi-Dharwad", "lat": 15.36, "lng": 75.12, "calls":  5, "escalated": 2, "avg_sentiment": 0.48, "primary_intent": "road_repair"},
    {"district": "kalaburagi",       "label": "Kalaburagi",       "lat": 17.33, "lng": 76.83, "calls":  5, "escalated": 2, "avg_sentiment": 0.55, "primary_intent": "pension_scheme"},
    {"district": "tumakuru",         "label": "Tumakuru",         "lat": 13.34, "lng": 77.12, "calls":  5, "escalated": 1, "avg_sentiment": 0.40, "primary_intent": "ration_card_issue"},
    {"district": "bengaluru_rural",  "label": "Bengaluru Rural",  "lat": 13.17, "lng": 77.60, "calls":  4, "escalated": 1, "avg_sentiment": 0.40, "primary_intent": "road_repair"},
    {"district": "davangere",        "label": "Davangere",        "lat": 14.46, "lng": 75.92, "calls":  4, "escalated": 1, "avg_sentiment": 0.44, "primary_intent": "bescom_billing"},
    {"district": "vijayapura",       "label": "Vijayapura",       "lat": 16.83, "lng": 75.71, "calls":  4, "escalated": 1, "avg_sentiment": 0.48, "primary_intent": "road_repair"},
    {"district": "ballari",          "label": "Ballari",          "lat": 15.14, "lng": 76.92, "calls":  4, "escalated": 1, "avg_sentiment": 0.50, "primary_intent": "water_supply_complaint"},
    {"district": "shivamogga",       "label": "Shivamogga",       "lat": 13.93, "lng": 75.57, "calls":  3, "escalated": 1, "avg_sentiment": 0.38, "primary_intent": "bescom_billing"},
    {"district": "chitradurga",      "label": "Chitradurga",      "lat": 14.23, "lng": 76.40, "calls":  3, "escalated": 1, "avg_sentiment": 0.45, "primary_intent": "water_supply_complaint"},
    {"district": "hassan",           "label": "Hassan",           "lat": 13.01, "lng": 76.10, "calls":  3, "escalated": 0, "avg_sentiment": 0.32, "primary_intent": "ration_card_issue"},
    {"district": "udupi",            "label": "Udupi",            "lat": 13.34, "lng": 74.74, "calls":  3, "escalated": 1, "avg_sentiment": 0.35, "primary_intent": "water_connection"},
    {"district": "raichur",          "label": "Raichur",          "lat": 16.21, "lng": 77.34, "calls":  3, "escalated": 1, "avg_sentiment": 0.55, "primary_intent": "pension_scheme"},
    {"district": "bagalkot",         "label": "Bagalkot",         "lat": 16.18, "lng": 75.70, "calls":  3, "escalated": 1, "avg_sentiment": 0.45, "primary_intent": "road_repair"},
    {"district": "koppal",           "label": "Koppal",           "lat": 15.35, "lng": 76.16, "calls":  2, "escalated": 1, "avg_sentiment": 0.50, "primary_intent": "water_supply_complaint"},
    {"district": "bidar",            "label": "Bidar",            "lat": 17.91, "lng": 77.52, "calls":  2, "escalated": 1, "avg_sentiment": 0.60, "primary_intent": "pension_scheme"},
    {"district": "gadag",            "label": "Gadag",            "lat": 15.42, "lng": 75.63, "calls":  2, "escalated": 0, "avg_sentiment": 0.40, "primary_intent": "sanitation_garbage"},
    {"district": "haveri",           "label": "Haveri",           "lat": 14.79, "lng": 75.40, "calls":  2, "escalated": 0, "avg_sentiment": 0.42, "primary_intent": "sanitation_garbage"},
    {"district": "ramanagara",       "label": "Ramanagara",       "lat": 12.72, "lng": 77.28, "calls":  2, "escalated": 0, "avg_sentiment": 0.35, "primary_intent": "ration_card_issue"},
    {"district": "kodagu",           "label": "Kodagu",           "lat": 12.34, "lng": 75.81, "calls":  2, "escalated": 0, "avg_sentiment": 0.28, "primary_intent": "water_connection"},
    {"district": "kolar",            "label": "Kolar",            "lat": 13.14, "lng": 78.13, "calls":  2, "escalated": 0, "avg_sentiment": 0.38, "primary_intent": "bescom_billing"},
    {"district": "chikkamagaluru",   "label": "Chikkamagaluru",   "lat": 13.32, "lng": 75.77, "calls":  2, "escalated": 0, "avg_sentiment": 0.30, "primary_intent": "road_repair"},
    {"district": "yadgir",           "label": "Yadgir",           "lat": 16.77, "lng": 77.13, "calls":  2, "escalated": 1, "avg_sentiment": 0.58, "primary_intent": "pension_scheme"},
    {"district": "uttara_kannada",   "label": "Uttara Kannada",   "lat": 14.80, "lng": 74.50, "calls":  2, "escalated": 0, "avg_sentiment": 0.35, "primary_intent": "water_connection"},
    {"district": "mandya",           "label": "Mandya",           "lat": 12.52, "lng": 76.90, "calls":  2, "escalated": 0, "avg_sentiment": 0.38, "primary_intent": "ration_card_issue"},
    {"district": "chikkaballapur",   "label": "Chikkaballapur",   "lat": 13.44, "lng": 77.73, "calls":  1, "escalated": 0, "avg_sentiment": 0.32, "primary_intent": "road_repair"},
    {"district": "chamarajanagar",   "label": "Chamarajanagara",  "lat": 11.92, "lng": 76.94, "calls":  1, "escalated": 0, "avg_sentiment": 0.30, "primary_intent": "ration_card_issue"},
]


@app.get("/analytics/overview")
async def analytics_overview():
    """Aggregated call analytics for the regional analytics dashboard."""
    data = _ANALYTICS_DISTRICT_DATA
    total_calls = sum(d["calls"] for d in data)
    total_escalated = sum(d["escalated"] for d in data)
    weighted_sentiment = (
        sum(d["avg_sentiment"] * d["calls"] for d in data) / total_calls
        if total_calls else 0
    )
    return {
        "summary": {
            "total_calls": total_calls,
            "escalated_calls": total_escalated,
            "resolved_calls": max(0, total_escalated - 4),
            "avg_confidence": 0.71,
            "avg_sentiment_intensity": round(weighted_sentiment, 2),
        },
        "by_district": data,
        "intent_distribution": [
            {"intent_id": "ration_card_issue",      "label": "Ration Card",      "count": 18},
            {"intent_id": "water_supply_complaint",  "label": "Water Supply",     "count": 16},
            {"intent_id": "police_complaint",        "label": "Police/Safety",    "count": 14},
            {"intent_id": "road_repair",             "label": "Road Repair",      "count": 13},
            {"intent_id": "pension_scheme",          "label": "Pension Scheme",   "count": 11},
            {"intent_id": "sanitation_garbage",      "label": "Sanitation",       "count":  8},
            {"intent_id": "bescom_billing",          "label": "BESCOM Billing",   "count":  7},
            {"intent_id": "other",                   "label": "Other",            "count":  6},
        ],
        "escalation_reasons": [
            {"reason": "high_distress",           "label": "High Distress",          "count": 12},
            {"reason": "repeated_clarification",  "label": "Repeated Clarification", "count":  8},
            {"reason": "low_confidence",          "label": "Low Confidence",         "count":  5},
        ],
        "language_distribution": [
            {"language": "kn", "label": "Kannada", "count": 68},
            {"language": "hi", "label": "Hindi",   "count": 22},
            {"language": "en", "label": "English", "count": 10},
        ],
        "hourly_trend": [
            {"hour":  8, "calls":  3, "escalated": 0},
            {"hour":  9, "calls":  6, "escalated": 1},
            {"hour": 10, "calls": 10, "escalated": 2},
            {"hour": 11, "calls": 13, "escalated": 3},
            {"hour": 12, "calls":  9, "escalated": 2},
            {"hour": 13, "calls":  8, "escalated": 1},
            {"hour": 14, "calls": 11, "escalated": 3},
            {"hour": 15, "calls": 12, "escalated": 2},
            {"hour": 16, "calls": 10, "escalated": 2},
            {"hour": 17, "calls": 14, "escalated": 4},
            {"hour": 18, "calls":  8, "escalated": 2},
            {"hour": 19, "calls":  5, "escalated": 1},
            {"hour": 20, "calls":  3, "escalated": 0},
            {"hour": 21, "calls":  2, "escalated": 0},
        ],
    }


# ─── DEMO / SEED ENDPOINTS ────────────────────────────────────────────────────

_demo_session_ids: set[str] = set()


@app.post("/demo/seed-agent-queue")
async def demo_seed_agent_queue():
    """
    Seed the agent dashboard queue with pre-built demo sessions.
    Idempotent — calling again re-seeds without duplicating.
    """
    from demo_fixtures.demo_sessions import build_demo_sessions, DEMO_QUEUE_ENTRIES, DEMO_SESSION_IDS

    sessions = build_demo_sessions()
    for session in sessions:
        await session_manager.save_session(session)
        _demo_session_ids.add(session.session_id)

    from datetime import datetime, timezone, timedelta
    for i, entry in enumerate(DEMO_QUEUE_ENTRIES):
        # Spread created_at so queue sort order is deterministic
        created_at = datetime.now(timezone.utc) - timedelta(minutes=5 + i * 7)
        await push_escalation(
            session_id=entry["session_id"],
            sentiment_intensity=entry["sentiment_intensity"],
            sentiment=entry["sentiment"],
            reason=entry["reason"],
            summary=entry["summary"],
            district=entry["district"],
            language=entry["language"],
            final_intent=entry["final_intent"],
            created_at=created_at,
        )

    return {"seeded": len(sessions), "session_ids": list(DEMO_SESSION_IDS)}


@app.delete("/demo/clear-agent-queue")
async def demo_clear_agent_queue():
    """Remove all demo sessions from the queue and session store."""
    from demo_fixtures.demo_sessions import DEMO_SESSION_IDS

    cleared = []
    for sid in DEMO_SESSION_IDS:
        await remove_from_queue(sid)
        _demo_session_ids.discard(sid)
        cleared.append(sid)

    return {"cleared": len(cleared), "session_ids": cleared}


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

    # Send current queue snapshot on connect — includes escalated + all active sessions
    from services.agent_queue import get_active_sessions, total_active_sessions
    entries = get_active_sessions(limit=50, offset=0)
    total = total_active_sessions()
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
            msg_type = msg.get("type")
            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            elif msg_type == "agent_reply":
                await _handle_agent_ws_reply(msg)
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

    register_citizen(session_id, websocket)

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

            elif msg_type == "end_call":
                print(f"[WS] Processing end_call...")
                await _handle_end_call(websocket, session)
                await session_manager.save_session(session)

            elif msg_type == "feedback":
                print(f"[WS] Processing feedback...")
                await _handle_feedback(websocket, session, msg)
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
        unregister_citizen(session_id)
        remove_active_session(session_id)
        await broadcast_to_agents({"type": "session_ended", "session_id": session_id})
        # Silently ensure a ticket exists if the call ended without going through end_call flow
        if session.turns and session.conversation_stage not in ("ended",):
            try:
                await ticket_service.create_ticket(session, "call_ended")
            except Exception:
                pass
        await session_manager.save_session(session)


async def _handle_audio_turn(websocket: WebSocket, session: SessionState, msg: dict):
    """
    Fast pipeline: ASR → quick conversational response → TTS → send audio to client.
    Full NLU (intent/sentiment/confidence) runs in background AFTER audio is sent,
    so the citizen hears a response ~600ms sooner.
    """
    audio_b64: str = msg.get("data", "")
    msg_language: str = msg.get("language", session.detected_language)
    district:     str = msg.get("district", session.district)

    # Preserve user's explicitly chosen language
    if not session.user_language:
        session.user_language = msg_language
    language = session.user_language

    session.detected_language = language
    session.district = district

    if not session.dialect_tag:
        from services.dialect_context import DialectContextProvider
        _dcp = DialectContextProvider()
        try:
            session.dialect_tag = _dcp.get_profile(district).dialect_tag
        except Exception:
            session.dialect_tag = district

    audio_bytes = base64.b64decode(audio_b64) if audio_b64 else b""
    print(f"[AUDIO] {len(audio_bytes)} bytes | lang={language} district={district}")

    # ── 1. ASR ─────────────────────────────────────────────────────────────
    async with track("asr"):
        asr_result = await asr.transcribe(audio_bytes, hint_language=language, district=district)
    print(f"[ASR] '{asr_result.transcript[:60]}' conf={asr_result.confidence}")

    # ── FAST PATH: pre-scripted scenario ───────────────────────────────────
    hit = _ss_match(session.session_id, asr_result.transcript)
    if hit:
        sk, idx, turn = hit
        print(f"[SS] scenario={sk} turn={idx}")
        await _ss_serve(websocket, session, sk, idx, turn, language)
        await session_manager.save_session(session)
        return

    # ── 2. Fast conversational response (plain text, ~200ms) ───────────────
    async with track("conversation"):
        ai_text = await nlu.generate_conversation_turn(asr_result.transcript, session)
    print(f"[CONV] '{ai_text[:80]}'")

    # ── 3. TTS ─────────────────────────────────────────────────────────────
    tts_audio = ""
    try:
        async with track("tts"):
            tts_audio = await tts.synthesize(ai_text, language=language)
        print(f"[TTS] audio length: {len(tts_audio)}")
    except Exception as e:
        print(f"[TTS] failed: {e}")

    # ── 4. Build turns and add to session ──────────────────────────────────
    citizen_turn = Turn(
        speaker="citizen",
        raw_transcript=asr_result.transcript,
        asr_confidence=asr_result.confidence,
        detected_language=asr_result.language,
    )
    session.add_turn(citizen_turn)

    ai_turn = Turn(
        speaker="ai",
        raw_transcript=ai_text,
        tts_audio_b64=tts_audio,
    )
    session.add_turn(ai_turn)

    # ── 5. Send audio to citizen immediately ───────────────────────────────
    session.verification_state = "pending"
    await websocket.send_json({
        "type": "turn_update",
        "citizen_turn": citizen_turn.model_dump(mode="json"),
        "ai_turn":      ai_turn.model_dump(mode="json"),
        "session": {
            "session_id":        session.session_id,
            "composite_confidence": session.composite_confidence,
            "sentiment_timeline": session.sentiment_timeline,
            "is_escalated":      session.is_escalated,
            "clarification_count": session.clarification_count,
            "verification_state": session.verification_state,
            "district":          session.district,
            "current_language":  session.detected_language,
            "conversation_stage": session.conversation_stage,
        },
        "mock_mode": settings.environment == "mock",
    })
    print(f"[WS] turn_update sent ← audio on its way to citizen")

    # Always show Yes/Partly/No panel so citizen can confirm understanding.
    # Synthesise TTS for the verification question so it is spoken after the
    # main AI response — the frontend plays both sequentially via its audio chain.
    verify_panel_text = _verification_engine.generate_verification_prompt(
        intent=session.final_intent or "other_grievance",
        entities={},
        language=language,
        district=district,
    )
    verify_tts = ""
    try:
        verify_tts = await tts.synthesize(verify_panel_text, language=language)
    except Exception:
        pass
    await websocket.send_json({
        "type": "verification_prompt",
        "text": verify_panel_text,
        "tts_audio_b64": verify_tts,
        "language": language,
        "district": district,
        "session_id": session.session_id,
        "conversation_stage": session.conversation_stage,
    })

    # ── 6. Background: full NLU + sentiment + escalation (non-blocking) ────
    # Runs while the citizen is listening to the TTS audio.
    asyncio.create_task(
        _background_nlu_task(websocket, session, asr_result, citizen_turn, audio_bytes, language, district)
    )


async def _background_nlu_task(
    websocket: WebSocket,
    session: SessionState,
    asr_result,
    citizen_turn: Turn,
    audio_bytes: bytes,
    language: str,
    district: str,
) -> None:
    """
    Runs after the audio response has been sent to the citizen.
    Extracts intent, sentiment, confidence and updates the agent dashboard.
    The citizen is already hearing the AI response while this runs.
    """
    try:
        nlu_result = await nlu.extract_intent_and_rephrase(asr_result.transcript, session)
        sentiment_result = await sentiment.analyze(asr_result.transcript, audio_bytes, language)

        # Back-fill the citizen turn that was already added to the session
        citizen_turn.intent = nlu_result.get("intent")
        citizen_turn.intent_entropy = nlu_result.get("intent_entropy", 0.0)
        citizen_turn.ai_rephrasing = nlu_result.get("rephrasing", "")
        citizen_turn.sentiment = TurnSentiment(
            label=sentiment_result.label,
            intensity=sentiment_result.intensity,
            prosodic_component=sentiment_result.prosodic_component,
            text_component=sentiment_result.text_component,
        )
        # Update session-level timeline and intent
        if citizen_turn.sentiment:
            session.sentiment_timeline.append({
                "turn_id": citizen_turn.turn_id,
                "timestamp": citizen_turn.timestamp.isoformat(),
                "label": sentiment_result.label,
                "intensity": sentiment_result.intensity,
                "prosodic_component": sentiment_result.prosodic_component,
                "text_component": sentiment_result.text_component,
            })
            if len(session.sentiment_timeline) > 20:
                session.sentiment_timeline = session.sentiment_timeline[-20:]
        session.final_intent = citizen_turn.intent

        esc_decision = escalation.evaluate(
            session,
            asr_confidence=asr_result.confidence,
            intent_entropy=citizen_turn.intent_entropy,
            sentiment=sentiment_result,
        )
        session.composite_confidence = 1.0 - esc_decision.composite_score

        turn_confidence = build_score(
            asr_conf=asr_result.confidence,
            intent_entropy=citizen_turn.intent_entropy,
            sentiment_intensity=sentiment_result.intensity,
            clarification_count=session.clarification_count,
        )
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

        # Send NLU enrichment to client (updates agent dashboard gauges)
        try:
            await websocket.send_json({
                "type": "nlu_update",
                "session_id": session.session_id,
                "nlu": {
                    "intent": nlu_result.get("intent"),
                    "intent_confidence": nlu_result.get("intent_confidence"),
                    "structured_summary": nlu_result.get("structured_summary"),
                    "responsible_department": nlu_result.get("responsible_department"),
                },
                "confidence_score": turn_confidence.model_dump(),
                "escalation": {
                    "composite_score": esc_decision.composite_score,
                    "explanation": esc_decision.explanation,
                },
                "sentiment_timeline": session.sentiment_timeline[-10:],
            })
        except Exception:
            pass  # WebSocket may have closed

        # Broadcast enriched data to agent dashboards
        last_sent = session.sentiment_timeline[-1] if session.sentiment_timeline else {}
        push_active_session(
            session_id=session.session_id,
            district=session.district,
            language=session.detected_language,
            sentiment=last_sent.get("label", "calm"),
            sentiment_intensity=last_sent.get("intensity", 0.3),
            summary=asr_result.transcript[:120],
            reason="active",
            final_intent=session.final_intent,
            is_escalated=session.is_escalated,
        )
        await broadcast_to_agents({
            "type": "session_live_update",
            "session_id": session.session_id,
            "citizen_turn": citizen_turn.model_dump(mode="json"),
            "confidence_score": turn_confidence.model_dump(),
            "sentiment_timeline": session.sentiment_timeline[-10:],
            "session": {
                "session_id": session.session_id,
                "district": session.district,
                "language": session.detected_language,
                "sentiment": last_sent.get("label", "calm"),
                "sentiment_intensity": last_sent.get("intensity", 0.3),
                "summary": asr_result.transcript[:120],
                "reason": "active",
                "final_intent": session.final_intent,
                "is_escalated": session.is_escalated,
            },
        })

        # Persist enriched session
        await session_manager.save_session(session)
        print(f"[BG_NLU] intent={session.final_intent} sentiment={sentiment_result.label}")

        # Escalate if needed
        if esc_decision.should_escalate:
            try:
                await _do_escalation(websocket, session, esc_decision, language)
            except Exception:
                pass

    except Exception as e:
        print(f"[BG_NLU] error: {e}")


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
        if session.conversation_stage == "gathering_info":
            # Citizen confirmed basic understanding — advance to seeking_confirmation
            # and immediately ask for final registration confirmation.
            session.conversation_stage = "seeking_confirmation"
            confirm_asks = {
                "kn": f"ಸರಿ, ತಿಳಿಯಿತು! ನಿಮ್ಮ {(session.final_intent or 'ದೂರು').replace('_', ' ')} ಬಗ್ಗೆ ದೂರು ದಾಖಲಿಸಲೇ?",
                "hi": f"ठीक है! आपकी {(session.final_intent or 'शिकायत').replace('_', ' ')} दर्ज करूं?",
                "en": f"Got it! Shall I go ahead and register your {(session.final_intent or 'complaint').replace('_', ' ')}?",
            }
            ack_text = confirm_asks.get(language, confirm_asks["en"])
            tts_audio = ""
            try:
                tts_audio = await tts.synthesize(ack_text, language=language)
            except Exception:
                pass
            ai_turn = Turn(speaker="ai", raw_transcript=ack_text, tts_audio_b64=tts_audio)
            session.add_turn(ai_turn)
            await websocket.send_json({
                "type": "verification_result",
                "state": "gathering_confirmed",
                "ai_response": ack_text,
                "tts_audio_b64": tts_audio,
                "session_id": session.session_id,
                "conversation_stage": "seeking_confirmation",
            })
            # Send a fresh verification_prompt for the registration confirmation step
            confirm_prompt = _verification_engine.generate_verification_prompt(
                intent=session.final_intent or "other_grievance",
                entities={},
                language=language,
                district=session.district,
            )
            await websocket.send_json({
                "type": "verification_prompt",
                "text": confirm_prompt,
                "language": language,
                "district": session.district,
                "session_id": session.session_id,
                "conversation_stage": "seeking_confirmation",
            })
            print(f"[VERIFICATION] gathering_info confirmed — advancing to seeking_confirmation")
            return

        # seeking_confirmation or confirmed_ready confirmed — ready to create ticket on end_call
        session.conversation_stage = "confirmed_ready"
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
            "conversation_stage": "confirmed_ready",
        })
        print(f"[VERIFICATION] Confirmed — waiting for end_call to create ticket. Intent: {session.final_intent}")
        await log_event(
            session.session_id, "verification_confirmed", actor="citizen",
            payload={"intent": session.final_intent, "clarification_count": session.clarification_count},
        )

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


async def _handle_end_call(websocket: WebSocket, session: SessionState):
    """
    Citizen tapped End Call.
    1. Say "hold a moment…"  2. Create ticket  3. Ask for feedback rating.
    """
    language = session.user_language or session.detected_language

    # Step 1 — "hold a moment"
    hold_text = verification.get_end_call_message(language)
    hold_audio = ""
    try:
        hold_audio = await tts.synthesize(hold_text, language=language)
    except Exception:
        pass
    ai_turn = Turn(speaker="ai", raw_transcript=hold_text, tts_audio_b64=hold_audio)
    session.add_turn(ai_turn)
    await websocket.send_json({
        "type": "hold_on",
        "ai_response": hold_text,
        "tts_audio_b64": hold_audio,
    })

    # Step 2 — create ticket
    ticket_info = await ticket_service.create_ticket(session, "confirmed")
    await write_verified_interaction(session)
    session.conversation_stage = "ended"
    await log_event(
        session.session_id, "call_ended", actor="citizen",
        payload={"intent": session.final_intent, "ticket_id": getattr(ticket_info, "ticket_id", None)},
    )

    try:
        await websocket.send_json({
            "type": "ticket_created",
            "ticket": ticket_info.model_dump(mode="json"),
        })
    except Exception:
        pass

    # Step 3 — feedback request
    feedback_text = verification.get_feedback_request(language)
    feedback_audio = ""
    try:
        feedback_audio = await tts.synthesize(feedback_text, language=language)
    except Exception:
        pass
    feedback_turn = Turn(speaker="ai", raw_transcript=feedback_text, tts_audio_b64=feedback_audio)
    session.add_turn(feedback_turn)
    await websocket.send_json({
        "type": "feedback_request",
        "text": feedback_text,
        "tts_audio_b64": feedback_audio,
        "ticket_id": getattr(ticket_info, "ticket_id", None),
    })
    print(f"[END_CALL] Ticket created, feedback requested. Session: {session.session_id}")


async def _handle_feedback(websocket: WebSocket, session: SessionState, msg: dict):
    """Citizen submits a 1–5 star rating. Log it and say goodbye."""
    rating: int = msg.get("rating", 0)
    language = session.user_language or session.detected_language

    await log_event(
        session.session_id, "feedback_submitted", actor="citizen",
        payload={"rating": rating},
    )

    goodbye = {
        "kn": "ಧನ್ಯವಾದ! ನಿಮ್ಮ ಪ್ರತಿಕ್ರಿಯೆಗೆ ಧನ್ಯವಾದ. ಒಳ್ಳೆಯ ದಿನ ಆಗಲಿ!",
        "hi": "धन्यवाद! आपकी प्रतिक्रिया के लिए शुक्रिया। अच्छा दिन हो!",
        "en": "Thank you for your feedback! Have a great day!",
    }
    bye_text = goodbye.get(language, goodbye["en"])
    bye_audio = ""
    try:
        bye_audio = await tts.synthesize(bye_text, language=language)
    except Exception:
        pass
    bye_turn = Turn(speaker="ai", raw_transcript=bye_text, tts_audio_b64=bye_audio)
    session.add_turn(bye_turn)
    await websocket.send_json({
        "type": "call_ended",
        "ai_response": bye_text,
        "tts_audio_b64": bye_audio,
        "rating": rating,
    })
    print(f"[FEEDBACK] Rating {rating}/5 logged. Session: {session.session_id}")


async def _handle_agent_ws_reply(msg: dict) -> None:
    """Agent dashboard sends a voice reply to the citizen via agent WebSocket."""
    session_id = msg.get("session_id", "")
    text = msg.get("text", "").strip()
    if not session_id or not text:
        return

    session = await session_manager.get_session(session_id)
    language = session.detected_language if session else "en"

    tts_audio = ""
    try:
        tts_audio = await tts.synthesize(text, language=language)
    except Exception as exc:
        print(f"[AGENT_REPLY] TTS failed: {exc}")

    delivered = await send_to_citizen(session_id, {
        "type": "agent_audio",
        "text": text,
        "tts_audio_b64": tts_audio,
    })
    print(f"[AGENT_REPLY] Delivered to citizen {session_id}: {delivered}")


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
    sentiment_label = last_sentiment.get("label", "calm")
    await push_escalation(
        session_id=session.session_id,
        sentiment_intensity=sentiment_intensity,
        sentiment=sentiment_label,
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

    # Create ticket and notify citizen so they have a reference number
    ticket_info = await ticket_service.create_ticket(session, "escalated")
    try:
        await websocket.send_json({
            "type": "ticket_created",
            "ticket": ticket_info.model_dump(mode="json"),
        })
    except Exception:
        pass
