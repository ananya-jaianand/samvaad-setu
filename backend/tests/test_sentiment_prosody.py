"""
Tests for multi-modal sentiment fusion and prosodic feature extraction.
Run with: pytest backend/tests/test_sentiment_prosody.py -v
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pytest
from services.sentiment import (
    SentimentResult,
    analyze_text_sentiment,
    fuse_sentiments,
    is_high_distress,
)
from services.prosody import (
    _neutral_features,
    _soft_clamp,
    prosodic_distress_score,
    extract_prosodic_features,
)


# ── analyze_text_sentiment ────────────────────────────────────────────────────

class TestAnalyzeTextSentiment:
    def test_distress_keywords_score_distress(self):
        scores = analyze_text_sentiment("please help emergency", "en")
        assert scores["distress"] > 0

    def test_calm_sentence_gives_calm(self):
        scores = analyze_text_sentiment("I need a water connection form.", "en")
        assert scores["calm"] > 0

    def test_anger_keywords_score_anger(self):
        scores = analyze_text_sentiment("This is useless and pathetic service", "en")
        assert scores["anger"] > 0

    def test_hindi_distress_keyword(self):
        scores = analyze_text_sentiment("मदद चाहिए अभी", "hi")
        assert scores["distress"] > 0

    def test_kannada_distress_keyword(self):
        scores = analyze_text_sentiment("ತುರ್ತು ಸಹಾಯ ಬೇಕು", "kn")
        assert scores["distress"] > 0

    def test_scores_sum_to_roughly_one_or_less(self):
        # After normalisation, total should be ≤ 1.0 (calm baseline can keep it lower)
        scores = analyze_text_sentiment("help me please emergency", "en")
        assert sum(scores.values()) <= 1.01


# ── fuse_sentiments ───────────────────────────────────────────────────────────

class TestFuseSentiments:
    def _calm_text(self):
        return {
            "distress": 0.0, "anger": 0.0, "fear": 0.0,
            "urgency": 0.0, "confusion": 0.0, "calm": 0.75,
        }

    def _distress_text(self):
        return {
            "distress": 0.7, "anger": 0.0, "fear": 0.1,
            "urgency": 0.1, "confusion": 0.0, "calm": 0.1,
        }

    def test_returns_sentiment_result(self):
        result = fuse_sentiments(self._calm_text(), 0.1)
        assert isinstance(result, SentimentResult)

    def test_high_prosodic_boosts_distress_over_calm_text(self):
        """KEY TEST (Prompt 4 requirement): calm words + high vocal stress → intensity > text-only."""
        text_only = fuse_sentiments(self._calm_text(), 0.0)
        with_prosody = fuse_sentiments(self._calm_text(), 0.85)
        assert with_prosody.intensity > text_only.intensity, (
            "High prosodic stress should raise intensity above text-only calm result"
        )

    def test_prosodic_distress_can_flip_label_to_distress(self):
        result = fuse_sentiments(self._calm_text(), 0.95)
        assert result.label == "distress"

    def test_zero_prosodic_preserves_text_label(self):
        result = fuse_sentiments(self._distress_text(), 0.0)
        assert result.label == "distress"

    def test_intensity_is_max_of_text_and_fused(self):
        result = fuse_sentiments(self._calm_text(), 0.90)
        # The result intensity should be >= the text component intensity
        assert result.intensity >= result.text_component

    def test_text_component_stored_correctly(self):
        result = fuse_sentiments(self._distress_text(), 0.2)
        assert 0.0 <= result.text_component <= 1.0

    def test_prosodic_component_stored_correctly(self):
        result = fuse_sentiments(self._calm_text(), 0.55)
        assert abs(result.prosodic_component - 0.55) < 1e-3

    def test_all_scores_dict_present(self):
        result = fuse_sentiments(self._calm_text(), 0.3)
        assert isinstance(result.all_scores, dict)
        assert "distress" in result.all_scores


# ── is_high_distress ──────────────────────────────────────────────────────────

class TestIsHighDistress:
    def _make(self, label, intensity):
        return SentimentResult(
            label=label, intensity=intensity,
            text_component=intensity, prosodic_component=0.0,
            all_scores={},
        )

    def test_distress_high_intensity_is_high(self):
        assert is_high_distress(self._make("distress", 0.75)) is True

    def test_distress_low_intensity_not_high(self):
        assert is_high_distress(self._make("distress", 0.30)) is False

    def test_fear_high_intensity_is_high(self):
        assert is_high_distress(self._make("fear", 0.80)) is True

    def test_anger_is_not_high_distress(self):
        # anger is NOT in the is_high_distress check in sentiment.py
        assert is_high_distress(self._make("anger", 0.90)) is False

    def test_calm_is_never_high_distress(self):
        assert is_high_distress(self._make("calm", 1.0)) is False


# ── prosody module ────────────────────────────────────────────────────────────

class TestProsody:
    def test_neutral_features_returns_dict(self):
        f = _neutral_features()
        for key in ("pitch_mean", "pitch_variance", "energy_mean", "speaking_rate", "voice_quality"):
            assert key in f

    def test_soft_clamp_midpoint(self):
        assert abs(_soft_clamp(5.0, 0, 10) - 0.5) < 1e-6

    def test_soft_clamp_below_lo_returns_zero(self):
        assert _soft_clamp(-1.0, 0, 10) == 0.0

    def test_soft_clamp_above_hi_returns_one(self):
        assert _soft_clamp(15.0, 0, 10) == 1.0

    def test_neutral_distress_score_is_low(self):
        score = prosodic_distress_score(_neutral_features())
        assert score < 0.50, "Neutral features should produce low distress"

    def test_high_stress_features_produce_high_score(self):
        stressed = {
            "pitch_mean":     250.0,
            "pitch_variance": 8000.0,   # very high
            "energy_mean":    0.20,     # loud
            "speaking_rate":  0.25,     # fast
            "voice_quality":  0.05,
        }
        score = prosodic_distress_score(stressed)
        assert score > 0.60, f"High-stress features should score > 0.60, got {score}"

    def test_extract_with_empty_bytes_returns_neutral(self):
        features = extract_prosodic_features(b"")
        assert features == _neutral_features()

    def test_extract_with_short_bytes_returns_neutral(self):
        features = extract_prosodic_features(b"\x00" * 100)
        assert features == _neutral_features()


# ── session_model timeline cap ────────────────────────────────────────────────

class TestSentimentTimelineCap:
    def test_timeline_capped_at_20(self):
        from models.session_model import SessionState, Turn, TurnSentiment
        session = SessionState()
        for i in range(25):
            turn = Turn(
                speaker="citizen",
                raw_transcript=f"turn {i}",
                sentiment=TurnSentiment(label="calm", intensity=0.5),
            )
            session.add_turn(turn)
        assert len(session.sentiment_timeline) == 20

    def test_timeline_keeps_most_recent(self):
        from models.session_model import SessionState, Turn, TurnSentiment
        session = SessionState()
        for i in range(22):
            turn = Turn(
                speaker="citizen",
                raw_transcript=f"turn {i}",
                sentiment=TurnSentiment(label="calm", intensity=float(i) / 22),
            )
            session.add_turn(turn)
        # The first two should have been dropped
        intensities = [e["intensity"] for e in session.sentiment_timeline]
        assert intensities[0] == pytest.approx(2 / 22, abs=1e-3)
