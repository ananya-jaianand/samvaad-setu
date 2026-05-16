"""
TTS Service — Gemini 2.5 Flash TTS (primary) with Sarvam Bulbul fallback.

Gemini TTS auto-detects language from the input text, so Kannada text speaks
Kannada, Hindi speaks Hindi, etc. — no explicit language_code needed.
Sarvam is kept as fallback for Kannada/Hindi if Gemini fails.
"""
import io
import wave
import base64
import httpx
from google import genai
from google.genai import types as genai_types

from config import settings

# Gemini TTS client (reuses same key as NLU)
_gemini_client: genai.Client | None = (
    genai.Client(api_key=settings.gemini_api_key)
    if settings.gemini_api_key
    else None
)

_GEMINI_TTS_MODEL = "gemini-2.5-flash-preview-tts"

# Calm, professional female voice — suits a government helpline
_VOICE_NAME = "Kore"

# Sarvam fallback config
SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"
_SARVAM_SPEAKER = "meera"   # meera is the multi-language Bulbul v2 voice
_SARVAM_LANG_MAP = {
    "kn": "kn-IN",
    "hi": "hi-IN",
    "en": "en-IN",
}

# Prosody presets per sentiment — calmer for distress
_PROSODY_MAP = {
    "distress": {"pace": 0.85, "pitch": -0.1},
    "anger":    {"pace": 0.88, "pitch": -0.05},
    "fear":     {"pace": 0.85, "pitch": -0.1},
    "urgency":  {"pace": 0.92, "pitch": 0.0},
    "calm":     {"pace": 1.00, "pitch": 0.0},
}


def _pcm_to_wav_b64(pcm_bytes: bytes, sample_rate: int = 24000) -> str:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)   # 16-bit
        w.setframerate(sample_rate)
        w.writeframes(pcm_bytes)
    return base64.b64encode(buf.getvalue()).decode()


async def synthesize(
    text: str,
    language: str = "kn",
    sentiment_label: str = "calm",
) -> str:
    """
    Convert text to speech. Returns base64-encoded WAV.
    Tries Gemini TTS first; falls back to Sarvam if Gemini unavailable or fails.
    """
    if settings.environment == "mock":
        return ""

    text = text.strip()
    if not text:
        return ""

    # ── Primary: Gemini TTS ────────────────────────────────────────────────
    if _gemini_client and settings.gemini_api_key:
        try:
            response = await _gemini_client.aio.models.generate_content(
                model=_GEMINI_TTS_MODEL,
                contents=text,
                config=genai_types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=genai_types.SpeechConfig(
                        voice_config=genai_types.VoiceConfig(
                            prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(
                                voice_name=_VOICE_NAME
                            )
                        )
                    ),
                ),
            )
            pcm = response.candidates[0].content.parts[0].inline_data.data
            if pcm:
                print(f"[TTS] Gemini OK — {len(pcm)} PCM bytes")
                return _pcm_to_wav_b64(pcm)
        except Exception as e:
            print(f"[TTS] Gemini failed ({e}), trying Sarvam fallback")

    # ── Fallback: Sarvam Bulbul ────────────────────────────────────────────
    if settings.sarvam_api_key:
        try:
            base_lang = language.split("-")[0]
            prosody = _PROSODY_MAP.get(sentiment_label, _PROSODY_MAP["calm"])
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
                print(f"[TTS] Sarvam fallback OK")
                return audio_b64
        except Exception as e:
            print(f"[TTS] Sarvam fallback failed: {e}")

    return ""
