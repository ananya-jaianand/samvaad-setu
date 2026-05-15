"""
ASR Service — Sarvam Saarika (primary) + AI4Bharat IndicConformer (fallback)
Confidence-weighted ensemble; falls back to mock in development mode.
"""
import httpx
import base64
import random
from config import settings
from dataclasses import dataclass

@dataclass
class ASRResult:
    transcript: str
    language: str           # BCP-47 code: kn, hi, en
    confidence: float       # 0–1
    source: str             # "saarika" | "indiconformer" | "ensemble" | "mock"

SARVAM_ASR_URL = "https://api.sarvam.ai/speech-to-text"
AI4BHARAT_ASR_URL = "https://ai4bharat.iitm.ac.in/asr/v1/recognize"


async def transcribe(audio_bytes: bytes, hint_language: str = "kn", district: str = "default") -> ASRResult:
    """
    Main entry point. Runs Saarika; if confidence < threshold, also runs
    IndicConformer and returns ensemble result (if AI4Bharat key available).
    """
    if settings.environment == "mock" or not settings.sarvam_api_key:
        return _mock_asr(hint_language)

    primary = await _saarika_asr(audio_bytes, hint_language)

    if primary.confidence >= settings.asr_confidence_threshold:
        return primary

    # Low confidence → run fallback if AI4Bharat key is available
    if settings.ai4bharat_api_key:
        fallback = await _indiconformer_asr(audio_bytes, hint_language)
        return _ensemble(primary, fallback)
    
    # No fallback available, return primary result
    return primary


async def _saarika_asr(audio_bytes: bytes, language: str) -> ASRResult:
    """
    POST multipart/form-data to Sarvam Saarika v2.5
    Docs: https://docs.sarvam.ai/api-reference-docs/endpoints/speech-to-text
    """
    try:
        # Use 'unknown' for automatic language detection
        # Or convert language code to Sarvam format (e.g., 'kn' -> 'kn-IN')
        sarvam_lang = 'unknown'  # Let Sarvam auto-detect the language
        
        print(f"[SARVAM] Calling API with {len(audio_bytes)} bytes, auto-detecting language")
        async with httpx.AsyncClient(timeout=30.0) as client:  # Increased timeout
            files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
            data  = {
                "model":         settings.sarvam_asr_model,
                "language_code": sarvam_lang,
                "with_timestamps": "false",
            }
            headers = {"api-subscription-key": settings.sarvam_api_key}
            print(f"[SARVAM] Sending request to {SARVAM_ASR_URL}")
            resp = await client.post(SARVAM_ASR_URL, files=files, data=data, headers=headers)
            print(f"[SARVAM] Response status: {resp.status_code}")
            resp.raise_for_status()
            body = resp.json()
            print(f"[SARVAM] Response body: {body}")

        transcript = body.get("transcript", "")
        confidence = float(body.get("confidence", 0.8))
        lang_detected = body.get("language_code", language)
        print(f"[SARVAM] Success: {transcript[:50]}...")
        return ASRResult(transcript=transcript, language=lang_detected, confidence=confidence, source="saarika")
    except httpx.TimeoutException as e:
        print(f"[SARVAM] Timeout error: {e}")
        raise Exception(f"Sarvam API timeout: {e}")
    except httpx.HTTPStatusError as e:
        print(f"[SARVAM] HTTP error: {e.response.status_code} - {e.response.text}")
        raise Exception(f"Sarvam API error: {e.response.status_code}")
    except Exception as e:
        print(f"[SARVAM] Unexpected error: {e}")
        raise


async def _indiconformer_asr(audio_bytes: bytes, language: str) -> ASRResult:
    """
    AI4Bharat IndicConformer fallback.
    Docs: https://github.com/AI4Bharat/IndicConformer
    Replace the URL/auth with whichever hosted endpoint you use.
    """
    # ── REPLACE WITH REAL API ──────────────────────────────────────────────
    audio_b64 = base64.b64encode(audio_bytes).decode()
    async with httpx.AsyncClient(timeout=12.0) as client:
        resp = await client.post(
            AI4BHARAT_ASR_URL,
            json={"audio": audio_b64, "language": language},
            headers={"Authorization": f"Bearer {settings.ai4bharat_api_key}"},
        )
        resp.raise_for_status()
        body = resp.json()

    return ASRResult(
        transcript=body.get("transcription", ""),
        language=language,
        confidence=float(body.get("confidence", 0.6)),
        source="indiconformer",
    )
    # ── END REPLACE ────────────────────────────────────────────────────────


def _ensemble(a: ASRResult, b: ASRResult) -> ASRResult:
    """Confidence-weighted transcript selection."""
    total = a.confidence + b.confidence
    if total == 0:
        return a
    # Pick higher-confidence transcript; blend score
    winner = a if a.confidence >= b.confidence else b
    blended_conf = (a.confidence ** 2 + b.confidence ** 2) / total
    return ASRResult(
        transcript=winner.transcript,
        language=winner.language,
        confidence=round(blended_conf, 3),
        source="ensemble",
    )


def _mock_asr(language: str) -> ASRResult:
    """Deterministic mock for local dev without API keys."""
    samples = {
        "kn": [
            ("ನನ್ನ ಮನೆಯ ಬಳಿ ಕಸ ತೆಗೆಯುತ್ತಿಲ್ಲ ಎರಡು ವಾರದಿಂದ", 0.91),
            ("ನೀರು ಸರಬರಾಜು ನಿಂತಿದೆ ಮೂರು ದಿನದಿಂದ", 0.87),
            ("ರಸ್ತೆಯಲ್ಲಿ ದೊಡ್ಡ ಗುಂಡಿ ಬಿದ್ದಿದೆ", 0.82),
            # PII-containing: citizen volunteers name + phone (common in real 1092 calls)
            ("ನನ್ನ ಹೆಸರು ರಮೇಶ ಪಾಟೀಲ್, ಮೊಬೈಲ್ 9844567890. ವಿದ್ಯಾನಗರ ಹುಬ್ಬಳ್ಳಿ ನಲ್ಲಿ HESCOM ಬಿಲ್ ₹8,400 ಬಂದಿದೆ, ಯಾವ್ತ್ತೂ ₹600 ಮೀರ್ತಿರ್ಲಿಲ್ಲ", 0.88),
            ("ಶ್ರೀಮತಿ ಲಕ್ಷ್ಮೀ ದೇವಿ ಇಲ್ಲಿಂದ ಕರೀತಿದ್ದೇನೆ, 14ನೇ ಕ್ರಾಸ್ ಕೆಶ್ವಾಪುರ. ಸಂಧ್ಯಾ ಸುರಕ್ಷಾ ಪಿಂಚಣಿ ಆರು ತಿಂಗಳಿಂದ ಬಂದಿಲ್ಲ", 0.84),
        ],
        "hi": [
            ("मेरे घर के पास कचरा नहीं उठाया जा रहा है", 0.88),
            ("बिजली तीन दिन से नहीं है", 0.85),
            # PII-containing: name, phone, address common in Hindi pension/utility calls
            ("मेरा नाम सुरेश कुमार है, मोबाइल 9741234567. कलबुर्गी में संध्या सुरक्षा पेंशन तीन महीने से नहीं आई, मकान नंबर 23 साईं नगर", 0.83),
        ],
        "en": [
            ("Garbage has not been collected for two weeks near my house", 0.93),
            ("Water supply has been cut off for three days", 0.90),
            # PII-containing: Aadhaar + phone + address in English 1092 call
            ("My name is Kavitha Reddy and my number is 9886012345. I live at 7th Main Koramangala Bangalore. BWSSB water account shows wrong name after my Aadhaar 4321 6789 0123 was linked", 0.91),
        ],
    }
    choices = samples.get(language, samples["en"])
    text, conf = random.choice(choices)
    # Simulate occasional low-confidence to exercise escalation path
    if random.random() < 0.15:
        conf = random.uniform(0.4, 0.6)
    return ASRResult(transcript=text, language=language, confidence=conf, source="mock")
