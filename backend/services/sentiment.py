"""
Sentiment Service — six-class emotion detection with multi-modal fusion.

Text path: keyword heuristics (prototype) / IndicBERT (production).
Prosodic path: librosa feature extraction, gated by ENABLE_PROSODY flag.
Fusion: text × 0.6 + prosodic × 0.4; intensity = max(text, fused) to avoid
        missing high vocal stress masked by calm words.
"""
from dataclasses import dataclass
from typing import Literal
from config import settings

SentimentLabel = Literal["distress", "anger", "fear", "urgency", "confusion", "calm"]

@dataclass
class SentimentResult:
    label: SentimentLabel
    intensity: float            # 0–1, dominant emotion intensity (renamed from score)
    text_component: float       # text-path contribution (renamed from text_score)
    prosodic_component: float   # prosodic-path contribution (renamed from prosodic_score)
    all_scores: dict            # {label: score} full distribution for timeline


# ── Keyword signal banks ──────────────────────────────────────────────────────

DISTRESS_SIGNALS = {
    "kn": ["ತುರ್ತು", "ಸಾಯ್ತಾ", "ಆಸ್ಪತ್ರೆ", "ಭಯ", "ಅಪಾಯ", "ಸಹಾಯ", "ದಯವಿಟ್ಟು"],
    "hi": ["मदद", "आपातकाल", "डर", "खतरा", "बचाओ", "जल्दी", "अस्पताल"],
    "en": ["help", "emergency", "scared", "danger", "dying", "please", "urgent", "hospital"],
}

ANGER_SIGNALS = {
    "kn": ["ಕೋಪ", "ಸಿಟ್ಟು", "ಅಸಹ್ಯ", "ಬೇಜವಾಬ್ದಾರಿ"],
    "hi": ["गुस्सा", "बकवास", "बेकार", "शर्म"],
    "en": ["angry", "useless", "pathetic", "incompetent", "ridiculous", "fed up"],
}

URGENCY_SIGNALS = {
    "kn": ["ತಕ್ಷಣ", "ಬೇಗ", "ಇಂದೇ", "ಈಗಲೇ"],
    "hi": ["तुरंत", "अभी", "जल्दी", "तत्काल"],
    "en": ["immediately", "right now", "today", "asap", "quick"],
}


# ── Text-based analysis ───────────────────────────────────────────────────────

def analyze_text_sentiment(transcript: str, language: str) -> dict:
    """
    Lightweight keyword heuristic for prototype.
    Production: replace with IndicBERT fine-tuned on Karnataka grievance corpus.
    """
    text_lower = transcript.lower()
    scores = {label: 0.0 for label in ["distress", "anger", "fear", "urgency", "confusion", "calm"]}

    for lang_key in [language, "en"]:
        for word in DISTRESS_SIGNALS.get(lang_key, []):
            if word in text_lower:
                scores["distress"] = min(1.0, scores["distress"] + 0.35)
        for word in ANGER_SIGNALS.get(lang_key, []):
            if word in text_lower:
                scores["anger"] = min(1.0, scores["anger"] + 0.35)
        for word in URGENCY_SIGNALS.get(lang_key, []):
            if word in text_lower:
                scores["urgency"] = min(1.0, scores["urgency"] + 0.30)

    q_count = transcript.count("?") + sum(
        1 for w in ["ಏಕೆ", "ಹೇಗೆ", "ಯಾವಾಗ", "क्यों", "कैसे", "why", "how", "when"]
        if w in text_lower
    )
    if q_count >= 2:
        scores["confusion"] = min(1.0, scores["confusion"] + 0.25 * q_count)

    total = sum(scores.values())
    if total < 0.1:
        scores["calm"] = 0.75
    else:
        scores = {k: round(v / total, 3) for k, v in scores.items()}

    return scores


# ── Prosodic analysis ─────────────────────────────────────────────────────────

def _prosodic_distress_from_bytes(audio_bytes: bytes) -> float:
    """
    Return a distress float [0,1] from audio.
    Delegates to prosody.py when ENABLE_PROSODY is True; returns neutral stub otherwise.
    """
    if settings.enable_prosody and len(audio_bytes) >= 1024:
        from services import prosody as _prosody
        features = _prosody.extract_prosodic_features(audio_bytes)
        return _prosody.prosodic_distress_score(features)
    # Stub: mildly calm
    return 0.10


# ── Fusion ────────────────────────────────────────────────────────────────────

def fuse_sentiments(
    text_scores: dict,
    prosodic_distress: float,
    text_weight: float = 0.60,
) -> SentimentResult:
    """
    Fuse text emotion scores with a scalar prosodic distress signal.

    Strategy — "take max":
      • Compute weighted fused-distress = text_distress*0.6 + prosodic*0.4
      • If prosodic_distress alone exceeds the text-dominant emotion's intensity,
        the prosodic signal wins: label → "distress", intensity = prosodic_distress.
      • Otherwise keep the text-dominant label; intensity = max(text, fused_distress)
        so a partial prosodic boost is still visible but doesn't flip the label.

    This ensures "calm words + high vocal stress → higher intensity than text-only".
    """
    prosodic_weight = 1.0 - text_weight

    text_dominant_label = max(text_scores, key=text_scores.get)
    text_dominant_intensity = text_scores[text_dominant_label]

    fused_distress = round(
        text_scores.get("distress", 0.0) * text_weight + prosodic_distress * prosodic_weight,
        4,
    )

    # Build all_scores for dashboard timeline
    all_scores = dict(text_scores)
    all_scores["distress"] = round(max(text_scores.get("distress", 0.0), fused_distress), 3)

    if prosodic_distress > text_dominant_intensity:
        # Vocal stress dominates: override label to distress
        label = "distress"
        intensity = round(max(prosodic_distress, fused_distress), 4)
        text_component = round(text_scores.get("distress", 0.0), 4)
    else:
        label = text_dominant_label
        intensity = round(max(text_dominant_intensity, fused_distress), 4)
        text_component = round(text_dominant_intensity, 4)

    return SentimentResult(
        label=label,
        intensity=intensity,
        text_component=text_component,
        prosodic_component=round(prosodic_distress, 4),
        all_scores=all_scores,
    )


async def analyze(transcript: str, audio_bytes: bytes, language: str) -> SentimentResult:
    """Main entry point — fuses text + prosodic sentiment."""
    text_scores = analyze_text_sentiment(transcript, language)
    prosodic_distress = _prosodic_distress_from_bytes(audio_bytes)
    return fuse_sentiments(text_scores, prosodic_distress)


def is_high_distress(result: SentimentResult) -> bool:
    return (
        result.label in ("distress", "fear")
        and result.intensity >= settings.distress_score_threshold
    )
