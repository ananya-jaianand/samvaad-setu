"""
Pre-built demo sessions for the Karnataka 1092 agent dashboard.

Five realistic escalated call scenarios covering:
  1. Mangaluru – Water supply crisis (high distress, tulu_coast dialect)
  2. Bengaluru  – Workplace harassment / women safety (fear, urban code-mix)
  3. Kalaburagi – Pension stopped for senior citizen (repeated clarification, Hindi)
  4. Mysuru     – Ration card address transfer (low ASR confidence, Mysuru dialect)
  5. Belagavi   – Garbage not collected (medium distress, north-Karnataka dialect)
"""

from datetime import datetime, timedelta
from models.session_model import SessionState, Turn, TurnSentiment

# Fixed prefixed UUIDs so the clear endpoint can identify demo sessions reliably
DEMO_SESSION_IDS = [
    "demo0001-aa11-bb22-cc33-dd4444444401",
    "demo0002-aa11-bb22-cc33-dd4444444402",
    "demo0003-aa11-bb22-cc33-dd4444444403",
    "demo0004-aa11-bb22-cc33-dd4444444404",
    "demo0005-aa11-bb22-cc33-dd4444444405",
]


def _ago(minutes: int) -> datetime:
    return datetime.utcnow() - timedelta(minutes=minutes)


def build_demo_sessions() -> list[SessionState]:
    sessions: list[SessionState] = []

    # ── Session 1 ─ Mangaluru ─ Water supply crisis ─────────────────────────
    s1 = SessionState(
        session_id=DEMO_SESSION_IDS[0],
        created_at=_ago(18),
        district="mangaluru",
        detected_language="kn",
        dialect_tag="tulu_coast",
        verification_state="escalated",
        clarification_count=1,
        is_escalated=True,
        escalation_reason="high_distress",
        escalation_summary="ನೀರು ಸರಬರಾಜು ಐದು ದಿನಗಳಿಂದ ಇಲ್ಲ — ಮನೆಯಲ್ಲಿ ಶಿಶು ಇದೆ, ತುರ್ತು ಪರಿಹಾರ ಬೇಕು",
        final_intent="water_supply_complaint",
        composite_confidence=0.74,
        turns=[
            Turn(
                turn_id="t1s1",
                timestamp=_ago(17),
                speaker="citizen",
                raw_transcript="ಆತ್, ನಮ್ಮ ಮನೆಗೆ ಐದು ದಿನದಿಂದ ನೀರು ಬರ್ತಿಲ್ಲ. ಪೈಪ್ ಒಡೆದಿದೆ ಅಂತ ಕಾಣ್ತದೆ. ಮನೆಯಲ್ಲಿ ಚಿಕ್ಕ ಮಗು ಇದೆ, ತುಂಬಾ ತೊಂದರೆ ಆಗ್ತಿದೆ.",
                asr_confidence=0.88,
                detected_language="kn",
                intent="water_supply_complaint",
                intent_entropy=0.21,
                sentiment=TurnSentiment(
                    label="distress", intensity=0.81,
                    text_component=0.75, prosodic_component=0.92,
                ),
                verification_state="pending",
            ),
            Turn(
                turn_id="t2s1",
                timestamp=_ago(16),
                speaker="ai",
                ai_rephrasing="ನಿಮ್ಮ ಮನೆಗೆ ಐದು ದಿನಗಳಿಂದ ನೀರಿನ ಸಂಪರ್ಕ ಇಲ್ಲ ಮತ್ತು ಚಿಕ್ಕ ಮಗುವಿರುವ ಕಾರಣ ತುರ್ತು ಪರಿಹಾರ ಬೇಕು — ನಾನು ಸರಿಯಾಗಿ ಅರ್ಥಮಾಡಿಕೊಂಡಿದ್ದೇನಾ?",
                asr_confidence=1.0,
                verification_state="pending",
            ),
            Turn(
                turn_id="t3s1",
                timestamp=_ago(15),
                speaker="citizen",
                raw_transcript="ಹೌದು, ಸರಿಯಾಗಿ ಹೇಳಿದಿರಿ. ನೆರೆಮನೆಯವರಿಗೂ ಅದೇ ಸಮಸ್ಯೆ ಇದೆ. ದಯಮಾಡಿ ಬೇಗ ಸರಿ ಮಾಡಿ.",
                asr_confidence=0.91,
                detected_language="kn",
                sentiment=TurnSentiment(
                    label="distress", intensity=0.89,
                    text_component=0.82, prosodic_component=0.98,
                ),
                verification_state="correct",
            ),
        ],
        sentiment_timeline=[
            {"turn_id": "t1s1", "timestamp": _ago(17).isoformat(), "label": "distress", "intensity": 0.81},
            {"turn_id": "t3s1", "timestamp": _ago(15).isoformat(), "label": "distress", "intensity": 0.89},
        ],
        confidence_history=[
            {"turn_id": "t1s1", "composite_score": 0.79, "asr_confidence": 0.88, "intent_entropy": 0.21},
            {"turn_id": "t3s1", "composite_score": 0.74, "asr_confidence": 0.91, "intent_entropy": 0.18},
        ],
    )
    sessions.append(s1)

    # ── Session 2 ─ Bengaluru ─ Workplace harassment / police complaint ──────
    s2 = SessionState(
        session_id=DEMO_SESSION_IDS[1],
        created_at=_ago(12),
        district="bengaluru_urban",
        detected_language="kn",
        dialect_tag="urban_kannada",
        verification_state="escalated",
        clarification_count=0,
        is_escalated=True,
        escalation_reason="high_distress",
        escalation_summary="Workplace harassment — caller in fear, requesting urgent police complaint filing",
        final_intent="police_complaint",
        composite_confidence=0.81,
        turns=[
            Turn(
                turn_id="t1s2",
                timestamp=_ago(11),
                speaker="citizen",
                raw_transcript="Hello, naanu help beku. Naanna office-alli naanna manager nanna harass maadtidaane. Itchche aagla, please police complaint haakabeku.",
                asr_confidence=0.85,
                detected_language="kn",
                intent="police_complaint",
                intent_entropy=0.15,
                sentiment=TurnSentiment(
                    label="fear", intensity=0.78,
                    text_component=0.80, prosodic_component=0.75,
                ),
                verification_state="pending",
            ),
            Turn(
                turn_id="t2s2",
                timestamp=_ago(10),
                speaker="ai",
                ai_rephrasing="ನಿಮ್ಮ ಕಚೇರಿಯಲ್ಲಿ ನಿಮ್ಮ ಮ್ಯಾನೇಜರ್ ನಿಮ್ಮನ್ನು ಕಿರುಕುಳ ನೀಡುತ್ತಿದ್ದಾರೆ ಮತ್ತು ನೀವು ಪೊಲೀಸ್ ದೂರು ದಾಖಲಿಸಲು ಸಹಾಯ ಬೇಕು — ಈ ಮಾಹಿತಿ ಸರಿಯೇ?",
                asr_confidence=1.0,
                verification_state="pending",
            ),
            Turn(
                turn_id="t3s2",
                timestamp=_ago(9),
                speaker="citizen",
                raw_transcript="Yes yes correct. Please hurry, I'm really scared right now.",
                asr_confidence=0.93,
                detected_language="en",
                sentiment=TurnSentiment(
                    label="fear", intensity=0.85,
                    text_component=0.88, prosodic_component=0.80,
                ),
                verification_state="correct",
            ),
        ],
        sentiment_timeline=[
            {"turn_id": "t1s2", "timestamp": _ago(11).isoformat(), "label": "fear", "intensity": 0.78},
            {"turn_id": "t3s2", "timestamp": _ago(9).isoformat(), "label": "fear", "intensity": 0.85},
        ],
        confidence_history=[
            {"turn_id": "t1s2", "composite_score": 0.82, "asr_confidence": 0.85, "intent_entropy": 0.15},
            {"turn_id": "t3s2", "composite_score": 0.81, "asr_confidence": 0.93, "intent_entropy": 0.12},
        ],
    )
    sessions.append(s2)

    # ── Session 3 ─ Kalaburagi ─ Senior citizen pension stopped (Hindi) ──────
    s3 = SessionState(
        session_id=DEMO_SESSION_IDS[2],
        created_at=_ago(25),
        district="kalaburagi",
        detected_language="hi",
        dialect_tag="hyderabad_ka",
        verification_state="escalated",
        clarification_count=2,
        is_escalated=True,
        escalation_reason="repeated_clarification",
        escalation_summary="वरिष्ठ नागरिक की पेंशन 3 महीने से बंद — बार-बार समझाने पर भी स्पष्टता नहीं",
        final_intent="pension_scheme",
        composite_confidence=0.52,
        turns=[
            Turn(
                turn_id="t1s3",
                timestamp=_ago(24),
                speaker="citizen",
                raw_transcript="Haan bhai, meri pension teen mahine se nahi aayi. Main 68 saal ka hoon, yahi meri aamdani hai.",
                asr_confidence=0.79,
                detected_language="hi",
                intent="pension_scheme",
                intent_entropy=0.38,
                sentiment=TurnSentiment(
                    label="concerned", intensity=0.55,
                    text_component=0.58, prosodic_component=0.50,
                ),
                verification_state="pending",
            ),
            Turn(
                turn_id="t2s3",
                timestamp=_ago(23),
                speaker="ai",
                ai_rephrasing="आपकी पेंशन पिछले तीन महीने से नहीं मिली है और यही आपकी एकमात्र आय है — क्या मैंने सही समझा?",
                asr_confidence=1.0,
                verification_state="pending",
            ),
            Turn(
                turn_id="t3s3",
                timestamp=_ago(22),
                speaker="citizen",
                raw_transcript="Haan, Atal Pension Yojana ke under aa rahi thi. Lekin kuch form bhar ke dene ke baad band ho gayi.",
                asr_confidence=0.72,
                detected_language="hi",
                sentiment=TurnSentiment(
                    label="concerned", intensity=0.58,
                    text_component=0.55, prosodic_component=0.62,
                ),
                verification_state="partial",
            ),
            Turn(
                turn_id="t4s3",
                timestamp=_ago(21),
                speaker="ai",
                ai_rephrasing="अटल पेंशन योजना के अंतर्गत फॉर्म जमा करने के बाद पेंशन बंद हुई — क्या यह सही है?",
                asr_confidence=1.0,
                verification_state="pending",
            ),
            Turn(
                turn_id="t5s3",
                timestamp=_ago(20),
                speaker="citizen",
                raw_transcript="Arey bhai, main teen baar baat kar chuka hoon yahan pe. Koi sunata nahi. Bahut takleef hai.",
                asr_confidence=0.68,
                detected_language="hi",
                sentiment=TurnSentiment(
                    label="distress", intensity=0.66,
                    text_component=0.70, prosodic_component=0.60,
                ),
                verification_state="incorrect",
            ),
        ],
        sentiment_timeline=[
            {"turn_id": "t1s3", "timestamp": _ago(24).isoformat(), "label": "concerned", "intensity": 0.55},
            {"turn_id": "t3s3", "timestamp": _ago(22).isoformat(), "label": "concerned", "intensity": 0.58},
            {"turn_id": "t5s3", "timestamp": _ago(20).isoformat(), "label": "distress",  "intensity": 0.66},
        ],
        confidence_history=[
            {"turn_id": "t1s3", "composite_score": 0.61, "asr_confidence": 0.79, "intent_entropy": 0.38},
            {"turn_id": "t3s3", "composite_score": 0.55, "asr_confidence": 0.72, "intent_entropy": 0.41},
            {"turn_id": "t5s3", "composite_score": 0.52, "asr_confidence": 0.68, "intent_entropy": 0.45},
        ],
    )
    sessions.append(s3)

    # ── Session 4 ─ Mysuru ─ Ration card address transfer (low confidence) ───
    s4 = SessionState(
        session_id=DEMO_SESSION_IDS[3],
        created_at=_ago(8),
        district="mysuru",
        detected_language="kn",
        dialect_tag="mysuru",
        verification_state="escalated",
        clarification_count=1,
        is_escalated=True,
        escalation_reason="low_confidence",
        escalation_summary="ರೇಷನ್ ಕಾರ್ಡ್ ವರ್ಗಾವಣೆ — ASR ಕಡಿಮೆ ವಿಶ್ವಾಸಾರ್ಹತೆ, ಫಾರ್ಮ್ ಮಾಹಿತಿ ಅಗತ್ಯ",
        final_intent="ration_card_issue",
        composite_confidence=0.41,
        turns=[
            Turn(
                turn_id="t1s4",
                timestamp=_ago(7),
                speaker="citizen",
                raw_transcript="ಆಗ್ಲಾ, ನಮ್ಮ ರೇಷನ್ ಕಾರ್ಡ್ ಇನ್ನೂ ಹಳೆ ಮನೆ ವಿಳಾಸದಲ್ಲಿ ಇದೆ. ಮದುವೆ ಆದ ಮೇಲೆ ವರ್ಗ ಮಾಡಿಸ್ಬೇಕು ಅಂತ ಕಛೇರಿಗೆ ಹೋದ್ರೆ ಅವ್ರು ಯಾವ್ದೋ ಫಾರ್ಮ್ ತರ್ರಿ ಅಂತ ಕಳ್ಸಿದ್ರು.",
                asr_confidence=0.58,
                detected_language="kn",
                intent="ration_card_issue",
                intent_entropy=0.52,
                sentiment=TurnSentiment(
                    label="confusion", intensity=0.42,
                    text_component=0.45, prosodic_component=0.38,
                ),
                verification_state="pending",
            ),
            Turn(
                turn_id="t2s4",
                timestamp=_ago(6),
                speaker="ai",
                ai_rephrasing="ಮದುವೆ ನಂತರ ರೇಷನ್ ಕಾರ್ಡ್ ಹೊಸ ವಿಳಾಸಕ್ಕೆ ವರ್ಗಾಯಿಸಲು ಬೇಕಾದ ಫಾರ್ಮ್ ಯಾವುದು ಎಂದು ತಿಳಿಯದೆ ಗೊಂದಲದಲ್ಲಿದ್ದೀರಾ?",
                asr_confidence=1.0,
                verification_state="pending",
            ),
            Turn(
                turn_id="t3s4",
                timestamp=_ago(5),
                speaker="citizen",
                raw_transcript="ಹೌದು, ಅದೇ ಅಂತ ಕಾಣ್ತದೆ. ಫಾರ್ಮ್ ಹೆಸರೇ ಗೊತ್ತಿಲ್ಲ.",
                asr_confidence=0.61,
                detected_language="kn",
                sentiment=TurnSentiment(
                    label="confusion", intensity=0.40,
                    text_component=0.42, prosodic_component=0.37,
                ),
                verification_state="correct",
            ),
        ],
        sentiment_timeline=[
            {"turn_id": "t1s4", "timestamp": _ago(7).isoformat(), "label": "confusion", "intensity": 0.42},
            {"turn_id": "t3s4", "timestamp": _ago(5).isoformat(), "label": "confusion", "intensity": 0.40},
        ],
        confidence_history=[
            {"turn_id": "t1s4", "composite_score": 0.44, "asr_confidence": 0.58, "intent_entropy": 0.52},
            {"turn_id": "t3s4", "composite_score": 0.41, "asr_confidence": 0.61, "intent_entropy": 0.49},
        ],
    )
    sessions.append(s4)

    # ── Session 5 ─ Belagavi ─ Garbage not collected (medium, North Karnataka)
    s5 = SessionState(
        session_id=DEMO_SESSION_IDS[4],
        created_at=_ago(35),
        district="belagavi",
        detected_language="kn",
        dialect_tag="north_karnataka",
        verification_state="escalated",
        clarification_count=1,
        is_escalated=True,
        escalation_reason="repeated_clarification",
        escalation_summary="ಎರಡು ವಾರದಿಂದ ಕಸ ತೆಗೆಯುತ್ತಿಲ್ಲ — BBMP ಮೂರು ಸಲ ಕರೆ ಮಾಡಿದರೂ ಪ್ರತಿಕ್ರಿಯೆ ಇಲ್ಲ",
        final_intent="sanitation_garbage",
        composite_confidence=0.63,
        turns=[
            Turn(
                turn_id="t1s5",
                timestamp=_ago(34),
                speaker="citizen",
                raw_transcript="ಆತ ಬಿಡ್ರಿ, ಎರಡು ವಾರದಿಂದ ನಮ್ಮ ಕಾಲೋನಿಯಲ್ಲಿ ಕಸ ತೆಗೀತಿಲ್ಲ. ಬಹಳ ದುರ್ಗಂಧ ಬರ್ತದೆ.",
                asr_confidence=0.84,
                detected_language="kn",
                intent="sanitation_garbage",
                intent_entropy=0.28,
                sentiment=TurnSentiment(
                    label="concerned", intensity=0.52,
                    text_component=0.55, prosodic_component=0.48,
                ),
                verification_state="pending",
            ),
            Turn(
                turn_id="t2s5",
                timestamp=_ago(33),
                speaker="ai",
                ai_rephrasing="ನಿಮ್ಮ ಕಾಲೋನಿಯಲ್ಲಿ ಎರಡು ವಾರಗಳಿಂದ ಕಸ ಸಂಗ್ರಹ ಆಗಿಲ್ಲ, ದುರ್ಗಂಧ ಇದೆ — ಸರಿಯೇ?",
                asr_confidence=1.0,
                verification_state="pending",
            ),
            Turn(
                turn_id="t3s5",
                timestamp=_ago(32),
                speaker="citizen",
                raw_transcript="ಹೌದ್ರಿ, ಮೂರ್ ಸಲ BBMP ಗೆ call ಮಾಡಿದ್ದೆ. ಯಾರೂ ಕೇಳಲ್ಲ.",
                asr_confidence=0.87,
                detected_language="kn",
                sentiment=TurnSentiment(
                    label="concerned", intensity=0.60,
                    text_component=0.62, prosodic_component=0.57,
                ),
                verification_state="correct",
            ),
        ],
        sentiment_timeline=[
            {"turn_id": "t1s5", "timestamp": _ago(34).isoformat(), "label": "concerned", "intensity": 0.52},
            {"turn_id": "t3s5", "timestamp": _ago(32).isoformat(), "label": "concerned", "intensity": 0.60},
        ],
        confidence_history=[
            {"turn_id": "t1s5", "composite_score": 0.67, "asr_confidence": 0.84, "intent_entropy": 0.28},
            {"turn_id": "t3s5", "composite_score": 0.63, "asr_confidence": 0.87, "intent_entropy": 0.31},
        ],
    )
    sessions.append(s5)

    return sessions


# Metadata for the queue (mirrors agent_queue.push_escalation meta schema)
DEMO_QUEUE_ENTRIES = [
    {
        "session_id": DEMO_SESSION_IDS[0],
        "sentiment_intensity": 0.89,
        "sentiment": "distress",
        "reason": "high_distress",
        "summary": "ನೀರು ಸರಬರಾಜು ಐದು ದಿನಗಳಿಂದ ಇಲ್ಲ — ಮನೆಯಲ್ಲಿ ಶಿಶು ಇದೆ",
        "district": "mangaluru",
        "language": "kn",
        "final_intent": "water_supply_complaint",
    },
    {
        "session_id": DEMO_SESSION_IDS[1],
        "sentiment_intensity": 0.85,
        "sentiment": "fear",
        "reason": "high_distress",
        "summary": "Workplace harassment — caller in fear, needs police complaint",
        "district": "bengaluru_urban",
        "language": "kn",
        "final_intent": "police_complaint",
    },
    {
        "session_id": DEMO_SESSION_IDS[2],
        "sentiment_intensity": 0.66,
        "sentiment": "concerned",
        "reason": "repeated_clarification",
        "summary": "पेंशन 3 महीने से बंद — 68 वर्षीय नागरिक, तीसरी बार कॉल",
        "district": "kalaburagi",
        "language": "hi",
        "final_intent": "pension_scheme",
    },
    {
        "session_id": DEMO_SESSION_IDS[3],
        "sentiment_intensity": 0.42,
        "sentiment": "confusion",
        "reason": "low_confidence",
        "summary": "ರೇಷನ್ ಕಾರ್ಡ್ ವರ್ಗಾವಣೆ — ASR ಕಡಿಮೆ ವಿಶ್ವಾಸಾರ್ಹತೆ",
        "district": "mysuru",
        "language": "kn",
        "final_intent": "ration_card_issue",
    },
    {
        "session_id": DEMO_SESSION_IDS[4],
        "sentiment_intensity": 0.60,
        "sentiment": "concerned",
        "reason": "repeated_clarification",
        "summary": "ಎರಡು ವಾರ ಕಸ ತೆಗೆದಿಲ್ಲ — BBMP ಮೂರು ಸಲ ಕರೆ, ಯಾರೂ ಸ್ಪಂದಿಸಿಲ್ಲ",
        "district": "belagavi",
        "language": "kn",
        "final_intent": "sanitation_garbage",
    },
]
