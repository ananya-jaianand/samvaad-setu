"""
Dialect Context — maps Karnataka districts to rich dialect profiles used to
condition NLU prompts and verification rephrasings.
"""
import json
from pathlib import Path
from pydantic import BaseModel

_PROFILES_PATH = Path(__file__).parent.parent / "data" / "dialect_profiles.json"
_profiles_cache: dict = {}


def _load_profiles() -> dict:
    global _profiles_cache
    if not _profiles_cache:
        with open(_PROFILES_PATH, encoding="utf-8") as f:
            _profiles_cache = json.load(f)
    return _profiles_cache


class DialectProfile(BaseModel):
    district: str
    dialect_tag: str
    formality_register: str                # "formal" | "informal" | "medium"
    vocabulary_hints: dict[str, str]       # dialect_term → standard + gloss
    common_phrases: list[str]
    code_mixing_patterns: list[str]


class DialectContextProvider:
    def get_profile(self, district: str) -> DialectProfile:
        """
        Return the DialectProfile for the given district key.
        Falls back to the 'default' profile for unknown districts.
        """
        profiles = _load_profiles()
        data = profiles.get(district) or profiles.get("default")
        return DialectProfile(**data)

    def inject_into_prompt(self, profile: DialectProfile, base_prompt: str) -> str:
        """
        Prepend a dialect context block to any LLM system prompt.
        Structured so the model can use it for both understanding and generation.
        """
        vocab_lines = "\n".join(
            f"  • {term} → {gloss}"
            for term, gloss in list(profile.vocabulary_hints.items())[:20]
        )
        phrases_lines = "\n".join(f"  • {p}" for p in profile.common_phrases[:3])
        mixing_lines = "\n".join(f"  • {p}" for p in profile.code_mixing_patterns[:2])

        dialect_block = f"""===DIALECT CONTEXT===
District dialect: {profile.dialect_tag} ({profile.district.replace('_', ' ').title()})
Formality register: {profile.formality_register}

Local vocabulary (dialect → standard Kannada + gloss):
{vocab_lines if vocab_lines else "  • Standard Kannada — no special vocabulary"}

Common greeting/framing phrases citizens may use:
{phrases_lines}

Code-mixing patterns to expect:
{mixing_lines}

When generating Kannada text back to the citizen, match this {profile.formality_register} register
and naturally use the dialect vocabulary above where appropriate.
===END DIALECT CONTEXT===

"""
        return dialect_block + base_prompt
