"""
Tests for IntentTaxonomy — validates the taxonomy service and NLU integration.
"""
import pytest
from services.intent_taxonomy import IntentTaxonomy, ALWAYS_ESCALATE_INTENTS
from services.nlu import _mock_nlu


@pytest.fixture
def taxonomy():
    return IntentTaxonomy()


class TestIntentTaxonomy:
    def test_get_categories_returns_all_items(self, taxonomy):
        cats = taxonomy.get_categories("en")
        assert len(cats) >= 30
        for c in cats:
            assert "id" in c
            assert "label" in c
            assert "responsible_department" in c
            assert "escalation_priority" in c

    def test_get_categories_kn_labels(self, taxonomy):
        cats = taxonomy.get_categories("kn")
        # Kannada labels use Unicode Kannada script
        labels = [c["label"] for c in cats]
        assert any("ಀ" <= ch <= "೿" for label in labels for ch in label)

    def test_get_categories_hi_labels(self, taxonomy):
        cats = taxonomy.get_categories("hi")
        labels = [c["label"] for c in cats]
        assert any("ऀ" <= ch <= "ॿ" for label in labels for ch in label)

    def test_validate_known_intents(self, taxonomy):
        known = [
            "water_connection_new", "water_supply_complaint",
            "ration_card_application", "ration_card_status", "ration_card_correction",
            "bbmp_property_tax", "bbmp_khata_transfer", "bbmp_birth_certificate",
            "bescom_billing", "bescom_new_connection", "electricity_outage",
            "road_damage", "road_repair", "streetlight",
            "sanitation_garbage", "encroachment", "public_health",
            "police_grievance", "women_safety",
            "government_employee_grievance", "pension_issue", "pension_scheme",
            "school_admission", "scholarship", "land_records",
            "drainage_sewage", "building_plan_approval",
            "caste_income_certificate", "disability_welfare",
            "noise_pollution", "bus_transport_complaint",
            "food_adulteration", "hospital_complaint",
            "distress_emergency", "other_grievance",
        ]
        for intent_id in known:
            assert taxonomy.validate_intent(intent_id), f"Missing intent: {intent_id}"

    def test_validate_rejects_unknown_intent(self, taxonomy):
        assert not taxonomy.validate_intent("made_up_intent")
        assert not taxonomy.validate_intent("")
        assert not taxonomy.validate_intent("WATER_SUPPLY_COMPLAINT")  # case sensitive

    def test_get_responsible_department_known(self, taxonomy):
        dept = taxonomy.get_responsible_department("distress_emergency")
        assert "Emergency" in dept

        dept = taxonomy.get_responsible_department("ration_card_status")
        assert "Food" in dept or "Civil" in dept

    def test_get_responsible_department_unknown(self, taxonomy):
        dept = taxonomy.get_responsible_department("nonexistent_intent")
        assert dept == "General Administration"

    def test_escalation_priority_range(self, taxonomy):
        for c in taxonomy.get_categories():
            p = taxonomy.get_escalation_priority(c["id"])
            assert 1 <= p <= 5

    def test_escalation_priority_emergency_is_highest(self, taxonomy):
        assert taxonomy.get_escalation_priority("distress_emergency") == 1
        assert taxonomy.get_escalation_priority("women_safety") == 1
        assert taxonomy.get_escalation_priority("food_adulteration") == 1

    def test_escalation_priority_other_grievance_is_lowest(self, taxonomy):
        assert taxonomy.get_escalation_priority("other_grievance") == 5

    def test_escalation_priority_unknown_defaults_to_3(self, taxonomy):
        assert taxonomy.get_escalation_priority("nonexistent") == 3

    def test_should_always_escalate(self, taxonomy):
        for intent_id in ALWAYS_ESCALATE_INTENTS:
            assert taxonomy.should_always_escalate(intent_id), f"Expected {intent_id} to always escalate"

    def test_should_not_always_escalate_routine(self, taxonomy):
        assert not taxonomy.should_always_escalate("bbmp_property_tax")
        assert not taxonomy.should_always_escalate("ration_card_status")
        assert not taxonomy.should_always_escalate("other_grievance")

    def test_get_label_en(self, taxonomy):
        label = taxonomy.get_label("distress_emergency", "en")
        assert label == "Distress / Emergency"

    def test_get_label_unknown(self, taxonomy):
        assert taxonomy.get_label("nonexistent", "en") is None

    def test_taxonomy_prompt_block_contains_all_ids(self, taxonomy):
        block = taxonomy.taxonomy_prompt_block("en")
        for c in taxonomy.get_categories():
            assert c["id"] in block

    def test_taxonomy_prompt_block_kn_includes_kannada(self, taxonomy):
        block = taxonomy.taxonomy_prompt_block("kn")
        assert any("ಀ" <= ch <= "೿" for ch in block)


class TestMockNLUIntegration:
    """Verify mock NLU returns taxonomy-valid intents and the new enrichment fields."""

    def test_mock_nlu_returns_valid_intent(self):
        taxonomy = IntentTaxonomy()
        result = _mock_nlu("my road has a big pothole", "en")
        assert taxonomy.validate_intent(result["intent"])

    def test_mock_nlu_emergency_keyword_maps_to_distress(self):
        result = _mock_nlu("emergency help needed now", "en")
        assert result["intent"] == "distress_emergency"
        assert result["always_escalate"] is True

    def test_mock_nlu_water_keyword(self):
        result = _mock_nlu("no water supply for 3 days", "en")
        assert result["intent"] == "water_supply_complaint"

    def test_mock_nlu_unknown_maps_to_other_grievance(self):
        taxonomy = IntentTaxonomy()
        result = _mock_nlu("some completely unrelated sentence xyz", "en")
        assert taxonomy.validate_intent(result["intent"])
        assert result["intent"] == "other_grievance"

    def test_mock_nlu_includes_responsible_department(self):
        result = _mock_nlu("road is broken", "en")
        assert "responsible_department" in result
        assert result["responsible_department"] != ""

    def test_mock_nlu_includes_always_escalate_flag(self):
        result = _mock_nlu("normal query about tax", "en")
        assert "always_escalate" in result
        assert result["always_escalate"] is False

    def test_mock_nlu_intent_out_of_taxonomy_false_for_valid(self):
        result = _mock_nlu("water problem", "en")
        assert result.get("intent_out_of_taxonomy") is False
