"""
TTS Service — Sarvam Bulbul with emotion-conditioned prosody.
Calmer tone for distressed callers; neutral/warm for standard queries.
"""
import httpx
import base64
from config import settings
from models.session_model import Turn

SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"

# Speaker voices per language — valid Sarvam Bulbul voice IDs
SPEAKER_MAP = {
    "kn": "meera",     # Kannada female voice
    "hi": "pavithra",  # Hindi female voice
    "en": "pavithra",  # English — Sarvam uses pavithra for en-IN too
}

# Prosody presets per sentiment — calmer for distress
PROSODY_MAP = {
    "distress": {"pace": 0.85, "pitch": -0.1},
    "anger":    {"pace": 0.88, "pitch": -0.05},
    "fear":     {"pace": 0.85, "pitch": -0.1},
    "urgency":  {"pace": 0.92, "pitch": 0.0},
    "confusion":{"pace": 0.90, "pitch": 0.0},
    "calm":     {"pace": 1.00, "pitch": 0.0},
}


async def synthesize(
    text: str,
    language: str = "kn",
    sentiment_label: str = "calm",
) -> str:
    """
    Convert text to speech. Returns base64-encoded WAV audio string.
    """
    if settings.environment == "mock" or not settings.sarvam_api_key:
        return _mock_tts(text, language)

    prosody = PROSODY_MAP.get(sentiment_label, PROSODY_MAP["calm"])
    # Normalize: "en-IN" → "en", "kn-IN" → "kn", "kn" → "kn"
    base_lang = language.split("-")[0]
    speaker = SPEAKER_MAP.get(base_lang, SPEAKER_MAP["en"])

    # ── REPLACE WITH REAL API ──────────────────────────────────────────────
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            SARVAM_TTS_URL,
            json={
                "inputs":            [text],
                "target_language_code": base_lang + "-IN",
                "speaker":           speaker,
                "model":             settings.sarvam_tts_model,
                "pace":              prosody["pace"],
                "pitch":             prosody["pitch"],
                "loudness":          1.0,
                "speech_sample_rate": 8000,
                "enable_preprocessing": True,
            },
            headers={"api-subscription-key": settings.sarvam_api_key},
        )
        if not resp.is_success:
            print(f"[TTS] Sarvam error {resp.status_code}: {resp.text}")
        resp.raise_for_status()
        body = resp.json()

    # Sarvam returns audio as base64 in audios[0]
    audio_b64 = body["audios"][0]
    return audio_b64
    # ── END REPLACE ────────────────────────────────────────────────────────


def _mock_tts(text: str, language: str) -> str:
    """
    Mock TTS — returns empty string so the frontend skips playback gracefully.
    Real TTS requires a Sarvam API key.
    """
    return ""
