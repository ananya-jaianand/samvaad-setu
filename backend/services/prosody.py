"""
Prosody Service — extract pitch, energy, and speaking-rate features from audio.
Gated behind ENABLE_PROSODY flag; falls back to a neutral stub when disabled
or when librosa/soundfile are not installed.

High pitch variance + high energy + fast speaking rate → high distress signal.
"""
import io
import numpy as np
from config import settings

# Lazy import — if librosa isn't installed the stub path is used instead.
try:
    import librosa
    _LIBROSA_AVAILABLE = True
except ImportError:
    _LIBROSA_AVAILABLE = False


def extract_prosodic_features(audio_bytes: bytes) -> dict:
    """
    Extract pitch_mean, pitch_variance, energy_mean, speaking_rate,
    and voice_quality from raw audio bytes (WAV / any format soundfile handles).

    Returns a dict with float values in roughly normalised ranges.
    Falls back to neutral values when the flag is off, librosa is missing,
    or the audio is too short / undecodable.
    """
    if not settings.enable_prosody or not _LIBROSA_AVAILABLE or len(audio_bytes) < 1024:
        return _neutral_features()

    try:
        import soundfile as sf
        audio_io = io.BytesIO(audio_bytes)
        y, sr = sf.read(audio_io, dtype="float32")

        # Mono downmix
        if y.ndim > 1:
            y = y.mean(axis=1)

        if len(y) < sr * 0.1:          # shorter than 100 ms — not useful
            return _neutral_features()

        # ── Pitch (F0) via piptrack ───────────────────────────────────────────
        pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
        # Keep only high-magnitude pitch values per frame
        voiced = pitches[magnitudes > magnitudes.mean()]
        voiced = voiced[voiced > 50]   # filter sub-bass artefacts

        pitch_mean     = float(np.mean(voiced))     if len(voiced) > 0 else 0.0
        pitch_variance = float(np.var(voiced))      if len(voiced) > 0 else 0.0

        # ── RMS energy ────────────────────────────────────────────────────────
        rms = librosa.feature.rms(y=y)[0]
        energy_mean = float(np.mean(rms))

        # ── Speaking rate (zero-crossing rate as proxy) ───────────────────────
        zcr = librosa.feature.zero_crossing_rate(y=y)[0]
        speaking_rate = float(np.mean(zcr))

        # ── Voice quality (spectral flatness — breathiness proxy) ─────────────
        flatness = librosa.feature.spectral_flatness(y=y)[0]
        voice_quality = float(np.mean(flatness))

        return {
            "pitch_mean":      pitch_mean,
            "pitch_variance":  pitch_variance,
            "energy_mean":     energy_mean,
            "speaking_rate":   speaking_rate,
            "voice_quality":   voice_quality,
        }

    except Exception:
        return _neutral_features()


def prosodic_distress_score(features: dict) -> float:
    """
    Map prosodic features to a distress score in [0, 1].

    High pitch variance  → higher distress (trembling/crying voice)
    High energy          → higher distress (shouting / urgency)
    High speaking rate   → higher distress (fast, panicked speech)

    Each signal is normalised against empirically reasonable ranges and
    combined with equal weights.
    """
    # Normalise each feature to [0, 1] using soft-clamp ranges
    # (derived from typical read-speech vs distressed-speech studies)
    pitch_var_score  = _soft_clamp(features.get("pitch_variance",  0.0), lo=0, hi=5000)
    energy_score     = _soft_clamp(features.get("energy_mean",     0.0), lo=0, hi=0.15)
    rate_score       = _soft_clamp(features.get("speaking_rate",   0.0), lo=0.05, hi=0.20)

    # Equal weight across the three signals
    distress = (pitch_var_score + energy_score + rate_score) / 3.0
    return round(min(1.0, max(0.0, distress)), 4)


def _soft_clamp(value: float, lo: float, hi: float) -> float:
    """Linearly map value from [lo, hi] to [0, 1], clamped at boundaries."""
    if hi <= lo:
        return 0.0
    return max(0.0, min(1.0, (value - lo) / (hi - lo)))


def _neutral_features() -> dict:
    return {
        "pitch_mean":     150.0,
        "pitch_variance":  80.0,
        "energy_mean":      0.04,
        "speaking_rate":    0.08,
        "voice_quality":    0.01,
    }
