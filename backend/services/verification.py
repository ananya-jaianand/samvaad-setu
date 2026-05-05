"""
Verification Engine — three-state confirmation loop.
This is the core differentiator: we confirm before we commit.
States: correct | partially_correct | incorrect
"""
import re
from config import settings
from models.session_model import VerificationState

# Confirmation keywords per language
CONFIRM_KEYWORDS = {
    "kn": {
        "correct":           ["ಹೌದು", "ಸರಿ", "ಆಯ್ತು", "ಸರಿಯಾಗಿದೆ", "ಹ್ಞೂ", "ಹ"],
        "partially_correct": ["ಸ್ವಲ್ಪ", "ಭಾಗಶಃ", "ಆದ್ರೆ", "ಅಲ್ಲ", "ಇಲ್ಲ ಆದ್ರೆ"],
        "incorrect":         ["ಇಲ್ಲ", "ತಪ್ಪು", "ಅಲ್ಲ", "ಹಾಗಲ್ಲ"],
    },
    "hi": {
        "correct":           ["हाँ", "सही", "ठीक है", "हां", "जी हाँ", "बिल्कुल"],
        "partially_correct": ["थोड़ा", "लेकिन", "मगर", "पर", "लेकिन नहीं"],
        "incorrect":         ["नहीं", "गलत", "ऐसा नहीं", "नही"],
    },
    "en": {
        "correct":           ["yes", "correct", "right", "exactly", "that's it", "yeah", "yep"],
        "partially_correct": ["sort of", "mostly", "but", "however", "not quite", "partly"],
        "incorrect":         ["no", "wrong", "not right", "that's not", "incorrect", "nope"],
    },
}


def classify_verification_response(response_text: str, language: str) -> VerificationState:
    """
    Classify citizen's verification response into one of three states.
    Uses keyword matching with priority: incorrect > partially_correct > correct.
    """
    text_lower = response_text.lower().strip()
    keywords = CONFIRM_KEYWORDS.get(language, CONFIRM_KEYWORDS["en"])

    # Check all languages in case of code-switching
    all_keywords = {}
    for lang_kws in CONFIRM_KEYWORDS.values():
        for state, words in lang_kws.items():
            all_keywords.setdefault(state, []).extend(words)

    def _matches(words: list) -> bool:
        return any(w.lower() in text_lower for w in words)

    # Priority: incorrect first (most actionable), then partial, then correct
    if _matches(all_keywords.get("incorrect", [])):
        return "incorrect"
    if _matches(all_keywords.get("partially_correct", [])):
        return "partially_correct"
    if _matches(all_keywords.get("correct", [])):
        return "correct"

    # Ambiguous — treat as partially correct to trigger a gentle re-clarification
    return "partially_correct"


def get_clarification_prompt(language: str, attempt: int) -> str:
    """Progressive clarification prompts — warmer on first attempt, more direct later."""
    prompts = {
        "kn": [
            "ದಯವಿಟ್ಟು ಮತ್ತೊಮ್ಮೆ ಹೇಳಿ — ನಿಮ್ಮ ಮನೆ ಹತ್ತಿರ ಏನಾಗಿದೆ?",
            "ನಿಮ್ಮ ಸಮಸ್ಯೆ ಸರಿಯಾಗಿ ಅರ್ಥವಾಗಲಿಲ್ಲ. ನಿಧಾನವಾಗಿ ಒಂದು ಸಲ ಹೇಳಿ.",
            "ಕ್ಷಮಿಸಿ, ನಿಮ್ಮನ್ನು ಮನುಷ್ಯ ಏಜೆಂಟ್‌ಗೆ ಸಂಪರ್ಕಿಸುತ್ತೇನೆ.",
        ],
        "hi": [
            "कृपया एक बार और बताएं — आपके पास क्या समस्या है?",
            "मुझे सही समझ नहीं आया। धीरे-धीरे एक बार बताइए।",
            "माफ़ करें, मैं आपको एक इंसान से जोड़ रहा हूँ।",
        ],
        "en": [
            "Could you describe the problem once more? I want to make sure I understand.",
            "I'm having trouble understanding. Could you say it slowly?",
            "I'll connect you to a human agent who can help you better.",
        ],
    }
    lang_prompts = prompts.get(language, prompts["en"])
    idx = min(attempt, len(lang_prompts) - 1)
    return lang_prompts[idx]


def get_acknowledgment(language: str, intent: str) -> str:
    """Acknowledgment after successful verification."""
    acks = {
        "kn": f"ಸರಿ, ನಿಮ್ಮ {_intent_label_kn(intent)} ಸಮಸ್ಯೆ ದಾಖಲಿಸಲಾಗಿದೆ. ಒಂದು ಕ್ಷಣ ತಡೆಯಿರಿ.",
        "hi": f"ठीक है, आपकी {_intent_label_hi(intent)} की समस्या दर्ज कर ली गई है। एक पल रुकिए।",
        "en": f"Got it. Your {intent.replace('_', ' ')} complaint has been noted. Please hold for a moment.",
    }
    return acks.get(language, acks["en"])


def _intent_label_kn(intent: str) -> str:
    labels = {
        "sanitation_garbage": "ಕಸ ವಿಲೇವಾರಿ",
        "water_supply_complaint": "ನೀರು ಸರಬರಾಜು",
        "electricity_outage": "ವಿದ್ಯುತ್ ಕಡಿತ",
        "road_damage": "ರಸ್ತೆ ಹಾನಿ",
        "other_grievance": "ದೂರು",
    }
    return labels.get(intent, "ದೂರು")


def _intent_label_hi(intent: str) -> str:
    labels = {
        "sanitation_garbage": "कचरा संग्रह",
        "water_supply_complaint": "जल आपूर्ति",
        "electricity_outage": "बिजली कटौती",
        "road_damage": "सड़क क्षति",
        "other_grievance": "शिकायत",
    }
    return labels.get(intent, "शिकायत")
