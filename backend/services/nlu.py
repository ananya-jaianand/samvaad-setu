"""
NLU Service — Google Gemini for intent extraction, rephrasing, and summarization.
Prompted with district-aware dialect context and Karnataka grievance taxonomy.
"""
import json
from google import genai
from config import settings, DISTRICT_DIALECT_MAP, INTENT_TAXONOMY, VERIFICATION_PHRASES
from models.session_model import SessionState, Turn
from services.dialect_context import DialectContextProvider
from services.intent_taxonomy import IntentTaxonomy
from services.pii_redactor import redact as pii_redact, unredact as pii_unredact

_dialect_provider = DialectContextProvider()
_taxonomy = IntentTaxonomy()

_MODEL = "gemini-2.5-flash"
_client: genai.Client | None = (
    genai.Client(api_key=settings.gemini_api_key)
    if settings.gemini_api_key
    else None
)


def _build_system_prompt(district: str, language: str, conversation_stage: str = "gathering_info") -> str:
    taxonomy_block = _taxonomy.taxonomy_prompt_block(language)

    if conversation_stage == "seeking_confirmation":
        stage_block = f"""CURRENT STAGE: Seeking confirmation
You have gathered enough information. Now:
- Provide a clear rephrasing that summarises the full issue with all details the citizen gave
- Set follow_up_question to "" (empty)
- Set verification_prompt to a natural yes/no question asking "Shall I register this complaint?"
  (e.g. in English: "Shall I go ahead and register this complaint for you?")"""
    else:
        stage_block = f"""CURRENT STAGE: Gathering information
You are building up a complete picture of the citizen's issue. Now:
- Briefly restate what you understood so far
- Ask ONE focused follow-up question to fill the single most important gap
  (priority order: specific location/ward → urgency/duration → any reference number → contact preference)
- Keep the question short and conversational
- Do NOT ask for personal names, Aadhaar, phone numbers, or any PII
- Set verification_prompt to "" (empty — do not ask for confirmation yet)"""

    base_prompt = f"""You are Samvaad-Setu, a multilingual voice assistant for the Karnataka 1092 citizen helpline.
You help citizens lodge grievances in Kannada, Hindi, and English.
The current caller is from {district.replace('_', ' ').title()} district.

GRIEVANCE INTENT TAXONOMY — return EXACTLY one of these intent IDs:
{taxonomy_block}

If the issue does not fit any category, use "other_grievance".

{stage_block}

RESPONSE FORMAT — valid JSON only, no markdown fences:
{{
  "intent": "<exact intent_id>",
  "intent_confidence": <0.0–1.0>,
  "intent_entropy": <0.0–1.0>,
  "rephrasing": "<restate citizen's issue in {language}, warm and clear, under 2 sentences>",
  "follow_up_question": "<ONE focused question in {language}, or empty string>",
  "verification_prompt": "<yes/no confirmation question in {language}, or empty string>",
  "structured_summary": {{
    "problem": "<one sentence>",
    "location_mentioned": "<ward, area, or locality — keep this, it's needed for routing>",
    "urgency_indicated": <true|false>,
    "key_details": ["<non-PII detail 1>", "<non-PII detail 2>"]
  }}
}}

RULES:
- Always respond in {language}
- Never invent details not present in the transcript
- If transcript is unclear, set intent_entropy > 0.6
- Never include personal names, phone numbers, or Aadhaar in rephrasing or prompts
- Area/locality/ward names are NOT PII — always include them for routing
- Use dialect vocabulary from the context block below when responding in Kannada"""

    profile = _dialect_provider.get_profile(district)
    return _dialect_provider.inject_into_prompt(profile, base_prompt)


async def generate_conversation_turn(
    transcript: str,
    session: SessionState,
) -> str:
    """
    Fast conversational response — plain text only, single Gemini call with a
    minimal prompt. Used as the primary voice response; full NLU runs in background.

    Target latency: ~200-350 ms (vs ~700 ms for full JSON NLU).
    """
    language = session.user_language or session.detected_language
    district = session.district
    stage = session.conversation_stage

    # Redact PII before sending to Gemini
    redacted, token_map = pii_redact(transcript, language)

    if not settings.gemini_api_key or settings.environment == "mock" or _client is None:
        return _mock_conversation_turn(redacted, token_map, language, stage)

    # Full conversation history so follow-ups build on everything said so far
    history_lines = []
    for t in session.turns:
        if t.speaker == "citizen":
            history_lines.append(f"Citizen: {t.raw_transcript}")
        elif t.speaker == "ai":
            history_lines.append(f"Assistant: {t.raw_transcript}")
    history = "\n".join(history_lines) or "—"

    # Collect what we know so far to avoid asking the same follow-up twice
    known_facts: list[str] = []
    if session.final_intent and session.final_intent != "other_grievance":
        known_facts.append(f"Issue type: {session.final_intent.replace('_', ' ')}")
    if session.district:
        known_facts.append(f"District: {session.district.replace('_', ' ')}")
    known_str = "; ".join(known_facts) if known_facts else "nothing confirmed yet"

    if stage == "seeking_confirmation":
        stage_directive = (
            f"Briefly summarise the citizen's issue in one sentence, then ask: "
            f"'Shall I go ahead and register this complaint?' — in {language}."
        )
    elif stage == "confirmed_ready":
        stage_directive = (
            f"Warmly confirm you have all details and tell them to tap 'End call' "
            f"when ready — in {language}."
        )
    else:
        stage_directive = (
            f"Acknowledge what you just heard briefly. "
            f"Known so far: {known_str}. "
            f"Ask ONE focused follow-up question to fill a gap "
            f"(e.g. specific ward/area if not known, how long the issue has existed, "
            f"or urgency). Do NOT repeat what is already known. — in {language}."
        )

    prompt = (
        f"You are Samvaad-Setu, a warm voice assistant for Karnataka 1092 helpline.\n"
        f"Caller is from {district.replace('_', ' ').title()}, speaking {language}.\n\n"
        f"Full conversation so far:\n{history}\n\n"
        f"Citizen just said: \"{redacted}\"\n\n"
        f"{stage_directive}\n\n"
        f"RULES: respond in {language} ONLY · max 2 sentences · no PII (names/phone/aadhaar) "
        f"· area/ward names are fine · warm, natural tone · never repeat a question already asked\n\n"
        f"Reply with ONLY the response text:"
    )

    try:
        response = await _client.aio.models.generate_content(
            model=_MODEL, contents=prompt
        )
        result = response.text.strip()
        if token_map:
            result = pii_unredact(result, token_map)
        return result
    except Exception as e:
        print(f"[NLU] generate_conversation_turn failed: {e}")
        return _mock_conversation_turn(redacted, token_map, language, stage)


def _mock_conversation_turn(
    redacted_transcript: str, token_map: dict, language: str, stage: str
) -> str:
    if stage == "seeking_confirmation":
        msgs = {
            "kn": f"ನೀವು {redacted_transcript[:35]}... ಎಂದು ದೂರು ನೀಡಿದ್ದೀರಿ. ಇದನ್ನು ದಾಖಲಿಸಲೇ?",
            "hi": f"आपने {redacted_transcript[:35]}... की शिकायत दी। क्या मैं इसे दर्ज करूं?",
            "en": f"You've reported: {redacted_transcript[:50]}... Shall I go ahead and register this complaint?",
        }
    elif stage == "confirmed_ready":
        msgs = {
            "kn": "ಧನ್ಯವಾದ! ನಿಮ್ಮ ವಿವರಗಳು ಸಿದ್ಧವಾಗಿವೆ. ಮಾತು ಮುಗಿದಾಗ 'ಕರೆ ಕೊನೆಗೊಳಿಸಿ' ಒತ್ತಿ.",
            "hi": "शुक्रिया! आपकी जानकारी तैयार है। जब तैयार हों तो 'कॉल समाप्त करें' दबाएं।",
            "en": "Thank you! I have all your details. Tap 'End call' whenever you're ready.",
        }
    else:
        msgs = {
            "kn": f"ನೀವು {redacted_transcript[:35]}... ಎಂದು ಹೇಳಿದ್ದೀರಿ. ಈ ಸಮಸ್ಯೆ ಯಾವ ಬೀದಿ ಅಥವಾ ಪ್ರದೇಶದಲ್ಲಿ ಇದೆ?",
            "hi": f"आपने {redacted_transcript[:35]}... बताया। यह समस्या किस क्षेत्र या गली में है?",
            "en": f"I understood: {redacted_transcript[:50]}... Could you tell me which area or street this is in?",
        }
    result = msgs.get(language, msgs["en"])
    if token_map:
        result = pii_unredact(result, token_map)
    return result


async def extract_intent_and_rephrase(
    transcript: str,
    session: SessionState,
) -> dict:
    """
    Core NLU call. Returns structured JSON with intent, rephrasing,
    verification prompt, and summary.
    """
    if not settings.gemini_api_key or settings.environment == "mock" or _client is None:
        return _mock_nlu(transcript, session.detected_language, session.conversation_stage)

    # Redact PII before any text leaves this process boundary
    redacted_transcript, token_map = pii_redact(transcript, session.detected_language)

    system = _build_system_prompt(session.district, session.detected_language, session.conversation_stage)

    # Build conversation history for multi-turn context
    conversation_history = ""
    for turn in session.citizen_turns()[-4:]:   # last 4 citizen turns for context
        conversation_history += f"Previous: {turn.raw_transcript}\n"

    # Combine system prompt with conversation
    full_prompt = f"{system}\n\nCONVERSATION HISTORY:\n{conversation_history}\n\nCURRENT TRANSCRIPT:\n{redacted_transcript}\n\nRespond with JSON only:"

    try:
        response = await _client.aio.models.generate_content(
            model=_MODEL, contents=full_prompt
        )
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
                return _mock_nlu(transcript, session.detected_language, session.conversation_stage)

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
            for field in ("rephrasing", "follow_up_question", "verification_prompt"):
                if field in result and result[field]:
                    result[field] = pii_unredact(result[field], token_map)

        return result

    except Exception as e:
        print(f"Gemini API error: {e}")
        return _mock_nlu(transcript, session.detected_language, session.conversation_stage)


async def generate_escalation_summary(session: SessionState) -> str:
    """
    One-line context summary for the human agent. Runs once at escalation.
    """
    if not settings.gemini_api_key or settings.environment == "mock" or _client is None:
        return f"Citizen called about {session.final_intent or 'unknown issue'}. {session.clarification_count} clarification attempts. Needs human assistance."

    prompt = f"""Summarize the following citizen call in ONE sentence (max 25 words) for a human agent who is picking it up mid-call.
Include: the core complaint, any urgency, and district if mentioned.

TRANSCRIPT:
{session.to_transcript_text()}

DETECTED INTENT: {session.final_intent}
DISTRICT: {session.district}

Respond with ONLY the one-line summary, no preamble."""

    try:
        response = await _client.aio.models.generate_content(
            model=_MODEL, contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        print(f"Gemini API error: {e}")
        return f"Citizen called about {session.final_intent or 'unknown issue'}. Needs human assistance."


async def generate_ticket_draft(session: SessionState) -> dict:
    """
    Generate a structured ticket draft for the 1092 intake form.
    """
    if not settings.gemini_api_key or settings.environment == "mock" or _client is None:
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
        response = await _client.aio.models.generate_content(
            model=_MODEL, contents=prompt
        )
        raw = response.text.strip()

        if raw.startswith('```'):
            raw = raw.split('```')[1]
            if raw.startswith('json'):
                raw = raw[4:]
        raw = raw.strip()

        return json.loads(raw)
    except Exception as e:
        print(f"Gemini API error: {e}")
        return {"category": session.final_intent, "description": "See transcript", "priority": "normal"}


def _mock_nlu(transcript: str, language: str, conversation_stage: str = "gathering_info") -> dict:
    """Mock NLU for dev without Gemini API key. Uses taxonomy-validated intent IDs."""
    # Apply PII redaction in mock mode — mirrors the production path and makes
    # the redaction pipeline visible in demo/dev runs
    redacted_transcript, token_map = pii_redact(transcript, language)
    pii_tokens_redacted = list(token_map.keys()) if token_map else []

    kw_map = {
        "ಕಸ": "sanitation_garbage", "garbage": "sanitation_garbage", "कचरा": "sanitation_garbage",
        "ನೀರು": "water_supply_complaint", "water": "water_supply_complaint", "पानी": "water_supply_complaint",
        "ರಸ್ತೆ": "road_damage", "road": "road_damage", "सड़क": "road_damage",
        "ವಿದ್ಯುತ್": "electricity_outage", "electricity": "electricity_outage", "बिजली": "electricity_outage",
        "hescom": "bescom_billing", "bescom": "bescom_billing", "ಬಿಲ್": "bescom_billing",
        "bill": "bescom_billing", "बिल": "bescom_billing",
        "ಪಿಂಚಣಿ": "pension_scheme", "pension": "pension_scheme", "पेंशन": "pension_scheme",
        "ಸಂಧ್ಯಾ ಸುರಕ್ಷಾ": "pension_scheme", "sandhya suraksha": "pension_scheme",
        "ರೇಷನ್": "ration_card_status", "ration": "ration_card_status",
        "ತುರ್ತು": "distress_emergency", "emergency": "distress_emergency", "अत्यावश्यक": "distress_emergency",
    }
    intent = "other_grievance"
    for kw, mapped in kw_map.items():
        if kw.lower() in redacted_transcript.lower():
            intent = mapped
            break

    phrases = {
        "kn": f"ನೀವು {redacted_transcript[:40]}... ಎಂದು ಹೇಳಿದ್ದೀರಿ.",
        "hi": f"आपने {redacted_transcript[:40]}... के बारे में बताया।",
        "en": f"You mentioned: {redacted_transcript[:50]}...",
    }

    # Stage-conditional follow-up vs confirmation
    if conversation_stage == "seeking_confirmation":
        follow_up_q = ""
        verify_prompt = VERIFICATION_PHRASES.get(language, VERIFICATION_PHRASES["en"])
    else:
        follow_up_qs = {
            "kn": "ಈ ಸಮಸ್ಯೆ ಯಾವ ಬೀದಿ ಅಥವಾ ಪ್ರದೇಶದಲ್ಲಿ ಇದೆ?",
            "hi": "यह समस्या किस क्षेत्र या गली में है?",
            "en": "Could you tell me the specific area or street where this problem is?",
        }
        follow_up_q = follow_up_qs.get(language, follow_up_qs["en"])
        verify_prompt = ""

    result = {
        "intent": intent,
        "intent_confidence": 0.78,
        "intent_entropy": 0.22,
        "rephrasing": phrases.get(language, phrases["en"]),
        "follow_up_question": follow_up_q,
        "verification_prompt": verify_prompt,
        "structured_summary": {
            "problem": redacted_transcript[:80],
            "location_mentioned": None,
            "urgency_indicated": any(w in redacted_transcript.lower() for w in ["urgent", "emergency", "ತುರ್ತು", "अत्यावश्यक"]),
            "key_details": [redacted_transcript[:40]],
            "pii_tokens_redacted": pii_tokens_redacted,
        },
        "responsible_department": _taxonomy.get_responsible_department(intent),
        "always_escalate": _taxonomy.should_always_escalate(intent),
        "intent_out_of_taxonomy": False,
    }

    # Restore PII in any fields spoken back to the citizen
    if token_map:
        for field in ("rephrasing", "follow_up_question", "verification_prompt"):
            if result.get(field):
                result[field] = pii_unredact(result[field], token_map)

    return result
