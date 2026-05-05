"""
Escalation Engine — multi-signal scoring per turn.
Every turn produces a composite score; if it crosses threshold, escalate.
Signals: ASR confidence + intent entropy + sentiment intensity + clarification counter.
"""
from dataclasses import dataclass
from typing import Optional
from config import settings
from models.session_model import SessionState, EscalationReason
from services.sentiment import SentimentResult, is_high_distress

@dataclass
class EscalationDecision:
    should_escalate: bool
    reason: EscalationReason
    composite_score: float          # 0–1, shown on agent dashboard gauge
    explanation: str                # human-readable, shown on dashboard

def compute_composite_score(
    asr_confidence: float,
    intent_entropy: float,
    sentiment: SentimentResult,
    clarification_count: int,
) -> float:
    """
    Composite escalation score [0,1]. Higher = more likely to escalate.

    Components:
    - ASR confidence gap:   how far below threshold we are
    - Intent entropy:       uncertainty in understanding
    - Sentiment intensity:  how distressed the caller is
    - Clarification toll:   penalty for repeated failed attempts
    """
    asr_gap       = max(0.0, settings.asr_confidence_threshold - asr_confidence) / settings.asr_confidence_threshold
    entropy_score = min(intent_entropy, 1.0)
    sentiment_score = sentiment.score if sentiment.label in ("distress", "anger", "fear") else sentiment.score * 0.3
    clarification_penalty = min(clarification_count / settings.max_clarification_turns, 1.0)

    # Weighted sum
    score = (
        asr_gap               * 0.25 +
        entropy_score         * 0.30 +
        sentiment_score       * 0.30 +
        clarification_penalty * 0.15
    )
    return round(min(score, 1.0), 3)


def evaluate(
    session: SessionState,
    asr_confidence: float,
    intent_entropy: float,
    sentiment: SentimentResult,
) -> EscalationDecision:
    """
    Run all escalation checks in priority order.
    Returns the first (highest-priority) reason that fires.
    """
    composite = compute_composite_score(
        asr_confidence, intent_entropy, sentiment, session.clarification_count
    )

    # 1. HIGH DISTRESS — always escalate immediately, no threshold waiting
    if is_high_distress(sentiment):
        return EscalationDecision(
            should_escalate=True,
            reason="high_distress",
            composite_score=composite,
            explanation=f"Caller shows high {sentiment.label} (score: {sentiment.score:.2f}). Routing to human agent immediately.",
        )

    # 2. LOW ASR CONFIDENCE — can't reliably hear the caller
    if asr_confidence < settings.asr_confidence_threshold:
        return EscalationDecision(
            should_escalate=True,
            reason="low_asr_confidence",
            composite_score=composite,
            explanation=f"ASR confidence {asr_confidence:.2f} < threshold {settings.asr_confidence_threshold}. Audio may be unclear.",
        )

    # 3. HIGH INTENT ENTROPY — genuinely don't understand the request
    if intent_entropy > settings.intent_entropy_threshold:
        return EscalationDecision(
            should_escalate=True,
            reason="high_intent_entropy",
            composite_score=composite,
            explanation=f"Intent classification uncertain (entropy: {intent_entropy:.2f}). Caller's request is ambiguous.",
        )

    # 4. REPEATED CLARIFICATION — tried and failed enough times
    if session.clarification_count >= settings.max_clarification_turns:
        return EscalationDecision(
            should_escalate=True,
            reason="repeated_clarification",
            composite_score=composite,
            explanation=f"Clarification attempted {session.clarification_count} times without success.",
        )

    # No escalation needed
    return EscalationDecision(
        should_escalate=False,
        reason="none",
        composite_score=composite,
        explanation="All signals within acceptable range.",
    )


def build_escalation_message(reason: EscalationReason, language: str) -> str:
    """Message spoken to citizen when handing off to human agent."""
    messages = {
        "kn": {
            "high_distress":         "ನಿಮ್ಮ ಪರಿಸ್ಥಿತಿ ಅರ್ಥವಾಯಿತು. ನಿಮ್ಮನ್ನು ತಕ್ಷಣ ಒಬ್ಬ ಅಧಿಕಾರಿಯೊಂದಿಗೆ ಸಂಪರ್ಕಿಸುತ್ತಿದ್ದೇನೆ.",
            "low_asr_confidence":    "ಸ್ವಲ್ಪ ಶಬ್ದ ಸ್ಪಷ್ಟವಾಗಿ ಕೇಳಿಸುತ್ತಿಲ್ಲ. ಒಬ್ಬ ಅಧಿಕಾರಿ ನಿಮಗೆ ಸಹಾಯ ಮಾಡುತ್ತಾರೆ.",
            "high_intent_entropy":   "ನಿಮ್ಮ ಸಮಸ್ಯೆ ಸರಿಯಾಗಿ ಅರ್ಥವಾಗಲಿಲ್ಲ. ಅಧಿಕಾರಿ ಮಾತನಾಡುತ್ತಾರೆ.",
            "repeated_clarification":"ಅಧಿಕಾರಿ ಬಳಿ ನಿಮ್ಮ ಸಮಸ್ಯೆ ಹೇಳಿ — ಸಂಪರ್ಕಿಸುತ್ತಿದ್ದೇನೆ.",
        },
        "hi": {
            "high_distress":         "आपकी स्थिति समझ आई। आपको अभी एक अधिकारी से जोड़ रहा हूँ।",
            "low_asr_confidence":    "आवाज़ स्पष्ट नहीं आ रही। एक अधिकारी आपकी मदद करेंगे।",
            "high_intent_entropy":   "आपकी बात पूरी तरह समझ नहीं आई। अधिकारी बात करेंगे।",
            "repeated_clarification":"अधिकारी से अपनी समस्या बताइए — जोड़ रहा हूँ।",
        },
        "en": {
            "high_distress":         "I understand this is urgent. Connecting you to a human agent right away.",
            "low_asr_confidence":    "I'm having trouble hearing you clearly. Let me connect you to an agent.",
            "high_intent_entropy":   "I want to make sure you get the right help. An agent will assist you.",
            "repeated_clarification":"Let me connect you to a human agent who can help you directly.",
        },
    }
    lang_msgs = messages.get(language, messages["en"])
    return lang_msgs.get(reason, lang_msgs.get("repeated_clarification", "Connecting you to an agent."))
