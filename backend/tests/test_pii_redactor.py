"""
Unit tests for pii_redactor — redact / unredact, all pattern types, feature flag.
Run with: pytest backend/tests/test_pii_redactor.py -v
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from config import settings
from services.pii_redactor import redact, unredact


@pytest.fixture(autouse=True)
def enable_redaction(monkeypatch):
    """All tests run with PII redaction enabled unless they explicitly test the flag."""
    monkeypatch.setattr(settings, "pii_redaction_enabled", True)


# ── Phone numbers ─────────────────────────────────────────────────────────────

class TestPhoneRedaction:
    def test_10_digit_mobile(self):
        text, tokens = redact("Call me at 9876543210", "en")
        assert "9876543210" not in text
        assert "PHONE_1" in text
        assert tokens["PHONE_1"] == "9876543210"

    def test_plus91_space_prefix(self):
        text, tokens = redact("My number is +91 9876543210", "en")
        assert "9876543210" not in text
        assert len(tokens) == 1

    def test_plus91_no_space_prefix(self):
        text, tokens = redact("Reach me at +919876543210", "en")
        assert "919876543210" not in text

    def test_zero_prefix(self):
        text, tokens = redact("Landline: 09123456789", "en")
        assert "9123456789" not in text

    def test_multiple_phones_get_distinct_tokens(self):
        text, tokens = redact("Primary 9876543210 backup 8765432109", "en")
        assert "PHONE_1" in text
        assert "PHONE_2" in text
        assert len(tokens) == 2

    def test_short_number_not_redacted(self):
        text, tokens = redact("extension 1234", "en")
        assert "1234" in text
        assert not tokens

    def test_number_in_sentence(self):
        text, tokens = redact("ನನ್ನ ಫೋನ್ 9988776655 ಆಗಿದೆ", "kn")
        assert "9988776655" not in text


# ── Aadhaar ───────────────────────────────────────────────────────────────────

class TestAadhaarRedaction:
    def test_12_digits_no_separator(self):
        text, tokens = redact("Aadhaar: 123456789012", "en")
        assert "123456789012" not in text
        assert "AADHAAR_1" in text
        assert tokens["AADHAAR_1"] == "123456789012"

    def test_space_separated(self):
        text, tokens = redact("ID: 1234 5678 9012", "en")
        assert "1234 5678 9012" not in text
        assert "AADHAAR_1" in text

    def test_dash_separated(self):
        text, tokens = redact("Aadhaar 1234-5678-9012 verified", "en")
        assert "1234-5678-9012" not in text

    def test_not_redacted_if_13_digits(self):
        # 13-digit number should NOT trigger Aadhaar redaction
        text, tokens = redact("Number 1234567890123", "en")
        assert "AADHAAR" not in text

    def test_aadhaar_precedes_phone_match(self):
        # An Aadhaar starting with 9 should not be split into a phone number
        text, tokens = redact("Aadhaar 9876 5432 1012", "en")
        aadhaar_tokens = {k: v for k, v in tokens.items() if k.startswith("AADHAAR")}
        phone_tokens = {k: v for k, v in tokens.items() if k.startswith("PHONE")}
        assert aadhaar_tokens  # one Aadhaar token
        assert not phone_tokens  # no spurious phone match


# ── Addresses ─────────────────────────────────────────────────────────────────

class TestAddressRedaction:
    def test_door_no_prefix(self):
        text, tokens = redact("I live at door no. 45, MG Road", "en")
        addr_tokens = {k for k in tokens if k.startswith("ADDRESS")}
        assert addr_tokens

    def test_house_no_prefix(self):
        text, tokens = redact("House No 123/A, 2nd Cross", "en")
        assert any(k.startswith("ADDRESS") for k in tokens)

    def test_hash_prefix(self):
        text, tokens = redact("Address: #12, Jayanagar", "en")
        assert any(k.startswith("ADDRESS") for k in tokens)

    def test_street_number_with_keyword(self):
        text, tokens = redact("Located at 45 2nd Cross", "en")
        assert any(k.startswith("ADDRESS") for k in tokens)

    def test_road_keyword(self):
        # "No. 10, MG Road" — door-number prefix triggers match
        text, tokens = redact("Office at No. 10, MG Road", "en")
        assert any(k.startswith("ADDRESS") for k in tokens)


# ── Names ─────────────────────────────────────────────────────────────────────

class TestNameRedaction:
    def test_mr_prefix(self):
        text, tokens = redact("Mr. Ravi Kumar called", "en")
        assert "Ravi Kumar" not in text
        assert any(k.startswith("CITIZEN_NAME") for k in tokens)

    def test_mrs_prefix(self):
        text, tokens = redact("Mrs. Priya Sharma is waiting", "en")
        assert "Priya Sharma" not in text

    def test_dr_prefix(self):
        text, tokens = redact("Dr. Suresh Babu prescribed", "en")
        assert "Suresh Babu" not in text

    def test_shri_prefix(self):
        text, tokens = redact("Shri Ramesh Gowda submitted the form", "en")
        assert "Ramesh Gowda" not in text

    def test_smt_prefix(self):
        text, tokens = redact("Smt. Lakshmi Devi is the applicant", "en")
        assert "Lakshmi Devi" not in text

    def test_name_intro_english(self):
        text, tokens = redact("My name is Rajesh Kumar", "en")
        assert "Rajesh Kumar" not in text
        assert any(k.startswith("CITIZEN_NAME") for k in tokens)

    def test_name_intro_iam_english(self):
        text, tokens = redact("I am Deepak Nair calling from Mangaluru", "en")
        assert "Deepak Nair" not in text

    def test_name_intro_hindi(self):
        text, tokens = redact("मेरा नाम रमेश कुमार है", "hi")
        assert "रमेश" not in text
        assert any(k.startswith("CITIZEN_NAME") for k in tokens)

    def test_name_intro_kannada(self):
        text, tokens = redact("ನನ್ನ ಹೆಸರು ರವಿ ಕುಮಾರ", "kn")
        assert "ರವಿ" not in text
        assert any(k.startswith("CITIZEN_NAME") for k in tokens)

    def test_kannada_honorific(self):
        text, tokens = redact("ಶ್ರೀ ರಾಜೇಶ್ ಗೌಡ ಅವರು ಬಂದಿದ್ದಾರೆ", "kn")
        assert any(k.startswith("CITIZEN_NAME") for k in tokens)


# ── unredact ──────────────────────────────────────────────────────────────────

class TestUnredact:
    def test_restores_phone(self):
        text, tokens = redact("Call 9876543210", "en")
        restored = unredact(text, tokens)
        assert "9876543210" in restored

    def test_restores_aadhaar(self):
        text, tokens = redact("Aadhaar 1234 5678 9012", "en")
        restored = unredact(text, tokens)
        assert "1234 5678 9012" in restored

    def test_restores_multiple_tokens(self):
        text, tokens = redact("Call 9876543210, Aadhaar: 123456789012", "en")
        restored = unredact(text, tokens)
        assert "9876543210" in restored
        assert "123456789012" in restored

    def test_empty_token_map_returns_input(self):
        original = "No PII here"
        assert unredact(original, {}) == original

    def test_unknown_tokens_left_intact(self):
        # unredact should leave tokens it doesn't know about unchanged
        result = unredact("Hello PHONE_99 world", {"PHONE_1": "9999999999"})
        assert "PHONE_99" in result


# ── Round-trip ────────────────────────────────────────────────────────────────

class TestRoundTrip:
    def test_phone_round_trip(self):
        original = "Please call 9876543210 for details"
        redacted, tokens = redact(original, "en")
        assert unredact(redacted, tokens) == original

    def test_mixed_pii_round_trip(self):
        original = "Mr. Ravi Kumar, Aadhaar 1234 5678 9012, phone +91 9876543210"
        redacted, tokens = redact(original, "en")
        restored = unredact(redacted, tokens)
        assert "Ravi Kumar" in restored
        assert "1234 5678 9012" in restored
        assert "9876543210" in restored


# ── Feature flag ──────────────────────────────────────────────────────────────

class TestFeatureFlag:
    def test_disabled_returns_original_unchanged(self, monkeypatch):
        monkeypatch.setattr(settings, "pii_redaction_enabled", False)
        original = "Phone 9876543210, Aadhaar 123456789012"
        text, tokens = redact(original, "en")
        assert text == original
        assert tokens == {}

    def test_enabled_redacts_phone(self, monkeypatch):
        monkeypatch.setattr(settings, "pii_redaction_enabled", True)
        text, tokens = redact("Phone 9876543210", "en")
        assert "9876543210" not in text
        assert tokens
