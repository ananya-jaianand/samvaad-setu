"""
Sentiment Service — six-class emotion detection.
Fuses prosodic features (energy, pitch, rate) with text-based classification.
In production: openSMILE for prosodics + IndicBERT fine-tuned on Karnataka grievances.
In prototype: lightweight heuristics + Claude for text classification.
"""
import re
from dataclasses import dataclass
from typing import Literal
from config import settings

SentimentLabel = Literal["distress", "anger", "fear", "urgency", "confusion", "calm"]

@dataclass
class SentimentResult:
    label: SentimentLabel
    score: float            # 0–1, intensity of the dominant emotion
    prosodic_score: float   # contribution from audio features
    text_score: float       # contribution from text features
    all_scores: dict        # {label: score} for timeline

# High-distress keywords per language (expand from IndicVoices annotations)
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


def analyze_text_sentiment(transcript: str, language: str) -> dict:
    """
    Lightweight keyword heuristic for prototype.
    In production: replace with IndicBERT fine-tuned on Karnataka grievance corpus.
    ── REPLACE WITH INDICBERT API ────────────────────────────────────────────
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

    # Question-heavy transcript → confusion signal
    q_count = transcript.count("?") + sum(1 for w in ["ಏಕೆ", "ಹೇಗೆ", "ಯಾವಾಗ", "क्यों", "कैसे", "why", "how", "when"] if w in text_lower)
    if q_count >= 2:
        scores["confusion"] = min(1.0, scores["confusion"] + 0.25 * q_count)

    # Normalise — if no signal, default to calm
    total = sum(scores.values())
    if total < 0.1:
        scores["calm"] = 0.75
    else:
        # Normalize to sum to 1
        scores = {k: round(v / total, 3) for k, v in scores.items()}

    return scores


def analyze_prosodic_sentiment(audio_bytes: bytes) -> dict:
    """
    In production: openSMILE feature extraction → energy, pitch variance, speaking rate.
    Prototype: returns neutral scores (stub — replace with openSMILE pipeline).
    ── REPLACE WITH openSMILE ────────────────────────────────────────────────
    """
    # TODO: pip install opensmile, extract eGeMAPSv02 features
    # features = opensmile.Smile(feature_set=opensmile.FeatureSet.eGeMAPSv02, ...)
    # energy = ..., pitch_var = ..., rate = ...
    # Map to sentiment via trained regressor

    # Stub: return mildly calm
    return {"distress": 0.1, "anger": 0.05, "fear": 0.05, "urgency": 0.1, "confusion": 0.1, "calm": 0.6}


def fuse_sentiments(text_scores: dict, prosodic_scores: dict, text_weight: float = 0.65) -> SentimentResult:
    """Weighted fusion of text and prosodic scores."""
    prosodic_weight = 1.0 - text_weight
    fused = {
        label: round(text_scores.get(label, 0) * text_weight + prosodic_scores.get(label, 0) * prosodic_weight, 3)
        for label in ["distress", "anger", "fear", "urgency", "confusion", "calm"]
    }

    dominant = max(fused, key=fused.get)
    return SentimentResult(
        label=dominant,
        score=fused[dominant],
        prosodic_score=prosodic_scores.get(dominant, 0.0),
        text_score=text_scores.get(dominant, 0.0),
        all_scores=fused,
    )


async def analyze(transcript: str, audio_bytes: bytes, language: str) -> SentimentResult:
    """Main entry point — fuses text + prosodic sentiment."""
    text_scores = analyze_text_sentiment(transcript, language)
    prosodic_scores = analyze_prosodic_sentiment(audio_bytes)
    return fuse_sentiments(text_scores, prosodic_scores)


def is_high_distress(result: SentimentResult) -> bool:
    return (
        result.label in ("distress", "fear") and
        result.score >= settings.distress_score_threshold
    )
