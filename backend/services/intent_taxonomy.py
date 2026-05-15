"""
Karnataka Grievance Intent Taxonomy — derived from Sevasindhu / Janasevaka categories.

Provides constrained intent IDs for NLU and escalation logic.
"""
import json
from pathlib import Path
from functools import lru_cache
from typing import Optional

_TAXONOMY_PATH = Path(__file__).parent.parent / "data" / "karnataka_grievance_taxonomy.json"

# Intent that always triggers immediate escalation regardless of confidence score
ALWAYS_ESCALATE_INTENTS = {"distress_emergency", "women_safety", "food_adulteration", "hospital_complaint"}


@lru_cache(maxsize=1)
def _load_taxonomy() -> list[dict]:
    with open(_TAXONOMY_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["categories"]


class IntentTaxonomy:
    def __init__(self):
        self._categories: list[dict] = _load_taxonomy()
        self._by_id: dict[str, dict] = {c["id"]: c for c in self._categories}

    def get_categories(self, language: str = "en") -> list[dict]:
        """Return all categories with labels in the requested language."""
        label_key = {"kn": "kn_label", "hi": "hi_label"}.get(language, "en_label")
        return [
            {
                "id": c["id"],
                "label": c[label_key],
                "responsible_department": c["responsible_department"],
                "escalation_priority": c["escalation_priority"],
            }
            for c in self._categories
        ]

    def validate_intent(self, intent_id: str) -> bool:
        return intent_id in self._by_id

    def get_responsible_department(self, intent_id: str) -> str:
        category = self._by_id.get(intent_id)
        if category is None:
            return "General Administration"
        return category["responsible_department"]

    def get_escalation_priority(self, intent_id: str) -> int:
        """1 = highest priority, 5 = lowest. Unknown intents default to 3."""
        category = self._by_id.get(intent_id)
        if category is None:
            return 3
        return category["escalation_priority"]

    def should_always_escalate(self, intent_id: str) -> bool:
        return intent_id in ALWAYS_ESCALATE_INTENTS

    def get_label(self, intent_id: str, language: str = "en") -> Optional[str]:
        category = self._by_id.get(intent_id)
        if category is None:
            return None
        label_key = {"kn": "kn_label", "hi": "hi_label"}.get(language, "en_label")
        return category[label_key]

    def taxonomy_prompt_block(self, language: str = "en") -> str:
        """
        Returns a formatted block for injection into the Gemini system prompt.
        Lists all valid intent IDs with their labels so the model can produce
        constrained output.
        """
        label_key = {"kn": "kn_label", "hi": "hi_label"}.get(language, "en_label")
        lines = []
        for c in self._categories:
            lines.append(f'  "{c["id"]}" — {c[label_key]} ({c["responsible_department"]})')
        return "\n".join(lines)
