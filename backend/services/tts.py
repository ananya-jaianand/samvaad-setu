"""
TTS Service — Sarvam Bulbul with emotion-conditioned prosody.
Calmer tone for distressed callers; neutral/warm for standard queries.
"""
import httpx
import base64
from config import settings
from models.session_model import Turn

SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"

# Speaker voices per language — adjust to Bulbul voice IDs when available
SPEAKER_MAP = {
    "kn": "meera",     # Kannada female voice
    "hi": "pavithra",  # Hindi female voice
    "en": "maya",      # English female voice
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
    speaker = SPEAKER_MAP.get(language, SPEAKER_MAP["en"])

    # ── REPLACE WITH REAL API ──────────────────────────────────────────────
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            SARVAM_TTS_URL,
            json={
                "inputs":            [text],
                "target_language_code": language + "-IN",
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
        resp.raise_for_status()
        body = resp.json()

    # Sarvam returns audio as base64 in audios[0]
    audio_b64 = body["audios"][0]
    return audio_b64
    # ── END REPLACE ────────────────────────────────────────────────────────


def _mock_tts(text: str, language: str) -> str:
    """
    Mock TTS — returns a tiny placeholder base64 WAV header.
    Frontend will detect empty audio and skip playback in mock mode.
    """
    # 44-byte minimal valid WAV header for 0 samples (silence)
    wav_header = bytes([
        0x52,0x49,0x46,0x46, 0x24,0x00,0x00,0x00,
        0x57,0x41,0x56,0x45, 0x66,0x6d,0x74,0x20,
        0x10,0x00,0x00,0x00, 0x01,0x00,0x01,0x00,
        0x40,0x1f,0x00,0x00, 0x40,0x1f,0x00,0x00,
        0x01,0x00,0x08,0x00, 0x64,0x61,0x74,0x61,
        0x00,0x00,0x00,0x00,
    ])
    return base64.b64encode(wav_header).decode()
