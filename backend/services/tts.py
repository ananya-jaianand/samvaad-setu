"""
TTS Service — Sarvam Bulbul (primary).
"""
import base64
import httpx

from config import settings

SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"
_SARVAM_SPEAKER = "anushka"
_SARVAM_LANG_MAP = {
    "kn": "kn-IN",
    "hi": "hi-IN",
    "en": "en-IN",
}

# Prosody presets per sentiment
_PROSODY_MAP = {
    "distress": {"pace": 0.85, "pitch": -0.1},
    "anger":    {"pace": 0.88, "pitch": -0.05},
    "fear":     {"pace": 0.85, "pitch": -0.1},
    "urgency":  {"pace": 0.92, "pitch": 0.0},
    "calm":     {"pace": 1.00, "pitch": 0.0},
}


async def synthesize(
    text: str,
    language: str = "kn",
    sentiment_label: str = "calm",
) -> str:
    """Returns base64-encoded WAV from Sarvam Bulbul TTS."""
    if settings.environment == "mock":
        return ""

    text = text.strip()
    if not text:
        return ""

    if not settings.sarvam_api_key:
        return ""

    base_lang = language.split("-")[0]
    prosody = _PROSODY_MAP.get(sentiment_label, _PROSODY_MAP["calm"])
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                SARVAM_TTS_URL,
                json={
                    "inputs": [text],
                    "target_language_code": _SARVAM_LANG_MAP.get(base_lang, "kn-IN"),
                    "speaker": _SARVAM_SPEAKER,
                    "model": settings.sarvam_tts_model,
                    "pace": prosody["pace"],
                    "pitch": prosody["pitch"],
                    "loudness": 1.0,
                    "speech_sample_rate": 8000,
                    "enable_preprocessing": True,
                },
                headers={"api-subscription-key": settings.sarvam_api_key},
            )
            resp.raise_for_status()
            audio_b64 = resp.json()["audios"][0]
            print(f"[TTS] Sarvam OK")
            return audio_b64
    except Exception as e:
        print(f"[TTS] Sarvam failed: {e}")
        return ""
