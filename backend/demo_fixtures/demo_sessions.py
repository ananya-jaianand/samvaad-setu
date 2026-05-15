"""
Pre-built demo sessions for the Karnataka 1092 agent dashboard.

Five realistic escalated call scenarios with rich turn-by-turn data:
  1. Mangaluru  – Water supply crisis (distress, tulu_coast dialect)
  2. Bengaluru  – Workplace harassment / women safety (fear, urban code-mix)
  3. Kalaburagi – Pension stopped, senior citizen (repeated clarification, Hindi)
  4. Mysuru     – Ration card address transfer (low ASR confidence)
  5. Belagavi   – Garbage not collected (medium urgency, north-Karnataka)
"""

from datetime import datetime, timedelta
from models.session_model import SessionState, Turn, TurnSentiment

DEMO_SESSION_IDS = [
    "demo0001-aa11-bb22-cc33-dd4444444401",
    "demo0002-aa11-bb22-cc33-dd4444444402",
    "demo0003-aa11-bb22-cc33-dd4444444403",
    "demo0004-aa11-bb22-cc33-dd4444444404",
    "demo0005-aa11-bb22-cc33-dd4444444405",
    "demo0006-aa11-bb22-cc33-dd4444444406",  # PII redaction demo
]


def _ago(minutes: int) -> datetime:
    return datetime.utcnow() - timedelta(minutes=minutes)


def build_demo_sessions() -> list[SessionState]:
    sessions: list[SessionState] = []

    # ── Session 1 ─ Mangaluru ─ Water supply crisis ─────────────────────────
    s1 = SessionState(
        session_id=DEMO_SESSION_IDS[0],
        created_at=_ago(22),
        district="mangaluru",
        detected_language="kn",
        dialect_tag="tulu_coast",
        verification_state="escalated",
        clarification_count=1,
        is_escalated=True,
        escalation_reason="high_distress",
        escalation_summary="No water supply for 5 days — infant at home, requesting emergency repair",
        final_intent="water_supply_complaint",
        composite_confidence=0.74,
        turns=[
            Turn(
                turn_id="t1s1", timestamp=_ago(21), speaker="citizen",
                raw_transcript="ಹಲೋ, 1092 ನಾ? ನಮ್ಮ ಮನೆಗೆ ಐದು ದಿನದಿಂದ ನೀರೇ ಬರ್ತಿಲ್ಲ. ತುಂಬಾ ತೊಂದರೆ ಆಗ್ತಿದೆ.",
                asr_confidence=0.91, detected_language="kn", intent="water_supply_complaint",
                intent_entropy=0.22,
                sentiment=TurnSentiment(label="calm", intensity=0.28, text_component=0.30, prosodic_component=0.25),
                verification_state="pending",
            ),
            Turn(
                turn_id="t2s1", timestamp=_ago(20), speaker="ai",
                ai_rephrasing="ನಿಮ್ಮ ಮನೆಗೆ ಐದು ದಿನಗಳಿಂದ ನೀರು ಬರ್ತಿಲ್ಲ ಅಂತ ಹೇಳ್ತಿದ್ದೀರಾ — ಯಾವ ಏರಿಯಾ ನೀವಿರೋದು?",
                asr_confidence=1.0, verification_state="pending",
            ),
            Turn(
                turn_id="t3s1", timestamp=_ago(19), speaker="citizen",
                raw_transcript="ನಮ್ ಮನೆ ಬಂದರ್ ರಸ್ತೆ ಹತ್ರ ಇದೆ. ನಮ್ ಪೈಪ್ ಒಡೆದಿದೆ ಅಂತ ಕಾಣ್ತದೆ. ನೆರೆಮನೆಯವ್ರಿಗೂ ಅದೇ ಸಮಸ್ಯೆ ಇದೆ. ಮನೆಯಲ್ಲಿ ಚಿಕ್ಕ ಮಗು ಇದೆ, ದಿನಾ ನೀರಿಗೆ ದೂರ ಹೋಗ್ಬೇಕಾಗ್ತಿದೆ.",
                asr_confidence=0.88, detected_language="kn", intent="water_supply_complaint",
                intent_entropy=0.18,
                sentiment=TurnSentiment(label="urgency", intensity=0.52, text_component=0.50, prosodic_component=0.55),
                verification_state="pending",
            ),
            Turn(
                turn_id="t4s1", timestamp=_ago(18), speaker="ai",
                ai_rephrasing="ಬಂದರ್ ರಸ್ತೆ ಏರಿಯಾದಲ್ಲಿ ಪೈಪ್ ಒಡೆದು ನೀರು ಬರ್ತಿಲ್ಲ, ಮನೆಯಲ್ಲಿ ಶಿಶು ಇದ್ದಾರೆ ಮತ್ತು ನೆರೆಮನೆಗಳಿಗೂ ಅದೇ ತೊಂದರೆ — ಸರಿಯಾ?",
                asr_confidence=1.0, verification_state="pending",
            ),
            Turn(
                turn_id="t5s1", timestamp=_ago(17), speaker="citizen",
                raw_transcript="ಹೌದು ಸರಿಯಾಗಿ ಹೇಳಿದಿರಿ. ಆದ್ರೆ ನಾನು ಮೊದ್ಲೇ KUWSDB ಗೆ ಕಾಲ್ ಮಾಡಿದ್ದೆ, ಯಾರೂ ಬರ್ಲಿಲ್ಲ. ಮಗು ಜ್ವರ ಬಂದಿದೆ, ಕುಡಿಯೋಕೆ ನೀರೇ ಇಲ್ಲ.",
                asr_confidence=0.92, detected_language="kn",
                sentiment=TurnSentiment(label="distress", intensity=0.76, text_component=0.72, prosodic_component=0.82),
                verification_state="correct",
            ),
            Turn(
                turn_id="t6s1", timestamp=_ago(16), speaker="ai",
                ai_rephrasing="KUWSDB ಗೆ ಮೊದಲೇ ಕಾಲ್ ಮಾಡಿದ್ದರೂ ಸ್ಪಂದನೆ ಇಲ್ಲ, ಮಗುವಿಗೆ ಜ್ವರ ಬೇರೆ ಇದೆ — ತುರ್ತಾಗಿ ಮೇಲಿನ ಅಧಿಕಾರಿಗಳಿಗೆ ದೂರು ಕಳಿಸ್ತೇನೆ.",
                asr_confidence=1.0, verification_state="pending",
            ),
            Turn(
                turn_id="t7s1", timestamp=_ago(15), speaker="citizen",
                raw_transcript="ಪ್ಲೀಸ್ ಬೇಗ ಮಾಡಿ. ನಾವು ತುಂಬಾ ಕಷ್ಟ ಪಡ್ತಿದ್ದೇವೆ. ಮಗು ಅಳ್ತಿದೆ.",
                asr_confidence=0.89, detected_language="kn",
                sentiment=TurnSentiment(label="distress", intensity=0.89, text_component=0.84, prosodic_component=0.96),
                verification_state="correct",
            ),
        ],
        sentiment_timeline=[
            {"turn_id": "t1s1", "timestamp": _ago(21).isoformat(), "label": "calm",    "intensity": 0.28},
            {"turn_id": "t3s1", "timestamp": _ago(19).isoformat(), "label": "urgency", "intensity": 0.52},
            {"turn_id": "t5s1", "timestamp": _ago(17).isoformat(), "label": "distress","intensity": 0.76},
            {"turn_id": "t7s1", "timestamp": _ago(15).isoformat(), "label": "distress","intensity": 0.89},
        ],
        confidence_history=[
            {"turn_id": "t1s1", "composite_score": 0.84, "asr_confidence": 0.91, "intent_entropy": 0.22},
            {"turn_id": "t3s1", "composite_score": 0.81, "asr_confidence": 0.88, "intent_entropy": 0.18},
            {"turn_id": "t5s1", "composite_score": 0.74, "asr_confidence": 0.92, "intent_entropy": 0.15},
            {"turn_id": "t7s1", "composite_score": 0.71, "asr_confidence": 0.89, "intent_entropy": 0.14},
        ],
    )
    sessions.append(s1)

    # ── Session 2 ─ Bengaluru ─ Workplace harassment ─────────────────────────
    s2 = SessionState(
        session_id=DEMO_SESSION_IDS[1],
        created_at=_ago(15),
        district="bengaluru_urban",
        detected_language="kn",
        dialect_tag="urban_kannada",
        verification_state="escalated",
        clarification_count=0,
        is_escalated=True,
        escalation_reason="high_distress",
        escalation_summary="Workplace harassment, caller in fear — urgent police complaint required",
        final_intent="police_grievance",
        composite_confidence=0.82,
        turns=[
            Turn(
                turn_id="t1s2", timestamp=_ago(14), speaker="citizen",
                raw_transcript="Hello, please help me. My manager is harassing me at office, I'm really scared.",
                asr_confidence=0.94, detected_language="en", intent="police_grievance",
                intent_entropy=0.14,
                sentiment=TurnSentiment(label="fear", intensity=0.62, text_component=0.65, prosodic_component=0.58),
                verification_state="pending",
            ),
            Turn(
                turn_id="t2s2", timestamp=_ago(13), speaker="ai",
                ai_rephrasing="ನಿಮ್ಮ ಮ್ಯಾನೇಜರ್ ನಿಮ್ಮನ್ನು ಕಚೇರಿಯಲ್ಲಿ ಕಿರುಕುಳ ನೀಡುತ್ತಿದ್ದಾರೆ ಎಂದು ಅರ್ಥ — ಇದು ದೈಹಿಕ ಅಥವಾ ಮಾನಸಿಕ ಕಿರುಕುಳ?",
                asr_confidence=1.0, verification_state="pending",
            ),
            Turn(
                turn_id="t3s2", timestamp=_ago(12), speaker="citizen",
                raw_transcript="Both. He shouts at me, throws files. Yesterday he blocked the exit when I tried to leave. I have voice recordings.",
                asr_confidence=0.91, detected_language="en",
                sentiment=TurnSentiment(label="fear", intensity=0.75, text_component=0.78, prosodic_component=0.71),
                verification_state="pending",
            ),
            Turn(
                turn_id="t4s2", timestamp=_ago(11), speaker="ai",
                ai_rephrasing="Your manager physically blocked the exit and has verbally abused you — you have recordings as evidence. I'll register a formal complaint. Should I also alert the women's helpline?",
                asr_confidence=1.0, verification_state="pending",
            ),
            Turn(
                turn_id="t5s2", timestamp=_ago(10), speaker="citizen",
                raw_transcript="Yes please. I'm still at office, I don't feel safe. Please send someone quickly.",
                asr_confidence=0.93, detected_language="en",
                sentiment=TurnSentiment(label="fear", intensity=0.85, text_component=0.88, prosodic_component=0.81),
                verification_state="correct",
            ),
            Turn(
                turn_id="t6s2", timestamp=_ago(9), speaker="ai",
                ai_rephrasing="Escalating to police and women's safety cell immediately. Please stay on the line and move to a public area inside the office.",
                asr_confidence=1.0, verification_state="pending",
            ),
        ],
        sentiment_timeline=[
            {"turn_id": "t1s2", "timestamp": _ago(14).isoformat(), "label": "fear",    "intensity": 0.62},
            {"turn_id": "t3s2", "timestamp": _ago(12).isoformat(), "label": "fear",    "intensity": 0.75},
            {"turn_id": "t5s2", "timestamp": _ago(10).isoformat(), "label": "fear",    "intensity": 0.85},
            {"turn_id": "t6s2", "timestamp": _ago(9).isoformat(),  "label": "distress","intensity": 0.88},
        ],
        confidence_history=[
            {"turn_id": "t1s2", "composite_score": 0.88, "asr_confidence": 0.94, "intent_entropy": 0.14},
            {"turn_id": "t3s2", "composite_score": 0.85, "asr_confidence": 0.91, "intent_entropy": 0.12},
            {"turn_id": "t5s2", "composite_score": 0.82, "asr_confidence": 0.93, "intent_entropy": 0.11},
        ],
    )
    sessions.append(s2)

    # ── Session 3 ─ Kalaburagi ─ Pension stopped (Hindi, repeated clarification)
    s3 = SessionState(
        session_id=DEMO_SESSION_IDS[2],
        created_at=_ago(30),
        district="kalaburagi",
        detected_language="hi",
        dialect_tag="hyderabad_ka",
        verification_state="escalated",
        clarification_count=2,
        is_escalated=True,
        escalation_reason="repeated_clarification",
        escalation_summary="Senior citizen pension stopped 3 months — 3rd call, no resolution",
        final_intent="pension_scheme",
        composite_confidence=0.51,
        turns=[
            Turn(
                turn_id="t1s3", timestamp=_ago(29), speaker="citizen",
                raw_transcript="Haan bhai, meri pension teen mahine se nahi aayi. Main 68 saal ka hoon, ghar mein aur koi nahi.",
                asr_confidence=0.82, detected_language="hi", intent="pension_scheme",
                intent_entropy=0.35,
                sentiment=TurnSentiment(label="calm", intensity=0.22, text_component=0.24, prosodic_component=0.19),
                verification_state="pending",
            ),
            Turn(
                turn_id="t2s3", timestamp=_ago(28), speaker="ai",
                ai_rephrasing="आपकी पेंशन पिछले तीन महीने से नहीं मिली है और आप अकेले रहते हैं — किस योजना के अंतर्गत पेंशन आती थी?",
                asr_confidence=1.0, verification_state="pending",
            ),
            Turn(
                turn_id="t3s3", timestamp=_ago(27), speaker="citizen",
                raw_transcript="Sandhya Suraksha thi. Kuch mahine pehle ek form bhar ke diya tha, tab se band ho gayi. Mera Aadhaar 7741 8823 4415 linked hai, phir bhi nahi aayi.",
                asr_confidence=0.76, detected_language="hi",
                sentiment=TurnSentiment(label="urgency", intensity=0.44, text_component=0.42, prosodic_component=0.47),
                verification_state="partially_correct",
            ),
            Turn(
                turn_id="t4s3", timestamp=_ago(26), speaker="ai",
                ai_rephrasing="संध्या सुरक्षा पेंशन, फॉर्म भरने के बाद बंद हुई — आधार लिंक है, फिर भी रुकी है — बैंक खाता किस बैंक में है?",
                asr_confidence=1.0, verification_state="pending",
            ),
            Turn(
                turn_id="t5s3", timestamp=_ago(25), speaker="citizen",
                raw_transcript="Haan link hai, main pehle bhi do baar call kar chuka hoon. Ek baar bola document bhejo, bheja. Phir bola office aao, gaya. Koi kaam nahi hua.",
                asr_confidence=0.71, detected_language="hi",
                sentiment=TurnSentiment(label="urgency", intensity=0.60, text_component=0.62, prosodic_component=0.57),
                verification_state="incorrect",
            ),
            Turn(
                turn_id="t6s3", timestamp=_ago(24), speaker="ai",
                ai_rephrasing="आपने दो बार पहले भी शिकायत दर्ज की थी — दस्तावेज भेजे, कार्यालय भी गए, फिर भी हल नहीं — क्या यह सही है?",
                asr_confidence=1.0, verification_state="pending",
            ),
            Turn(
                turn_id="t7s3", timestamp=_ago(23), speaker="citizen",
                raw_transcript="Bilkul sahi. Arey bhai teen mahine se kha kya raha hoon main? Yahi meri zindagi ki kamai thi. Bahut takleef hai.",
                asr_confidence=0.68, detected_language="hi",
                sentiment=TurnSentiment(label="distress", intensity=0.72, text_component=0.76, prosodic_component=0.67),
                verification_state="correct",
            ),
            Turn(
                turn_id="t8s3", timestamp=_ago(22), speaker="ai",
                ai_rephrasing="मैं इस केस को वरिष्ठ अधिकारी को तुरंत भेज रहा हूँ — आपका रेफरेंस नंबर नोट कर लें।",
                asr_confidence=1.0, verification_state="pending",
            ),
        ],
        sentiment_timeline=[
            {"turn_id": "t1s3", "timestamp": _ago(29).isoformat(), "label": "calm",    "intensity": 0.22},
            {"turn_id": "t3s3", "timestamp": _ago(27).isoformat(), "label": "urgency", "intensity": 0.44},
            {"turn_id": "t5s3", "timestamp": _ago(25).isoformat(), "label": "urgency", "intensity": 0.60},
            {"turn_id": "t7s3", "timestamp": _ago(23).isoformat(), "label": "distress","intensity": 0.72},
        ],
        confidence_history=[
            {"turn_id": "t1s3", "composite_score": 0.68, "asr_confidence": 0.82, "intent_entropy": 0.35},
            {"turn_id": "t3s3", "composite_score": 0.58, "asr_confidence": 0.76, "intent_entropy": 0.40},
            {"turn_id": "t5s3", "composite_score": 0.53, "asr_confidence": 0.71, "intent_entropy": 0.44},
            {"turn_id": "t7s3", "composite_score": 0.51, "asr_confidence": 0.68, "intent_entropy": 0.47},
        ],
    )
    sessions.append(s3)

    # ── Session 4 ─ Mysuru ─ Ration card address transfer (low confidence) ───
    s4 = SessionState(
        session_id=DEMO_SESSION_IDS[3],
        created_at=_ago(10),
        district="mysuru",
        detected_language="kn",
        dialect_tag="mysuru",
        verification_state="escalated",
        clarification_count=1,
        is_escalated=True,
        escalation_reason="low_confidence",
        escalation_summary="Ration card address update post-marriage — low ASR confidence, form guidance needed",
        final_intent="ration_card_correction",
        composite_confidence=0.43,
        turns=[
            Turn(
                turn_id="t1s4", timestamp=_ago(9), speaker="citizen",
                raw_transcript="ಆಗ್ಲಾ, ನಮ್ಮ ರೇಷನ್ ಕಾರ್ಡ್ ಇನ್ನೂ ಹಳೆ ಮನೆ ವಿಳಾಸದಲ್ಲಿ ಇದೆ. ಮದ್ವೆ ಆಯ್ತು ಈಗ ಹೊಸ ಮನೆ.",
                asr_confidence=0.61, detected_language="kn", intent="ration_card_correction",
                intent_entropy=0.50,
                sentiment=TurnSentiment(label="calm", intensity=0.18, text_component=0.20, prosodic_component=0.16),
                verification_state="pending",
            ),
            Turn(
                turn_id="t2s4", timestamp=_ago(8), speaker="ai",
                ai_rephrasing="ಮದುವೆ ನಂತರ ರೇಷನ್ ಕಾರ್ಡ್ ಹೊಸ ವಿಳಾಸಕ್ಕೆ ವರ್ಗಾಯಿಸಬೇಕು — ನಿಮ್ಮ ಹಳೆಯ ಜಿಲ್ಲೆ ಯಾವುದು?",
                asr_confidence=1.0, verification_state="pending",
            ),
            Turn(
                turn_id="t3s4", timestamp=_ago(7), speaker="citizen",
                raw_transcript="ಹಳೆ ಮನೆ ಮೈಸೂರೇ, ಹೊಸ ಮನೆನೂ ಮೈಸೂರೇ. ಕಛೇರಿಗೆ ಹೋದ್ರೆ ಯಾವ್ದೋ ಫಾರ್ಮ್ ತರ್ರಿ ಅಂತ ಹೇಳಿ ಕಳ್ಸಿದ್ರು, ಆ ಫಾರ್ಮ್ ಎಲ್ಲಿ ಸಿಗ್ತದೆ ಗೊತ್ತಿಲ್ಲ.",
                asr_confidence=0.58, detected_language="kn",
                sentiment=TurnSentiment(label="confusion", intensity=0.42, text_component=0.44, prosodic_component=0.39),
                verification_state="partially_correct",
            ),
            Turn(
                turn_id="t4s4", timestamp=_ago(6), speaker="ai",
                ai_rephrasing="ಮೈಸೂರಿನಲ್ಲೇ ವರ್ಗ — RC-6 ಫಾರ್ಮ್ ಬೇಕು. ಅದು ಆಹಾರ ಇಲಾಖೆ ಕಚೇರಿ ಅಥವಾ ಸೇವಾ ಸಿಂಧು ಪೋರ್ಟಲ್ ನಲ್ಲಿ ಸಿಗ್ತದೆ — ಅರ್ಥ ಆಯ್ತಾ?",
                asr_confidence=1.0, verification_state="pending",
            ),
            Turn(
                turn_id="t5s4", timestamp=_ago(5), speaker="citizen",
                raw_transcript="ಸ್ವಲ್ಪ ಅರ್ಥ ಆಯ್ತು. ಆದ್ರೆ ಸೇವಾ ಸಿಂಧು ಅಂದ್ರೆ ಏನು? ಅದು online ನಾ? ನನಗೆ ಫೋನ್ ಎಲ್ಲ ಅಷ್ಟು ಗೊತ್ತಾಗೋದಿಲ್ಲ.",
                asr_confidence=0.55, detected_language="kn",
                sentiment=TurnSentiment(label="confusion", intensity=0.38, text_component=0.40, prosodic_component=0.35),
                verification_state="correct",
            ),
            Turn(
                turn_id="t6s4", timestamp=_ago(4), speaker="ai",
                ai_rephrasing="ಸೇವಾ ಸಿಂಧು ಒಂದು ಸರ್ಕಾರಿ ವೆಬ್ಸೈಟ್. ಆದ್ರೆ ನೀವು ನೇರ ಕಚೇರಿಗೆ ಹೋಗಿ RC-6 ತಗೊಳ್ಳಬಹುದು — ಒಬ್ಬ ಅಧಿಕಾರಿ ನಿಮ್ಮನ್ನ ಸಂಪರ್ಕಿಸ್ತಾರೆ.",
                asr_confidence=1.0, verification_state="pending",
            ),
        ],
        sentiment_timeline=[
            {"turn_id": "t1s4", "timestamp": _ago(9).isoformat(), "label": "calm",      "intensity": 0.18},
            {"turn_id": "t3s4", "timestamp": _ago(7).isoformat(), "label": "confusion", "intensity": 0.42},
            {"turn_id": "t5s4", "timestamp": _ago(5).isoformat(), "label": "confusion", "intensity": 0.38},
            {"turn_id": "t6s4", "timestamp": _ago(4).isoformat(), "label": "calm",      "intensity": 0.25},
        ],
        confidence_history=[
            {"turn_id": "t1s4", "composite_score": 0.52, "asr_confidence": 0.61, "intent_entropy": 0.50},
            {"turn_id": "t3s4", "composite_score": 0.46, "asr_confidence": 0.58, "intent_entropy": 0.53},
            {"turn_id": "t5s4", "composite_score": 0.43, "asr_confidence": 0.55, "intent_entropy": 0.56},
        ],
    )
    sessions.append(s4)

    # ── Session 5 ─ Belagavi ─ Garbage not collected ──────────────────────────
    s5 = SessionState(
        session_id=DEMO_SESSION_IDS[4],
        created_at=_ago(42),
        district="belagavi",
        detected_language="kn",
        dialect_tag="north_karnataka",
        verification_state="escalated",
        clarification_count=1,
        is_escalated=True,
        escalation_reason="repeated_clarification",
        escalation_summary="14 days no garbage collection — BBMP called 3 times, no response",
        final_intent="sanitation_garbage",
        composite_confidence=0.64,
        turns=[
            Turn(
                turn_id="t1s5", timestamp=_ago(41), speaker="citizen",
                raw_transcript="ಆತ ಬಿಡ್ರಿ, ನಮ್ಮ ಬಡಾವಣೆಯಲ್ಲಿ ಎರಡು ವಾರದಿಂದ ಕಸ ತೆಗೀತಿಲ್ಲ. ರಸ್ತೇಲಿ ಕಸ ರಾಶಿ ಆಗಿದೆ.",
                asr_confidence=0.87, detected_language="kn", intent="sanitation_garbage",
                intent_entropy=0.26,
                sentiment=TurnSentiment(label="calm", intensity=0.24, text_component=0.26, prosodic_component=0.21),
                verification_state="pending",
            ),
            Turn(
                turn_id="t2s5", timestamp=_ago(40), speaker="ai",
                ai_rephrasing="ನಿಮ್ಮ ಬಡಾವಣೆಯಲ್ಲಿ ಎರಡು ವಾರಗಳಿಂದ ಕಸ ಸಂಗ್ರಹ ಆಗ್ತಿಲ್ಲ — ಯಾವ ಬಡಾವಣೆ ಮತ್ತು ಮೊದಲು BBMP ಗೆ ದೂರು ಕೊಟ್ಟಿದ್ದೀರಾ?",
                asr_confidence=1.0, verification_state="pending",
            ),
            Turn(
                turn_id="t3s5", timestamp=_ago(39), speaker="citizen",
                raw_transcript="ಕ್ಯಾಂಪ್ ಏರಿಯಾ. ಹೌದ್ರಿ ಮೂರ್ ಸಲ BBMP ಗೆ call ಮಾಡಿದ್ದೆ. ಒಂದ್ ಸಲ ಗಾಡಿ ಬರ್ತದೆ ಅಂದ್ರು, ಬರ್ಲಿಲ್ಲ.",
                asr_confidence=0.89, detected_language="kn",
                sentiment=TurnSentiment(label="urgency", intensity=0.48, text_component=0.50, prosodic_component=0.45),
                verification_state="partially_correct",
            ),
            Turn(
                turn_id="t4s5", timestamp=_ago(38), speaker="ai",
                ai_rephrasing="ಕ್ಯಾಂಪ್ ಏರಿಯಾದಲ್ಲಿ ೧೪ ದಿನ ಕಸ ತೆಗೆದಿಲ್ಲ, ೩ ಸಲ BBMP ಗೆ ಕರೆ ಮಾಡಿದ್ರೂ ಗಾಡಿ ಬಂದಿಲ್ಲ — ಸರಿಯಾ?",
                asr_confidence=1.0, verification_state="pending",
            ),
            Turn(
                turn_id="t5s5", timestamp=_ago(37), speaker="citizen",
                raw_transcript="ಹೌದ್ರಿ ಸರಿ. ಮಳೆ ಬೇರೆ ಬರ್ತದೆ, ಕಸ ಕೊಳ್ಳೆ ಹೋಗ್ತದೆ. ರೋಗ ಬರ್ತದೆ ಅನ್ನೋ ಭಯ ಇದೆ.",
                asr_confidence=0.85, detected_language="kn",
                sentiment=TurnSentiment(label="urgency", intensity=0.60, text_component=0.62, prosodic_component=0.57),
                verification_state="correct",
            ),
            Turn(
                turn_id="t6s5", timestamp=_ago(36), speaker="ai",
                ai_rephrasing="ಮಳೆ ಮತ್ತು ಆರೋಗ್ಯ ಭಯ ಇರುವ ಕಾರಣ ಇದನ್ನ ತುರ್ತು ದೂರು ಆಗಿ BBMP ಮೇಲಿನ ಅಧಿಕಾರಿಗೆ ಕಳಿಸ್ತೇನೆ.",
                asr_confidence=1.0, verification_state="pending",
            ),
        ],
        sentiment_timeline=[
            {"turn_id": "t1s5", "timestamp": _ago(41).isoformat(), "label": "calm",    "intensity": 0.24},
            {"turn_id": "t3s5", "timestamp": _ago(39).isoformat(), "label": "urgency", "intensity": 0.48},
            {"turn_id": "t5s5", "timestamp": _ago(37).isoformat(), "label": "urgency", "intensity": 0.60},
            {"turn_id": "t6s5", "timestamp": _ago(36).isoformat(), "label": "urgency", "intensity": 0.58},
        ],
        confidence_history=[
            {"turn_id": "t1s5", "composite_score": 0.72, "asr_confidence": 0.87, "intent_entropy": 0.26},
            {"turn_id": "t3s5", "composite_score": 0.68, "asr_confidence": 0.89, "intent_entropy": 0.28},
            {"turn_id": "t5s5", "composite_score": 0.64, "asr_confidence": 0.85, "intent_entropy": 0.31},
        ],
    )
    sessions.append(s5)

    # ── Session 6 ─ Hubballi-Dharwad ─ HESCOM wrong billing (PII redaction demo)
    # Citizen volunteers name + phone in the first turn.
    # raw_transcript carries the original PII; NLU receives a redacted copy
    # (CITIZEN_NAME_1, PHONE_1) when PII_REDACTION_ENABLED=true.
    s6 = SessionState(
        session_id=DEMO_SESSION_IDS[5],
        created_at=_ago(35),
        district="hubballi_dharwad",
        detected_language="kn",
        dialect_tag="north_karnataka",
        verification_state="escalated",
        clarification_count=1,
        is_escalated=True,
        escalation_reason="repeated_clarification",
        escalation_summary="HESCOM bill ₹8,400 vs meter reading 1847 units — office visit unresolved · PII redacted before NLU: CITIZEN_NAME_1 + PHONE_1",
        final_intent="bescom_billing",
        composite_confidence=0.67,
        turns=[
            Turn(
                turn_id="t1s6", timestamp=_ago(34), speaker="citizen",
                raw_transcript="ನನ್ನ ಹೆಸರು ರಮೇಶ ಪಾಟೀಲ್, ಮೊಬೈಲ್ 9844567890. ವಿದ್ಯಾನಗರ ಹುಬ್ಬಳ್ಳಿ ನಲ್ಲಿ ನಮ್ಮ HESCOM ಬಿಲ್ ₹8,400 ಬಂದಿದೆ, ಯಾವ್ತ್ತೂ ₹600 ಮೀರ್ತಿರ್ಲಿಲ್ಲ",
                asr_confidence=0.89, detected_language="kn", intent="bescom_billing",
                intent_entropy=0.28,
                sentiment=TurnSentiment(label="calm", intensity=0.20, text_component=0.22, prosodic_component=0.17),
                verification_state="pending",
            ),
            Turn(
                turn_id="t2s6", timestamp=_ago(33), speaker="ai",
                ai_rephrasing="ವಿದ್ಯಾನಗರ ಹುಬ್ಬಳ್ಳಿ ನಲ್ಲಿ HESCOM ಬಿಲ್ ₹8,400 ಬಂದಿದೆ, ಸಾಮಾನ್ಯ ₹600 ಬರ್ತಿತ್ತು ಅಂತ ಹೇಳ್ತಿದ್ದೀರಾ. ನಿಮ್ಮ ಮೀಟರ್ ರೀಡಿಂಗ್ ಬಿಲ್ ನಲ್ಲಿ ಬರ್ದ ಅಂಕಿ ಜೊತೆ ಹೊಂದ್ತಿದೆಯಾ?",
                asr_confidence=1.0, verification_state="pending",
            ),
            Turn(
                turn_id="t3s6", timestamp=_ago(32), speaker="citizen",
                raw_transcript="ಇಲ್ಲ ಸ್ವಾಮಿ. ಮೀಟರ್ ಲ್ಲಿ 1847 ಯೂನಿಟ್ ತೋರ್ಸ್ತಿದೆ, ಬಿಲ್ ನಲ್ಲಿ 4200 ಅಂತ ಬಿಟ್ಟಿದ್ದಾರೆ. HESCOM ಕಚೇರಿಗೆ ಹೋಗಿದ್ದೆ, ಅವ್ರು ಕಂಪ್ಯೂಟರ್ ಎರರ್ ಅಂದ್ರು ಆದ್ರೆ ಕರೆಕ್ಟ್ ಮಾಡ್ಲಿಲ್ಲ",
                asr_confidence=0.86, detected_language="kn", intent="bescom_billing",
                intent_entropy=0.24,
                sentiment=TurnSentiment(label="urgency", intensity=0.45, text_component=0.47, prosodic_component=0.42),
                verification_state="pending",
            ),
            Turn(
                turn_id="t4s6", timestamp=_ago(31), speaker="ai",
                ai_rephrasing="ಮೀಟರ್ 1847 ಯೂನಿಟ್ ಆದ್ರೆ ಬಿಲ್ 4200 ಯೂನಿಟ್ ತೋರ್ಸ್ತಿದೆ — HESCOM ಕಚೇರಿ ಭೇಟಿ ಮಾಡಿದ್ರೂ ತಿದ್ದಲಿಲ್ಲ — ಇದು ಸರಿಯಾಗಿ ಹೇಳಿದ್ದೀನಾ?",
                asr_confidence=1.0, verification_state="pending",
            ),
            Turn(
                turn_id="t5s6", timestamp=_ago(30), speaker="citizen",
                raw_transcript="ಹೌದ್ರಿ ಸರಿ ಹೇಳಿದ್ರಿ. ₹8,400 ಕಟ್ಟಲ್ಲ ಬಿಡ್ರಿ, ನಾನು 30 ವರ್ಷದಿಂದ ಅಲ್ಲಿದ್ದೇನೆ, ಬಿಲ್ ಕಟ್ಟೋ ರೆಕಾರ್ಡ್ ಇದೆ. ದೂರು ಕೊಡ್ರಿ",
                asr_confidence=0.91, detected_language="kn",
                sentiment=TurnSentiment(label="urgency", intensity=0.58, text_component=0.60, prosodic_component=0.55),
                verification_state="correct",
            ),
            Turn(
                turn_id="t6s6", timestamp=_ago(29), speaker="ai",
                ai_rephrasing="30 ವರ್ಷದ ಉತ್ತಮ ಪಾವತಿ ದಾಖಲೆ ಇರುವ ನಿಮ್ಮ ಪ್ರಕರಣ HESCOM ಹಿರಿಯ ಅಧಿಕಾರಿ ಮತ್ತು ಕರ್ನಾಟಕ ವಿದ್ಯುತ್ ನಿಯಂತ್ರಣ ಆಯೋಗಕ್ಕೆ ದೂರು ಮಾಡ್ತೇನೆ.",
                asr_confidence=1.0, verification_state="pending",
            ),
        ],
        sentiment_timeline=[
            {"turn_id": "t1s6", "timestamp": _ago(34).isoformat(), "label": "calm",    "intensity": 0.20},
            {"turn_id": "t3s6", "timestamp": _ago(32).isoformat(), "label": "urgency", "intensity": 0.45},
            {"turn_id": "t5s6", "timestamp": _ago(30).isoformat(), "label": "urgency", "intensity": 0.58},
            {"turn_id": "t6s6", "timestamp": _ago(29).isoformat(), "label": "urgency", "intensity": 0.55},
        ],
        confidence_history=[
            {"turn_id": "t1s6", "composite_score": 0.74, "asr_confidence": 0.89, "intent_entropy": 0.28},
            {"turn_id": "t3s6", "composite_score": 0.70, "asr_confidence": 0.86, "intent_entropy": 0.24},
            {"turn_id": "t5s6", "composite_score": 0.67, "asr_confidence": 0.91, "intent_entropy": 0.22},
        ],
    )
    sessions.append(s6)

    return sessions


# English (and Hindi) translations for demo turns — used by the agent dashboard
# language toggle. Keyed by session_id → turn_id → lang → text.
DEMO_TURN_TRANSLATIONS: dict[str, dict[str, dict[str, str]]] = {
    DEMO_SESSION_IDS[0]: {  # Mangaluru — water supply (Kannada)
        "t1s1": {
            "en": "Hello, is this 1092? We haven't had any water at our home for five days. It's causing a lot of trouble.",
            "hi": "हेलो, 1092 है क्या? हमारे घर में पाँच दिनों से पानी नहीं आया। बहुत तकलीफ हो रही है।",
        },
        "t2s1": {
            "en": "You mentioned there's been no water at your home for five days — which area are you in?",
            "hi": "आपने कहा कि आपके घर में पाँच दिनों से पानी नहीं है — आप किस इलाके में हैं?",
        },
        "t3s1": {
            "en": "Our house is near Bandar road. I think our pipe has broken. The neighbors have the same problem too. There's a young baby at home, we have to go far every day for water.",
            "hi": "हमारा घर बंदर रोड के पास है। लगता है हमारा पाइप टूट गया है। पड़ोसियों को भी यही समस्या है। घर में छोटा बच्चा है, रोज पानी के लिए दूर जाना पड़ता है।",
        },
        "t4s1": {
            "en": "The pipe has broken in the Bandar road area with no water, there's an infant at home, and the neighbors have the same issue — is that correct?",
            "hi": "बंदर रोड इलाके में पाइप टूट गया और पानी नहीं आ रहा, घर में शिशु है और पड़ोसियों को भी यही समस्या है — सही है?",
        },
        "t5s1": {
            "en": "Yes, you've stated it correctly. But I had called KUWSDB (Karnataka Urban Water Supply & Drainage Board) earlier and no one came. The baby has a fever and there's no water to drink.",
            "hi": "हाँ, सही कहा। लेकिन मैंने पहले ही KUWSDB को कॉल किया था, कोई नहीं आया। बच्चे को बुखार है और पीने का पानी नहीं है।",
        },
        "t6s1": {
            "en": "KUWSDB was called earlier but there was no response, and the baby has a fever — I'm escalating this to senior authorities urgently.",
            "hi": "KUWSDB को पहले कॉल किया था लेकिन कोई प्रतिक्रिया नहीं, बच्चे को बुखार है — मैं इसे तुरंत वरिष्ठ अधिकारियों को भेज रहा हूँ।",
        },
        "t7s1": {
            "en": "Please do it quickly. We are suffering a lot. The baby is crying.",
            "hi": "कृपया जल्दी करें। हम बहुत तकलीफ में हैं। बच्चा रो रहा है।",
        },
    },
    DEMO_SESSION_IDS[1]: {  # Bengaluru — workplace harassment (already English, add KN/HI)
        "t2s2": {
            "en": "I understand your manager is harassing you at the office — is this physical or verbal harassment?",
            "hi": "मैं समझता हूँ कि आपका मैनेजर आपको कार्यालय में परेशान कर रहा है — क्या यह शारीरिक या मानसिक उत्पीड़न है?",
        },
        "t4s2": {
            "en": "Your manager physically blocked the exit and has verbally abused you — you have recordings as evidence. I'll register a formal complaint. Should I also alert the women's helpline?",
            "hi": "आपके मैनेजर ने शारीरिक रूप से रास्ता रोका और मौखिक दुर्व्यवहार किया — आपके पास रिकॉर्डिंग भी है। मैं औपचारिक शिकायत दर्ज करूँगा। क्या महिला हेल्पलाइन को भी सूचित करूँ?",
        },
        "t6s2": {
            "en": "Escalating to police and women's safety cell immediately. Please stay on the line and move to a public area inside the office.",
            "hi": "पुलिस और महिला सुरक्षा सेल को तुरंत सूचित किया जा रहा है। कृपया लाइन पर रहें और कार्यालय के अंदर किसी सार्वजनिक क्षेत्र में चले जाएँ।",
        },
    },
    DEMO_SESSION_IDS[2]: {  # Kalaburagi — pension (Hindi)
        "t2s3": {
            "en": "Your pension hasn't arrived for the past three months and you live alone — under which scheme did the pension come?",
            "kn": "ನಿಮ್ಮ ಪೆನ್ಶನ್ ಕಳೆದ ಮೂರು ತಿಂಗಳಿಂದ ಬಂದಿಲ್ಲ ಮತ್ತು ನೀವು ಒಬ್ಬರೇ ಇದ್ದೀರಿ — ಯಾವ ಯೋಜನೆಯ ಅಡಿ ಪೆನ್ಶನ್ ಬರ್ತಿತ್ತು?",
        },
        "t4s3": {
            "en": "Sandhya Suraksha pension, stopped after filling a form — Aadhaar is linked but pension still didn't arrive — which bank holds the account?",
            "kn": "ಸಂಧ್ಯಾ ಸುರಕ್ಷಾ ಪೆನ್ಶನ್, ಫಾರ್ಮ್ ಭರಿಸಿದ ನಂತರ ಬಂಧ ಆಗಿದೆ — ಆಧಾರ್ ಲಿಂಕ್ ಇದ್ರೂ ಬಂದಿಲ್ಲ — ಯಾವ ಬ್ಯಾಂಕ್ ನಲ್ಲಿ ಖಾತೆ ಇದೆ?",
        },
        "t6s3": {
            "en": "You had filed two previous complaints — sent documents, visited the office — still no resolution — is that correct?",
            "kn": "ನೀವು ಎರಡು ಬಾರಿ ಮೊದಲು ದೂರು ದಾಖಲಿಸಿದ್ದೀರಿ — ದಾಖಲೆ ಕಳಿಸಿದ್ರಿ, ಕಚೇರಿಗೂ ಹೋದ್ರಿ — ಆದ್ರೂ ಪರಿಹಾರ ಆಗಿಲ್ಲ — ಸರಿಯಾ?",
        },
        "t8s3": {
            "en": "I'm sending this case immediately to senior officials — please note your reference number.",
            "kn": "ಈ ಪ್ರಕರಣವನ್ನು ತಕ್ಷಣ ವರಿಷ್ಠ ಅಧಿಕಾರಿಗಳಿಗೆ ಕಳಿಸ್ತಿದ್ದೇನೆ — ನಿಮ್ಮ ಉಲ್ಲೇಖ ಸಂಖ್ಯೆ ಗಮನಿಸಿ.",
        },
        "t1s3": {
            "en": "Yes, my pension hasn't come for three months. I'm 68 years old and there's no one else at home.",
            "kn": "ಹೌದು, ನನ್ನ ಪೆನ್ಶನ್ ಮೂರು ತಿಂಗಳಿಂದ ಬಂದಿಲ್ಲ. ನನಗೆ 68 ವರ್ಷ, ಮನೆಯಲ್ಲಿ ಬೇರೆ ಯಾರೂ ಇಲ್ಲ.",
        },
        "t3s3": {
            "en": "It was Sandhya Suraksha. A few months ago I filled out a form and submitted it, after that it stopped. My Aadhaar [AADHAAR_1] is linked, but it still didn't come.",
            "kn": "ಸಂಧ್ಯಾ ಸುರಕ್ಷಾ ಇತ್ತು. ಕೆಲ ತಿಂಗಳ ಹಿಂದೆ ಒಂದು ಫಾರ್ಮ್ ಭರಿಸಿ ಕೊಟ್ಟಿದ್ದೆ, ಆಮೇಲೆ ಬಂಧ ಆಯ್ತು. ಆಧಾರ್ ಲಿಂಕ್ ಇದೆ ಆದ್ರೂ ಬಂದಿಲ್ಲ.",
        },
        "t5s3": {
            "en": "Yes it's linked. I've already called twice before. Once they said send documents, I sent them. Then they said come to office, I went. Nothing worked.",
            "kn": "ಹೌದು ಲಿಂಕ್ ಆಗಿದೆ, ನಾನು ಮೊದಲು ಎರಡು ಸಲ ಕಾಲ್ ಮಾಡಿದ್ದೇನೆ. ಒಂದು ಸಲ ದಾಖಲೆ ಕಳಿಸಿ ಅಂದ್ರು, ಕಳಿಸಿದ್ದೆ. ನಂತರ ಕಚೇರಿಗೆ ಬನ್ನಿ ಅಂದ್ರು, ಹೋದ್ದೆ. ಏನೂ ಕೆಲಸ ಆಗಿಲ್ಲ.",
        },
        "t7s3": {
            "en": "Absolutely right. What have I been eating for three months? This was my life's savings. It is very difficult.",
            "kn": "ಬಿಲ್ಕುಲ್ ಸರಿ. ಮೂರು ತಿಂಗಳಿಂದ ಏನು ತಿಂತಿದ್ದೇನೆ? ಇದು ನನ್ನ ಜೀವನದ ದುಡಿತ. ತುಂಬಾ ಕಷ್ಟ.",
        },
    },
    DEMO_SESSION_IDS[3]: {  # Mysuru — ration card (Kannada)
        "t1s4": {
            "en": "Our ration card is still at the old house address. Got married, now at a new house.",
            "hi": "हमारा राशन कार्ड अभी भी पुराने घर के पते पर है। शादी हो गई, अब नए घर में हैं।",
        },
        "t2s4": {
            "en": "After marriage you need to transfer the ration card to the new address — what was your old district?",
            "hi": "शादी के बाद राशन कार्ड नए पते पर ट्रांसफर करना होगा — आपका पुराना जिला कौन सा था?",
        },
        "t3s4": {
            "en": "Old house is in Mysuru, new house is also in Mysuru. When I went to the office they said bring some form and sent me back, don't know where to get that form.",
            "hi": "पुराना घर मैसूरु में है, नया घर भी मैसूरु में है। जब कार्यालय गई तो उन्होंने कोई फॉर्म लाने को कहा और वापस भेज दिया, वह फॉर्म कहाँ मिलेगा नहीं पता।",
        },
        "t4s4": {
            "en": "Transfer within Mysuru — you need the RC-6 form. It's available at the Food Department office or Seva Sindhu portal — understood?",
            "hi": "मैसूरु के अंदर ट्रांसफर — आपको RC-6 फॉर्म चाहिए। यह खाद्य विभाग कार्यालय या सेवा सिंधु पोर्टल पर मिलता है — समझे?",
        },
        "t5s4": {
            "en": "Understood a bit. But what is Seva Sindhu? Is it online? I'm not very familiar with phones and all.",
            "hi": "थोड़ा समझ आया। लेकिन सेवा सिंधु क्या है? क्या यह ऑनलाइन है? मुझे फोन और सब ज़्यादा नहीं पता।",
        },
        "t6s4": {
            "en": "Seva Sindhu is a government website. But you can directly go to the office and get RC-6 — an officer will contact you.",
            "hi": "सेवा सिंधु एक सरकारी वेबसाइट है। लेकिन आप सीधे कार्यालय जाकर RC-6 ले सकती हैं — एक अधिकारी आपसे संपर्क करेंगे।",
        },
    },
    DEMO_SESSION_IDS[4]: {  # Belagavi — garbage (Kannada)
        "t1s5": {
            "en": "Ah, our colony hasn't had garbage collected for two weeks. Garbage has piled up on the road.",
            "hi": "अरे, हमारी कॉलोनी में दो हफ्तों से कूड़ा नहीं उठाया गया। सड़क पर कूड़े का ढेर लग गया है।",
        },
        "t2s5": {
            "en": "Your colony hasn't had garbage collection for two weeks — which colony and have you reported to BBMP before?",
            "hi": "आपकी कॉलोनी में दो हफ्तों से कूड़ा नहीं उठाया — कौन सी कॉलोनी और पहले BBMP को शिकायत की है?",
        },
        "t3s5": {
            "en": "Camp area. Yes, I called BBMP three times. Once they said the vehicle is coming, it didn't come.",
            "hi": "कैम्प एरिया। हाँ, मैंने BBMP को तीन बार कॉल किया। एक बार कहा गाड़ी आएगी, नहीं आई।",
        },
        "t4s5": {
            "en": "14 days no garbage collection in Camp area, BBMP called 3 times but vehicle didn't come — is that correct?",
            "hi": "कैम्प एरिया में 14 दिन से कूड़ा नहीं उठाया, 3 बार BBMP को कॉल किया फिर भी गाड़ी नहीं आई — सही है?",
        },
        "t5s5": {
            "en": "Yes, that's right. Rain is also coming, the garbage will rot. Afraid of disease.",
            "hi": "हाँ, सही है। बारिश भी आने वाली है, कूड़ा सड़ेगा। बीमारी का डर है।",
        },
        "t6s5": {
            "en": "Due to rain and health risk, I'm sending this as an urgent complaint to senior BBMP officials.",
            "hi": "बारिश और स्वास्थ्य जोखिम के कारण, मैं इसे BBMP के वरिष्ठ अधिकारियों को एक अत्यावश्यक शिकायत के रूप में भेज रहा हूँ।",
        },
    },
    DEMO_SESSION_IDS[5]: {  # Hubballi — HESCOM wrong billing (PII redaction demo)
        "t1s6": {
            "en": "My name is Ramesh Patil, mobile 9844567890. In Vidyanagar Hubballi our HESCOM bill has come as ₹8,400 — it never exceeded ₹600.",
            "hi": "मेरा नाम रमेश पाटील है, मोबाइल 9844567890. विद्यानगर हुब्बली में हमारा HESCOM बिल ₹8,400 आया है, कभी ₹600 नहीं पार किया था।",
        },
        "t2s6": {
            "en": "You're saying the HESCOM bill in Vidyanagar Hubballi is ₹8,400 when it was normally ₹600. Does the meter reading match the figure on the bill?",
            "hi": "आप कह रहे हैं कि विद्यानगर हुब्बली में HESCOM बिल ₹8,400 आया है जबकि सामान्यतः ₹600 आता था। क्या मीटर रीडिंग बिल में दिए गए नंबर से मेल खाती है?",
        },
        "t3s6": {
            "en": "No sir. Meter shows 1847 units, but the bill says 4200. I went to the HESCOM office, they said it was a computer error but didn't correct it.",
            "hi": "नहीं सर। मीटर 1847 यूनिट दिखाता है, लेकिन बिल में 4200 लिखा है। मैं HESCOM कार्यालय गया, उन्होंने कंप्यूटर एरर बताया लेकिन सुधारा नहीं।",
        },
        "t4s6": {
            "en": "Meter reads 1847 units but bill shows 4200 — HESCOM office visit didn't get it corrected — have I understood correctly?",
            "hi": "मीटर 1847 यूनिट है लेकिन बिल 4200 यूनिट दिखा रहा है — HESCOM कार्यालय जाने पर भी नहीं सुधरा — क्या मैंने सही समझा?",
        },
        "t5s6": {
            "en": "Yes, that's right. I won't pay ₹8,400. I've been here 30 years, I have a record of bill payments. Please file a complaint.",
            "hi": "हाँ, सही कहा। मैं ₹8,400 नहीं भरूँगा। मैं 30 साल से यहाँ हूँ, बिल भुगतान का रिकॉर्ड है। शिकायत दर्ज करें।",
        },
        "t6s6": {
            "en": "Your case with 30 years of good payment record is being escalated to HESCOM senior officials and the Karnataka Electricity Regulatory Commission.",
            "hi": "30 साल के अच्छे भुगतान रिकॉर्ड वाले आपके मामले को HESCOM वरिष्ठ अधिकारियों और कर्नाटक विद्युत नियामक आयोग को भेजा जा रहा है।",
        },
    },
}


# Queue metadata — English summaries keep queue cards readable
DEMO_QUEUE_ENTRIES = [
    {
        "session_id": DEMO_SESSION_IDS[0],
        "sentiment_intensity": 0.89,
        "sentiment": "distress",
        "reason": "high_distress",
        "summary": "No water 5 days · infant sick · KUWSDB unresponsive",
        "district": "mangaluru",
        "language": "kn",
        "final_intent": "water_supply_complaint",
    },
    {
        "session_id": DEMO_SESSION_IDS[1],
        "sentiment_intensity": 0.85,
        "sentiment": "fear",
        "reason": "high_distress",
        "summary": "Workplace harassment · caller in fear · police complaint",
        "district": "bengaluru_urban",
        "language": "kn",
        "final_intent": "police_grievance",
    },
    {
        "session_id": DEMO_SESSION_IDS[2],
        "sentiment_intensity": 0.66,
        "sentiment": "concerned",
        "reason": "repeated_clarification",
        "summary": "Pension stopped 3 months · 68yr alone · 3rd call",
        "district": "kalaburagi",
        "language": "hi",
        "final_intent": "pension_scheme",
    },
    {
        "session_id": DEMO_SESSION_IDS[3],
        "sentiment_intensity": 0.42,
        "sentiment": "confusion",
        "reason": "low_confidence",
        "summary": "Ration card address update · unclear on RC-6 form",
        "district": "mysuru",
        "language": "kn",
        "final_intent": "ration_card_correction",
    },
    {
        "session_id": DEMO_SESSION_IDS[4],
        "sentiment_intensity": 0.60,
        "sentiment": "concerned",
        "reason": "repeated_clarification",
        "summary": "14 days no garbage · BBMP called 3x · health risk",
        "district": "belagavi",
        "language": "kn",
        "final_intent": "sanitation_garbage",
    },
    {
        "session_id": DEMO_SESSION_IDS[5],
        "sentiment_intensity": 0.58,
        "sentiment": "concerned",
        "reason": "repeated_clarification",
        "summary": "HESCOM bill ₹8,400 vs meter 1847 units · office visit failed · PII redacted",
        "district": "hubballi_dharwad",
        "language": "kn",
        "final_intent": "bescom_billing",
    },
]
