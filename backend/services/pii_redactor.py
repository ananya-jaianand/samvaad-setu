"""
PII Redactor — strip sensitive data before LLM calls, restore for display.

Redaction tokens:
  PHONE_N        → Indian phone numbers (10-digit, +91 optional)
  AADHAAR_N      → 12-digit Aadhaar-like sequences
  CITIZEN_NAME_N → Names detected via honorifics or self-intro phrases
  ADDRESS_N      → Door numbers and street/area patterns

Usage:
  redacted, token_map = redact(text, "kn")
  original = unredact(redacted, token_map)

Controlled by settings.pii_redaction_enabled; returns input unchanged when off.
"""
import re
from config import settings

# ── Phone numbers ─────────────────────────────────────────────────────────────
# +91/91/0 prefix optional; mobile range 6–9 followed by 9 more digits
_PHONE_RE = re.compile(
    r'(?<!\d)(?:\+91[\s\-]?|91[\s\-]?|0)?[6-9]\d{9}(?!\d)'
)

# ── Aadhaar ───────────────────────────────────────────────────────────────────
# Exactly 12 digits, optionally space/dash-separated in groups of 4
_AADHAAR_RE = re.compile(
    r'(?<!\d)\d{4}[\s\-]?\d{4}[\s\-]?\d{4}(?!\d)'
)

# ── Addresses ─────────────────────────────────────────────────────────────────
# Door/house/flat number prefix, or street-number + keyword suffix
_ADDRESS_RE = re.compile(
    r'(?:'
    r'(?:door|house|flat|plot|site|no\.?|#)\s*(?:no\.?)?\s*\d+[\w/\-]*'
    r'|'
    r'\d+[\w/\-]*\s*,?\s*(?:\d+(?:st|nd|rd|th)\s+)?'
    r'(?:cross|main|street|road|nagar|layout|colony|circle|avenue|lane|extension)'
    r')',
    re.IGNORECASE,
)

# ── Names via honorifics ──────────────────────────────────────────────────────
# Matches "Mr. Ravi Kumar", "Smt. Lakshmi Devi", "ಶ್ರೀ ರವಿ", etc.
_HONORIFIC_NAME_RE = re.compile(
    r'(?:Mr\.?|Mrs\.?|Ms\.?|Miss|Dr\.?|Prof\.?|Shri\.?|Smt\.?|Sri\.?|Kumari\.?|Rev\.?|'
    r'श्री\s*\.?|श्रीमती\s*\.?|कुमारी\s*\.?|डॉ\s*\.?|'
    r'ಶ್ರೀ\s*\.?|ಶ್ರೀಮತಿ\s*\.?|ಡಾ\s*\.?'
    r')\s+'
    r'[\wऀ-ॿಀ-೿][\wऀ-ॿಀ-೿]*'
    r'(?:\s+[\wऀ-ॿಀ-೿][\wऀ-ॿಀ-೿]*){0,3}',
    re.UNICODE | re.IGNORECASE,
)

# ── Names via self-introduction phrases ───────────────────────────────────────
# Language-keyed; group 1 captures the name portion only
_NAME_INTRO_RE: dict[str, re.Pattern] = {
    "en": re.compile(
        r"(?:my name is|i(?:'m| am)|this is|call(?:ing|ed)|name(?:'s| is))\s+"
        r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})",
        re.IGNORECASE,
    ),
    "hi": re.compile(
        r"(?:मेरा नाम|मेरा नाम है|नाम है|मैं)\s+"
        r"([ऀ-ॿ]+(?:\s+[ऀ-ॿ]+){0,2})",
        re.UNICODE,
    ),
    "kn": re.compile(
        r"(?:ನನ್ನ ಹೆಸರು|ಹೆಸರು|ನಾನು)\s+"
        r"([ಀ-೿]+(?:\s+[ಀ-೿]+){0,2})",
        re.UNICODE,
    ),
}


def redact(text: str, language: str = "en") -> tuple[str, dict]:
    """
    Redact PII from text.  Returns (redacted_text, token_map).
    token_map maps each placeholder token back to the original string.
    No-op when settings.pii_redaction_enabled is False.
    """
    if not settings.pii_redaction_enabled:
        return text, {}

    token_map: dict[str, str] = {}
    counters: dict[str, int] = {}

    def _next(prefix: str) -> str:
        counters[prefix] = counters.get(prefix, 0) + 1
        return f"{prefix}_{counters[prefix]}"

    def _replacer(prefix: str):
        def _sub(m: re.Match) -> str:
            tok = _next(prefix)
            token_map[tok] = m.group(0)
            return tok
        return _sub

    # Order matters: Aadhaar (12-digit) before phone (10-digit) to prevent
    # partial overlap when an Aadhaar digit sequence starts with 6-9.
    text = _AADHAAR_RE.sub(_replacer("AADHAAR"), text)
    text = _PHONE_RE.sub(_replacer("PHONE"), text)
    text = _ADDRESS_RE.sub(_replacer("ADDRESS"), text)

    # Honorific-prefixed names (high precision)
    text = _HONORIFIC_NAME_RE.sub(_replacer("CITIZEN_NAME"), text)

    # Language-specific self-introduction patterns; only group(1) is the name
    lang_re = _NAME_INTRO_RE.get(language)
    if lang_re:
        def _intro_sub(m: re.Match) -> str:
            name = m.group(1)
            offset = m.start(1) - m.start(0)
            tok = _next("CITIZEN_NAME")
            token_map[tok] = name
            return m.group(0)[:offset] + tok
        text = lang_re.sub(_intro_sub, text)

    return text, token_map


def unredact(redacted_text: str, token_map: dict) -> str:
    """Replace redaction tokens with their original values."""
    if not token_map:
        return redacted_text
    result = redacted_text
    for token, original in token_map.items():
        result = result.replace(token, original)
    return result