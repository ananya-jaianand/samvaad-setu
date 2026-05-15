# pyrefly: ignore [missing-import]
from pydantic_settings import BaseSettings
from typing import Literal

class Settings(BaseSettings):
    # API Keys
    anthropic_api_key: str = ""
    gemini_api_key: str = ""         # Google Gemini API key
    sarvam_api_key: str = ""         # get from api.sarvam.ai
    ai4bharat_api_key: str = ""      # get from ai4bharat.org

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Postgres
    postgres_url: str = "postgresql://localhost:5432/samvaad_setu"

    # App
    environment: Literal["mock", "production"] = "mock"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000", "http://localhost:8081"]
    max_session_minutes: int = 30

    # Escalation thresholds
    asr_confidence_threshold: float = 0.65
    intent_entropy_threshold: float = 0.45
    distress_score_threshold: float = 0.70
    max_clarification_turns: int = 3

    # Model config
    claude_model: str = "claude-sonnet-4-20250514"
    sarvam_asr_model: str = "saarika:v2.5"
    sarvam_tts_model: str = "bulbul:v1"

    # Feature flags
    enable_prosody: bool = False            # set True to activate librosa prosodic extraction
    pii_redaction_enabled: bool = False     # set True in production to mask PII before LLM calls

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

# District → dialect context mapping
# Derived from IndicVoices + Kathbath dialect-tagged data
DISTRICT_DIALECT_MAP = {
    "mysuru":          {"variant": "mysuru",        "vocabulary_hints": "ಆಗ್ಲಾ, ಇರ್ಲಿ, ಮಾಡ್ಲಿ", "formality": "high"},
    "mangaluru":       {"variant": "tulu_coast",    "vocabulary_hints": "ಆತ್, ಉಂಡು, ಮಲ್ಪುವ", "formality": "medium"},
    "belagavi":        {"variant": "north_karnataka","vocabulary_hints": "ಆತ, ಇಲ್ಲಾ, ಮಾಡ್ರಿ",  "formality": "medium"},
    "kalaburagi":      {"variant": "hyderabad_ka",  "vocabulary_hints": "ಆತ್ ಬಿಡ್ರಿ, ಮಾಡ್ರಿ",  "formality": "medium"},
    "bengaluru_urban": {"variant": "urban_kannada", "vocabulary_hints": "ಆಯ್ತ, ಮಾಡ್ತೀನಿ",    "formality": "low"},
    "default":         {"variant": "standard",      "vocabulary_hints": "",                    "formality": "medium"},
}

# Grievance intent taxonomy (from Sevasindhu / Janasevaka categories)
INTENT_TAXONOMY = [
    "water_supply_complaint",
    "electricity_outage",
    "road_damage",
    "sanitation_garbage",
    "property_tax_query",
    "birth_death_certificate",
    "ration_card_issue",
    "pension_scheme",
    "police_complaint",
    "health_facility",
    "education_school",
    "land_records",
    "other_grievance",
]

SUPPORTED_LANGUAGES = {
    "kn": "Kannada",
    "hi": "Hindi",
    "en": "English",
}

# Verification phrases per language
VERIFICATION_PHRASES = {
    "kn": "ನಾನು ಅರ್ಥಮಾಡಿಕೊಂಡಿದ್ದು ಸರಿಯಾಗಿದೆಯಾ?",
    "hi": "ಕ್ಯಾ ಮೈಂನೇ ಸಹಿ ಸಮಝಾ?",
    "en": "Did I understand that correctly?",
}
