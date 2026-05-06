"""
Confidence Scorer — composite signal that drives clarify vs. escalate decisions.

Weights:
  asr_confidence        × 0.35   (can we hear the caller?)
  (1 - intent_entropy)  × 0.35   (do we understand what they want?)
  (1 - sentiment_inten) × 0.20   (are they calm enough to continue?)
  clarification penalty −0.15/count  (repeated failures cost confidence)

Thresholds:
  composite < 0.60  → should clarify (ask again before committing)
  composite < 0.40  → should escalate due to low_confidence
  distress/fear/anger intensity > 0.70 → escalate due to high_distress
  clarification_count ≥ 2 → escalate due to repeated_clarification
"""
from pydantic import BaseModel, Field


class ConfidenceScore(BaseModel):
    asr_confidence: float = Field(ge=0.0, le=1.0)
    intent_entropy: float = Field(ge=0.0, le=1.0)
    sentiment_intensity: float = Field(ge=0.0, le=1.0)
    clarification_count: int = Field(ge=0)
    composite_score: float = Field(ge=0.0, le=1.0)


def compute_composite(
    asr_conf: float,
    intent_entropy: float,
    sentiment_intensity: float,
    clarification_count: int,
) -> float:
    """
    Returns a composite confidence score in [0, 1].
    Higher = more confident the system understands the citizen correctly.
    """
    raw = (
        asr_conf                      * 0.35
        + (1.0 - intent_entropy)      * 0.35
        + (1.0 - sentiment_intensity) * 0.20
        - clarification_count         * 0.15
    )
    return round(max(0.0, min(1.0, raw)), 4)


def build_score(
    asr_conf: float,
    intent_entropy: float,
    sentiment_intensity: float,
    clarification_count: int,
) -> ConfidenceScore:
    """Convenience constructor that computes composite and wraps into model."""
    return ConfidenceScore(
        asr_confidence=round(max(0.0, min(1.0, asr_conf)), 4),
        intent_entropy=round(max(0.0, min(1.0, intent_entropy)), 4),
        sentiment_intensity=round(max(0.0, min(1.0, sentiment_intensity)), 4),
        clarification_count=max(0, clarification_count),
        composite_score=compute_composite(
            asr_conf, intent_entropy, sentiment_intensity, clarification_count
        ),
    )


def should_clarify(score: ConfidenceScore) -> bool:
    """True when confidence is too low to commit to an intent but not yet critical."""
    return score.composite_score < 0.60


_HIGH_DISTRESS_LABELS = {"distress", "fear", "anger"}


def should_escalate(
    score: ConfidenceScore,
    sentiment_label: str,
) -> tuple[bool, str]:
    """
    Returns (should_escalate, reason).
    Checks triggers in priority order — most severe first.
    """
    # 1. High distress — always escalate immediately
    if sentiment_label in _HIGH_DISTRESS_LABELS and score.sentiment_intensity > 0.70:
        return True, "high_distress"

    # 2. Repeated clarification failures
    if score.clarification_count >= 2:
        return True, "repeated_clarification"

    # 3. Composite confidence critically low
    if score.composite_score < 0.40:
        return True, "low_confidence"

    return False, "none"
