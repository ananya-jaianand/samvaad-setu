"""
NLU Service — Google Gemini for intent extraction, rephrasing, and summarization.
Prompted with district-aware dialect context and Karnataka grievance taxonomy.
"""
import json
import google.generativeai as genai
from config import settings, DISTRICT_DIALECT_MAP, INTENT_TAXONOMY, VERIFICATION_PHRASES
from models.session_model import SessionState, Turn
from services.dialect_context import DialectContextProvider
from services.intent_taxonomy import IntentTaxonomy
from services.pii_redactor import redact as pii_redact, unredact as pii_unredact

_dialect_provider = DialectContextProvider()
_taxonomy = IntentTaxonomy()

# Configure Gemini
genai.configure(api_key=settings.gemini_api_key)
model = genai.GenerativeModel('gemini-2.0-flash-exp')


def _build_system_prompt(district: str, language: str) -> str:
    taxonomy_block = _taxonomy.taxonomy_prompt_block(language)

    base_prompt = f"""You are Samvaad-Setu, a multilingual voice assistant for the Karnataka 1092 citizen helpline.
You help citizens in Kannada, Hindi, and English. The current caller is from {district.replace('_', ' ').title()} district.

GRIEVANCE INTENT TAXONOMY — you MUST return one of these intent IDs exactly as written:
{taxonomy_block}

If the citizen's issue does not match any category above, use "other_grievance".

RESPONSE FORMAT — always respond in valid JSON only, no markdown fences:
{{
  "intent": "<exact intent_id from taxonomy above>",
  "intent_confidence": <0.0–1.0>,
  "intent_entropy": <0.0–1.0>,
  "rephrasing": "<restate citizen's issue in their language, warm and clear>",
  "verification_prompt": "<ask citizen to confirm, using natural {language} phrasing>",
  "structured_summary": {{
    "problem": "<one sentence>",
    "location_mentioned": "<extracted location or null>",
    "urgency_indicated": <true|false>,
    "key_details": ["<detail1>", "<detail2>"]
  }}
}}

RULES:
- Always respond in the SAME LANGUAGE the citizen used ({language})
- Never invent details not present in the transcript
- If transcript is unclear, set intent_entropy > 0.6
- Keep rephrasing under 2 sentences — warm, not robotic
- verification_prompt must be a natural yes/no question
- Use the dialect vocabulary from the context block above when generating Kannada responses"""

    profile = _dialect_provider.get_profile(district)
    return _dialect_provider.inject_into_prompt(profile, base_prompt)


async def extract_intent_and_rephrase(
    transcript: str,
    session: SessionState,
) -> dict:
    """
    Core NLU call. Returns structured JSON with intent, rephrasing,
    verification prompt, and summary.
    """
    if not settings.gemini_api_key or settings.environment == "mock":
        return _mock_nlu(transcript, session.detected_language)

    # Redact PII before any text leaves this process boundary
    redacted_transcript, token_map = pii_redact(transcript, session.detected_language)

    system = _build_system_prompt(session.district, session.detected_language)

    # Build conversation history for multi-turn context
    conversation_history = ""
    for turn in session.citizen_turns()[-4:]:   # last 4 citizen turns for context
        conversation_history += f"Previous: {turn.raw_transcript}\n"

    # Combine system prompt with conversation
    full_prompt = f"{system}\n\nCONVERSATION HISTORY:\n{conversation_history}\n\nCURRENT TRANSCRIPT:\n{redacted_transcript}\n\nRespond with JSON only:"

    try:
        response = await model.generate_content_async(full_prompt)
        raw = response.text.strip()

        # Remove markdown code fences if present
        if raw.startswith('```'):
            raw = raw.split('```')[1]
            if raw.startswith('json'):
                raw = raw[4:]
        raw = raw.strip()

        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            import re
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                result = json.loads(match.group())
            else:
                return _mock_nlu(transcript, session.detected_language)

        # Validate intent against taxonomy; flag for human review if unknown
        intent = result.get("intent", "other_grievance")
        if not _taxonomy.validate_intent(intent):
            print(f"[NLU] Unknown intent '{intent}' — not in taxonomy, flagging for human review")
            result["intent"] = "other_grievance"
            result["intent_out_of_taxonomy"] = True
            result["original_intent"] = intent

        result["responsible_department"] = _taxonomy.get_responsible_department(result["intent"])
        result["always_escalate"] = _taxonomy.should_always_escalate(result["intent"])

        # Restore PII in any text that will be spoken back to the citizen
        if token_map:
            for field in ("rephrasing", "verification_prompt"):
                if field in result:
                    result[field] = pii_unredact(result[field], token_map)

        return result

    except Exception as e:
        print(f"Gemini API error: {e}")
        return _mock_nlu(transcript, session.detected_language)


async def generate_escalation_summary(session: SessionState) -> str:
    """
    One-line context summary for the human agent. Runs once at escalation.
    """
    if not settings.gemini_api_key or settings.environment == "mock":
        return f"Citizen called about {session.final_intent or 'unknown issue'}. {session.clarification_count} clarification attempts. Needs human assistance."

    prompt = f"""Summarize the following citizen call in ONE sentence (max 25 words) for a human agent who is picking it up mid-call.
Include: the core complaint, any urgency, and district if mentioned.

TRANSCRIPT:
{session.to_transcript_text()}

DETECTED INTENT: {session.final_intent}
DISTRICT: {session.district}

Respond with ONLY the one-line summary, no preamble."""

    try:
        response = await model.generate_content_async(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini API error: {e}")
        return f"Citizen called about {session.final_intent or 'unknown issue'}. Needs human assistance."


async def generate_ticket_draft(session: SessionState) -> dict:
    """
    Generate a structured ticket draft for the 1092 intake form.
    """
    if not settings.gemini_api_key or settings.environment == "mock":
        return {
            "category": session.final_intent or "other_grievance",
            "sub_category": "",
            "description": session.turns[-1].raw_transcript if session.turns else "",
            "location": session.district,
            "priority": "high" if session.is_escalated else "normal",
            "language": session.detected_language,
        }

    prompt = f"""Based on this citizen call transcript, generate a structured grievance ticket for the Karnataka 1092 system.

TRANSCRIPT:
{session.to_transcript_text()}

Respond ONLY in valid JSON:
{{
  "category": "<from taxonomy>",
  "sub_category": "<specific issue>",
  "description": "<clear problem statement in English, 2-3 sentences>",
  "location": "<district or locality mentioned>",
  "priority": "high|normal|low",
  "language": "{session.detected_language}",
  "suggested_department": "<which govt dept should handle this>"
}}"""

    try:
        response = await model.generate_content_async(prompt)
        raw = response.text.strip()
        
        # Remove markdown code fences if present
        if raw.startswith('```'):
            raw = raw.split('```')[1]
            if raw.startswith('json'):
                raw = raw[4:]
        raw = raw.strip()
        
        return json.loads(raw)
    except Exception as e:
        print(f"Gemini API error: {e}")
        return {"category": session.final_intent, "description": "See transcript", "priority": "normal"}


def _mock_nlu(transcript: str, language: str) -> dict:
    """Mock NLU for dev without Gemini API key. Uses taxonomy-validated intent IDs."""
    kw_map = {
        "ಕಸ": "sanitation_garbage", "garbage": "sanitation_garbage", "कचरा": "sanitation_garbage",
        "ನೀರು": "water_supply_complaint", "water": "water_supply_complaint", "पानी": "water_supply_complaint",
        "ರಸ್ತೆ": "road_damage", "road": "road_damage", "सड़क": "road_damage",
        "ವಿದ್ಯುತ್": "electricity_outage", "electricity": "electricity_outage", "बिजली": "electricity_outage",
        "ಪಿಂಚಣಿ": "pension_scheme", "pension": "pension_scheme",
        "ರೇಷನ್": "ration_card_status", "ration": "ration_card_status",
        "ತುರ್ತು": "distress_emergency", "emergency": "distress_emergency", "अत्यावश्यक": "distress_emergency",
    }
    intent = "other_grievance"
    for kw, mapped in kw_map.items():
        if kw.lower() in transcript.lower():
            intent = mapped
            break

    phrases = {
        "kn": f"ನೀವು {transcript[:40]}... ಎಂದು ಹೇಳಿದ್ದೀರಿ.",
        "hi": f"आपने {transcript[:40]}... के बारे में बताया।",
        "en": f"You mentioned: {transcript[:50]}...",
    }

    return {
        "intent": intent,
        "intent_confidence": 0.78,
        "intent_entropy": 0.22,
        "rephrasing": phrases.get(language, phrases["en"]),
        "verification_prompt": VERIFICATION_PHRASES.get(language, VERIFICATION_PHRASES["en"]),
        "structured_summary": {
            "problem": transcript[:80],
            "location_mentioned": None,
            "urgency_indicated": any(w in transcript.lower() for w in ["urgent", "emergency", "ತುರ್ತು", "अत्यावश्यक"]),
            "key_details": [transcript[:40]],
        },
        "responsible_department": _taxonomy.get_responsible_department(intent),
        "always_escalate": _taxonomy.should_always_escalate(intent),
        "intent_out_of_taxonomy": False,
    }
