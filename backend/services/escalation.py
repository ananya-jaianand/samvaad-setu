"""
Escalation Engine — delegates all scoring to confidence_scorer, then
maps the result to escalation messages and WebSocket payloads.
"""
from dataclasses import dataclass
from config import settings
from models.session_model import SessionState, EscalationReason
from services.sentiment import SentimentResult
from services.confidence_scorer import ConfidenceScore, build_score, should_escalate


@dataclass
class EscalationDecision:
    should_escalate: bool
    reason: EscalationReason
    composite_score: float           # raw score from ConfidenceScore (0–1)
    explanation: str
    confidence_score: ConfidenceScore = None   # full breakdown for agent dashboard


def evaluate(
    session: SessionState,
    asr_confidence: float,
    intent_entropy: float,
    sentiment: SentimentResult,
) -> EscalationDecision:
    """
    Build a ConfidenceScore for this turn and decide whether to escalate.
    Returns an EscalationDecision with the full score attached.
    """
    score = build_score(
        asr_conf=asr_confidence,
        intent_entropy=intent_entropy,
        sentiment_intensity=sentiment.intensity,
        clarification_count=session.clarification_count,
    )

    escalate, reason = should_escalate(score, sentiment.label)

    if not escalate:
        explanation = (
            f"Composite confidence {score.composite_score:.2f} — all signals within range."
        )
    elif reason == "high_distress":
        explanation = (
            f"Caller shows high {sentiment.label} (intensity: {sentiment.score:.2f}). "
            "Routing to human agent immediately."
        )
    elif reason == "repeated_clarification":
        explanation = (
            f"Verification failed {session.clarification_count} times. "
            "Escalating to prevent caller frustration."
        )
    else:  # low_confidence
        explanation = (
            f"Composite confidence {score.composite_score:.2f} below threshold 0.40. "
            f"ASR: {asr_confidence:.2f}, entropy: {intent_entropy:.2f}."
        )

    return EscalationDecision(
        should_escalate=escalate,
        reason=reason,
        composite_score=score.composite_score,
        explanation=explanation,
        confidence_score=score,
    )


def build_escalation_message(reason: EscalationReason, language: str) -> str:
    """Message spoken to citizen when handing off to human agent."""
    messages = {
        "kn": {
            "high_distress":          "ನಿಮ್ಮ ಪರಿಸ್ಥಿತಿ ಅರ್ಥವಾಯಿತು. ನಿಮ್ಮನ್ನು ತಕ್ಷಣ ಒಬ್ಬ ಅಧಿಕಾರಿಯೊಂದಿಗೆ ಸಂಪರ್ಕಿಸುತ್ತಿದ್ದೇನೆ.",
            "low_asr_confidence":     "ಸ್ವಲ್ಪ ಶಬ್ದ ಸ್ಪಷ್ಟವಾಗಿ ಕೇಳಿಸುತ್ತಿಲ್ಲ. ಒಬ್ಬ ಅಧಿಕಾರಿ ನಿಮಗೆ ಸಹಾಯ ಮಾಡುತ್ತಾರೆ.",
            "low_confidence":         "ನಿಮ್ಮ ಸಮಸ್ಯೆ ಸರಿಯಾಗಿ ಅರ್ಥವಾಗಲಿಲ್ಲ. ಅಧಿಕಾರಿ ಮಾತನಾಡುತ್ತಾರೆ.",
            "high_intent_entropy":    "ನಿಮ್ಮ ಸಮಸ್ಯೆ ಸರಿಯಾಗಿ ಅರ್ಥವಾಗಲಿಲ್ಲ. ಅಧಿಕಾರಿ ಮಾತನಾಡುತ್ತಾರೆ.",
            "repeated_clarification": "ಅಧಿಕಾರಿ ಬಳಿ ನಿಮ್ಮ ಸಮಸ್ಯೆ ಹೇಳಿ — ಸಂಪರ್ಕಿಸುತ್ತಿದ್ದೇನೆ.",
        },
        "hi": {
            "high_distress":          "आपकी स्थिति समझ आई। आपको अभी एक अधिकारी से जोड़ रहा हूँ।",
            "low_asr_confidence":     "आवाज़ स्पष्ट नहीं आ रही। एक अधिकारी आपकी मदद करेंगे।",
            "low_confidence":         "आपकी बात पूरी तरह समझ नहीं आई। अधिकारी बात करेंगे।",
            "high_intent_entropy":    "आपकी बात पूरी तरह समझ नहीं आई। अधिकारी बात करेंगे।",
            "repeated_clarification": "अधिकारी से अपनी समस्या बताइए — जोड़ रहा हूँ।",
        },
        "en": {
            "high_distress":          "I understand this is urgent. Connecting you to a human agent right away.",
            "low_asr_confidence":     "I'm having trouble hearing you clearly. Let me connect you to an agent.",
            "low_confidence":         "I want to make sure you get the right help. An agent will assist you.",
            "high_intent_entropy":    "I want to make sure you get the right help. An agent will assist you.",
            "repeated_clarification": "Let me connect you to a human agent who can help you directly.",
        },
    }
    lang_msgs = messages.get(language, messages["en"])
    return lang_msgs.get(reason, lang_msgs.get("repeated_clarification", "Connecting you to an agent."))
