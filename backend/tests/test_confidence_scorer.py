"""
Unit tests for confidence_scorer — compute_composite, should_clarify, should_escalate.
Run with: pytest backend/tests/test_confidence_scorer.py -v
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from services.confidence_scorer import (
    ConfidenceScore,
    build_score,
    compute_composite,
    should_clarify,
    should_escalate,
)


# ── compute_composite ─────────────────────────────────────────────────────────

class TestComputeComposite:
    def test_perfect_inputs_near_max(self):
        score = compute_composite(1.0, 0.0, 0.0, 0)
        # 1.0*0.35 + 1.0*0.35 + 1.0*0.20 = 0.90
        assert abs(score - 0.90) < 1e-3

    def test_zero_asr_reduces_score(self):
        high = compute_composite(1.0, 0.0, 0.0, 0)
        low  = compute_composite(0.0, 0.0, 0.0, 0)
        assert low < high

    def test_high_entropy_reduces_score(self):
        low_entropy  = compute_composite(0.8, 0.0, 0.0, 0)
        high_entropy = compute_composite(0.8, 1.0, 0.0, 0)
        assert high_entropy < low_entropy

    def test_high_sentiment_intensity_reduces_score(self):
        calm     = compute_composite(0.8, 0.2, 0.0, 0)
        distress = compute_composite(0.8, 0.2, 1.0, 0)
        assert distress < calm

    def test_clarification_count_reduces_score(self):
        zero  = compute_composite(0.8, 0.2, 0.2, 0)
        one   = compute_composite(0.8, 0.2, 0.2, 1)
        two   = compute_composite(0.8, 0.2, 0.2, 2)
        assert zero > one > two

    def test_clarification_penalty_is_015_per_count(self):
        s0 = compute_composite(0.8, 0.0, 0.0, 0)
        s1 = compute_composite(0.8, 0.0, 0.0, 1)
        assert abs((s0 - s1) - 0.15) < 1e-3

    def test_result_clamped_to_zero_on_bad_inputs(self):
        score = compute_composite(0.0, 1.0, 1.0, 10)
        assert score == 0.0

    def test_result_never_exceeds_one(self):
        score = compute_composite(1.0, 0.0, 0.0, 0)
        assert score <= 1.0


# ── build_score / ConfidenceScore model ───────────────────────────────────────

class TestBuildScore:
    def test_returns_confidence_score_instance(self):
        s = build_score(0.8, 0.2, 0.1, 0)
        assert isinstance(s, ConfidenceScore)

    def test_composite_matches_compute_composite(self):
        s = build_score(0.75, 0.3, 0.2, 1)
        expected = compute_composite(0.75, 0.3, 0.2, 1)
        assert abs(s.composite_score - expected) < 1e-4

    def test_fields_stored_correctly(self):
        s = build_score(0.9, 0.1, 0.05, 2)
        assert s.asr_confidence == pytest.approx(0.9, abs=1e-4)
        assert s.intent_entropy == pytest.approx(0.1, abs=1e-4)
        assert s.sentiment_intensity == pytest.approx(0.05, abs=1e-4)
        assert s.clarification_count == 2


# ── should_clarify ────────────────────────────────────────────────────────────

class TestShouldClarify:
    def _score(self, composite: float) -> ConfidenceScore:
        return ConfidenceScore(
            asr_confidence=0.8,
            intent_entropy=0.2,
            sentiment_intensity=0.1,
            clarification_count=0,
            composite_score=composite,
        )

    def test_below_threshold_needs_clarification(self):
        assert should_clarify(self._score(0.59)) is True

    def test_at_threshold_does_not_need_clarification(self):
        assert should_clarify(self._score(0.60)) is False

    def test_above_threshold_confident(self):
        assert should_clarify(self._score(0.85)) is False

    def test_zero_composite_needs_clarification(self):
        assert should_clarify(self._score(0.0)) is True


# ── should_escalate ───────────────────────────────────────────────────────────

class TestShouldEscalate:
    def _score(
        self,
        composite: float = 0.75,
        sentiment_intensity: float = 0.2,
        clarification_count: int = 0,
    ) -> ConfidenceScore:
        return ConfidenceScore(
            asr_confidence=0.8,
            intent_entropy=0.2,
            sentiment_intensity=sentiment_intensity,
            clarification_count=clarification_count,
            composite_score=composite,
        )

    # high_distress trigger
    def test_high_distress_label_with_high_intensity_escalates(self):
        for label in ("distress", "fear", "anger"):
            escalate, reason = should_escalate(self._score(sentiment_intensity=0.75), label)
            assert escalate is True, f"Expected escalation for label={label}"
            assert reason == "high_distress"

    def test_high_distress_label_with_low_intensity_no_escalate(self):
        escalate, reason = should_escalate(self._score(sentiment_intensity=0.65), "distress")
        # intensity = 0.65 < 0.70 threshold, composite = 0.75 → no escalation
        assert escalate is False

    def test_calm_label_does_not_trigger_distress_escalation(self):
        escalate, reason = should_escalate(self._score(sentiment_intensity=0.9), "calm")
        assert escalate is False or reason != "high_distress"

    def test_urgency_label_does_not_trigger_distress_escalation(self):
        escalate, reason = should_escalate(self._score(sentiment_intensity=0.9), "urgency")
        # "urgency" is not in _HIGH_DISTRESS_LABELS
        assert reason != "high_distress"

    # repeated_clarification trigger
    def test_two_clarifications_triggers_escalation(self):
        escalate, reason = should_escalate(self._score(clarification_count=2), "calm")
        assert escalate is True
        assert reason == "repeated_clarification"

    def test_three_clarifications_also_triggers(self):
        escalate, reason = should_escalate(self._score(clarification_count=3), "calm")
        assert escalate is True
        assert reason == "repeated_clarification"

    def test_one_clarification_does_not_trigger(self):
        escalate, reason = should_escalate(self._score(clarification_count=1, composite=0.65), "calm")
        assert escalate is False

    # low_confidence trigger
    def test_composite_below_040_triggers_low_confidence(self):
        escalate, reason = should_escalate(self._score(composite=0.35), "calm")
        assert escalate is True
        assert reason == "low_confidence"

    def test_composite_at_040_does_not_trigger(self):
        escalate, reason = should_escalate(self._score(composite=0.40), "calm")
        assert escalate is False

    def test_composite_above_040_calm_no_escalation(self):
        escalate, _ = should_escalate(self._score(composite=0.70), "calm")
        assert escalate is False

    # priority order: high_distress before repeated_clarification before low_confidence
    def test_high_distress_takes_priority_over_repeated_clarification(self):
        score = self._score(composite=0.30, sentiment_intensity=0.80, clarification_count=3)
        _, reason = should_escalate(score, "distress")
        assert reason == "high_distress"

    def test_repeated_clarification_takes_priority_over_low_confidence(self):
        score = self._score(composite=0.30, clarification_count=2)
        _, reason = should_escalate(score, "calm")
        assert reason == "repeated_clarification"
