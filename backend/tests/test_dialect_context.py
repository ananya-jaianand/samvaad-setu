"""
Tests for DialectContextProvider and the dialect-conditioning of verification rephrasings.
Run with: pytest backend/tests/test_dialect_context.py -v
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from services.dialect_context import DialectContextProvider, DialectProfile
from services.verification_engine import VerificationEngine


@pytest.fixture
def provider():
    return DialectContextProvider()


@pytest.fixture
def engine():
    return VerificationEngine()


# ── DialectContextProvider ────────────────────────────────────────────────────

class TestDialectContextProvider:
    def test_returns_dialect_profile_instance(self, provider):
        profile = provider.get_profile("mangaluru")
        assert isinstance(profile, DialectProfile)

    def test_mangaluru_has_tulu_coast_tag(self, provider):
        profile = provider.get_profile("mangaluru")
        assert profile.dialect_tag == "tulu_coast"

    def test_bengaluru_urban_has_urban_kannada_tag(self, provider):
        profile = provider.get_profile("bengaluru_urban")
        assert profile.dialect_tag == "urban_kannada"

    def test_mysuru_is_formal(self, provider):
        profile = provider.get_profile("mysuru")
        assert profile.formality_register == "formal"

    def test_bengaluru_is_informal(self, provider):
        profile = provider.get_profile("bengaluru_urban")
        assert profile.formality_register == "informal"

    def test_unknown_district_falls_back_to_default(self, provider):
        profile = provider.get_profile("unknown_place_xyz")
        assert profile.district == "default"

    def test_mangaluru_vocabulary_hints_nonempty(self, provider):
        profile = provider.get_profile("mangaluru")
        assert len(profile.vocabulary_hints) > 0

    def test_all_nine_districts_loadable(self, provider):
        districts = [
            "bengaluru_urban", "bengaluru_rural", "mysuru",
            "mangaluru", "udupi", "hubballi_dharwad",
            "belagavi", "kalaburagi", "vijayapura",
        ]
        for d in districts:
            profile = provider.get_profile(d)
            assert profile.district == d, f"Profile mismatch for {d}"

    def test_common_phrases_nonempty_for_all_districts(self, provider):
        districts = ["bengaluru_urban", "mysuru", "mangaluru", "kalaburagi"]
        for d in districts:
            profile = provider.get_profile(d)
            assert len(profile.common_phrases) > 0, f"No common phrases for {d}"


class TestInjectIntoPrompt:
    def test_prepends_dialect_block(self, provider):
        profile = provider.get_profile("mangaluru")
        result = provider.inject_into_prompt(profile, "BASE PROMPT")
        assert result.startswith("===DIALECT CONTEXT===")
        assert "BASE PROMPT" in result

    def test_dialect_tag_present_in_block(self, provider):
        profile = provider.get_profile("mangaluru")
        result = provider.inject_into_prompt(profile, "BASE")
        assert "tulu_coast" in result

    def test_formality_register_present(self, provider):
        profile = provider.get_profile("mysuru")
        result = provider.inject_into_prompt(profile, "BASE")
        assert "formal" in result

    def test_vocabulary_hints_appear_in_block(self, provider):
        profile = provider.get_profile("mangaluru")
        result = provider.inject_into_prompt(profile, "BASE")
        # At least one Tulu-influenced term should appear
        assert "ಆತ್" in result

    def test_different_districts_produce_different_prompts(self, provider):
        mangaluru = provider.get_profile("mangaluru")
        mysuru = provider.get_profile("mysuru")
        base = "You are an assistant."
        r1 = provider.inject_into_prompt(mangaluru, base)
        r2 = provider.inject_into_prompt(mysuru, base)
        assert r1 != r2


# ── Dialect-conditioned verification rephrasings ──────────────────────────────

class TestDialectConditionedRephrasings:
    def test_mangaluru_and_bengaluru_rephrasings_differ(self, engine):
        """
        Core Prompt-2 test: same intent, different district → different phrasing pool.
        Run enough iterations to rule out random-variant collision.
        """
        mangaluru_prompts = set()
        bengaluru_prompts = set()

        for _ in range(10):
            mangaluru_prompts.add(engine.generate_verification_prompt(
                intent="sanitation_garbage", entities={},
                language="kn", district="mangaluru",
            ))
            bengaluru_prompts.add(engine.generate_verification_prompt(
                intent="sanitation_garbage", entities={},
                language="kn", district="bengaluru_urban",
            ))

        # The two pools must not be identical
        assert mangaluru_prompts != bengaluru_prompts, (
            "Mangaluru and Bengaluru Urban produced the same phrasing pool — "
            "dialect conditioning is not working."
        )

    def test_mysuru_rephrasing_contains_kn_label(self, engine):
        text = engine.generate_verification_prompt(
            intent="water_supply_complaint", entities={},
            language="kn", district="mysuru",
        )
        assert "ನೀರು ಸರಬರಾಜು" in text

    def test_kalaburagi_rephrasing_nonempty(self, engine):
        text = engine.generate_verification_prompt(
            intent="road_damage", entities={},
            language="kn", district="kalaburagi",
        )
        assert isinstance(text, str) and len(text) > 0

    def test_hindi_rephrasing_unaffected_by_kannada_dialect(self, engine):
        # Hindi should use the default/standard pool regardless of district
        text = engine.generate_verification_prompt(
            intent="sanitation_garbage", entities={},
            language="hi", district="mangaluru",
        )
        assert "कचरा" in text

    def test_english_rephrasing_contains_intent_label(self, engine):
        text = engine.generate_verification_prompt(
            intent="electricity_outage", entities={},
            language="en", district="bengaluru_urban",
        )
        assert "electricity" in text.lower()
