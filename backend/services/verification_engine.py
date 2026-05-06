"""
Verification Engine — dialect-aware restatement and three-state confirmation loop.
Central constraint: citizen must explicitly confirm understanding before intent is committed.
"""
import json
import random
from pathlib import Path
from typing import Optional

from models.session_model import SessionState
from services import verification as _legacy
from services.dialect_context import DialectContextProvider

_dialect_provider = DialectContextProvider()

_PHRASINGS_PATH = Path(__file__).parent.parent / "data" / "verification_phrasings.json"
_phrasings_cache: dict = {}


def _load_phrasings() -> dict:
    global _phrasings_cache
    if not _phrasings_cache:
        with open(_PHRASINGS_PATH, encoding="utf-8") as f:
            _phrasings_cache = json.load(f)
    return _phrasings_cache


# Human-readable intent labels per language for use in verification prompts
_INTENT_LABELS: dict[str, dict[str, str]] = {
    "kn": {
        "sanitation_garbage":       "ಕಸ ಸಂಗ್ರಹ",
        "water_supply_complaint":   "ನೀರು ಸರಬರಾಜು",
        "electricity_outage":       "ವಿದ್ಯುತ್ ಕಡಿತ",
        "road_damage":              "ರಸ್ತೆ ಹಾನಿ",
        "property_tax_query":       "ಆಸ್ತಿ ತೆರಿಗೆ",
        "birth_death_certificate":  "ಜನನ/ಮರಣ ಪ್ರಮಾಣಪತ್ರ",
        "ration_card_issue":        "ಪಡಿತರ ಚೀಟಿ",
        "pension_scheme":           "ಪಿಂಚಣಿ",
        "police_complaint":         "ಪೊಲೀಸ್ ದೂರು",
        "health_facility":          "ಆರೋಗ್ಯ ಸೇವೆ",
        "education_school":         "ಶಿಕ್ಷಣ",
        "land_records":             "ಭೂ ದಾಖಲೆ",
        "other_grievance":          "ದೂರು",
    },
    "hi": {
        "sanitation_garbage":       "कचरा संग्रह",
        "water_supply_complaint":   "जल आपूर्ति",
        "electricity_outage":       "बिजली कटौती",
        "road_damage":              "सड़क क्षति",
        "property_tax_query":       "संपत्ति कर",
        "birth_death_certificate":  "जन्म/मृत्यु प्रमाण पत्र",
        "ration_card_issue":        "राशन कार्ड",
        "pension_scheme":           "पेंशन",
        "police_complaint":         "पुलिस शिकायत",
        "health_facility":          "स्वास्थ्य सेवा",
        "education_school":         "शिक्षा",
        "land_records":             "भूमि रिकॉर्ड",
        "other_grievance":          "शिकायत",
    },
    "en": {
        "sanitation_garbage":       "garbage collection",
        "water_supply_complaint":   "water supply",
        "electricity_outage":       "electricity outage",
        "road_damage":              "road damage",
        "property_tax_query":       "property tax",
        "birth_death_certificate":  "birth/death certificate",
        "ration_card_issue":        "ration card",
        "pension_scheme":           "pension scheme",
        "police_complaint":         "police complaint",
        "health_facility":          "health facility",
        "education_school":         "education",
        "land_records":             "land records",
        "other_grievance":          "grievance",
    },
}


class VerificationEngine:
    def generate_verification_prompt(
        self,
        intent: str,
        entities: dict,
        language: str,
        district: str,
    ) -> str:
        """
        Returns a natural, dialect-conditioned restatement of the citizen's issue.
        Selects a random variant so repeated turns don't sound robotic.
        """
        phrasings = _load_phrasings()
        lang_phrasings = phrasings.get(language) or phrasings.get("en", {})

        # Use DialectContextProvider for richer profile including vocabulary
        profile = _dialect_provider.get_profile(district)
        variant_key = profile.dialect_tag

        # Prefer dialect-specific variants; fall back to language default
        variants = lang_phrasings.get(variant_key) or lang_phrasings.get("default", [])
        if not variants:
            return "Did I understand you correctly?"

        template = random.choice(variants)

        issue_map = _INTENT_LABELS.get(language, _INTENT_LABELS["en"])
        issue = issue_map.get(intent, intent.replace("_", " "))

        # For Kannada, optionally flavour the issue label with local vocabulary
        if language == "kn" and profile.vocabulary_hints:
            # Append a common affirmative phrase from the profile if available
            affirmatives = [k for k in profile.vocabulary_hints if k in ("ಆತ್", "ಆಯ್ತ", "ಆಗ್ಲಾ", "ಆತ")]
            if affirmatives and not template.startswith(affirmatives[0]):
                template = affirmatives[0] + ", " + template[0].lower() + template[1:]

        return template.format(issue=issue)

    def process_verification_response(
        self,
        session: SessionState,
        state: str,
        correction_text: Optional[str] = None,
    ) -> dict:
        """
        Handle one verification response from the citizen.

        state must be "correct" | "partial" | "incorrect".

        Returns a dict with:
          action:                  "confirmed" | "clarify" | "escalate"
          new_verification_state:  updated session-level state string
          clarification_prompt:    str — present if action == "clarify"
          escalation_reason:       str — present if action == "escalate"
        """
        if state == "correct":
            session.verification_state = "confirmed"
            return {
                "action": "confirmed",
                "new_verification_state": "confirmed",
            }

        # Both "partial" and "incorrect" follow the same re-clarify / escalate path.
        session.clarification_count += 1
        if session.clarification_count < 2:
            session.verification_state = "partial"
            prompt = _legacy.get_clarification_prompt(
                session.detected_language, session.clarification_count
            )
            return {
                "action": "clarify",
                "new_verification_state": "partial",
                "clarification_prompt": prompt,
            }

        session.verification_state = "escalated"
        return {
            "action": "escalate",
            "new_verification_state": "escalated",
            "escalation_reason": "repeated_clarification",
        }
