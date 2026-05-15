"""
Samvaad-Setu AI Agent for 1092 Karnataka Helpline
Modeling Lead Implementation

LOW LATENCY OPTIMIZATIONS:
1. allow_interruptions=True - Enables user to interrupt agent at any time for faster interaction
2. JSON-first processing - Complete JSON parsing before any TTS playback to prevent partial content
3. Real-time modeling data logging - Comprehensive console output for team visibility

KEY FEATURES:
- Verification Machine for grievance confirmation
- Multi-language support (Kannada, English, Hindi, Tamil)
- Urgency-based escalation (score > 8 = immediate human handoff)
- Real-time classification logging with emojis for easy monitoring
"""

import json
import logging
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import JobContext, WorkerOptions, cli
from livekit.plugins import sarvam, anthropic

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Grievance Categories for 1092 Helpline
GRIEVANCE_TAXONOMY = [
    'Health Card/Arogya',
    'Aadhaar Services',
    'Revenue (Income/Caste)',
    'Pension (Widow/Handicapped)',
    'BBMP (Khatha Transfer)',
    'Sanitation/Waste',
    'Water Supply'
]

# System Prompt for Claude-3.5-Sonnet
SYSTEM_PROMPT = """You are a polite and efficient AI assistant for the 1092 Karnataka Government Helpline.

Your primary responsibilities:
1. Act as a courteous representative of the Karnataka Government's citizen services helpline
2. Extract the user's intent from the conversation transcript
3. **CRUCIAL**: Always rephrase the user's issue into a clear verification question to confirm understanding
4. Use {district_context} to adjust your language and vocabulary based on regional dialect preferences

GRIEVANCE CATEGORIES:
{grievance_categories}

VERIFICATION REQUIREMENT:
You MUST always create a verification question that:
- Summarizes the key issue the caller is facing
- Includes relevant location/context details mentioned
- Asks for confirmation in a polite manner
- Example: "I understand you are calling about a water leak in Indiranagar, is that correct?"
- Example: "So you need help with your Aadhaar card update at the Jayanagar office, is that right?"

DIALECT ADJUSTMENT:
Use the {district_context} variable to:
- Adjust terminology based on regional preferences
- Use locally familiar names for services and locations
- Adapt formality level based on district norms

OUTPUT FORMAT:
You must respond with STRICTLY VALID JSON containing exactly these keys:
{{
    "intent": "The primary grievance category from the taxonomy that matches the user's issue",
    "original_language": "The language/dialect the user is speaking (e.g., Kannada, English, Hindi, Tamil, etc.)",
    "sentiment": "The emotional tone of the caller (e.g., frustrated, calm, angry, distressed, neutral)",
    "urgency_score": <number between 1-10, where 1 is low priority and 10 is emergency>,
    "verification_question": "A clear, polite question rephrasing the issue to confirm your understanding"
}}

IMPORTANT:
- Output ONLY valid JSON, no additional text or explanation
- The verification_question is MANDATORY and must be present in every response
- Urgency scoring: Consider severity, impact on daily life, and time-sensitivity
- Be culturally sensitive and respectful in all interactions
"""

# Format the system prompt with grievance categories
def get_system_prompt(district_context: str = "") -> str:
    """
    Get the formatted system prompt with grievance categories and district context.

    Args:
        district_context: Optional context about the caller's district for dialect adjustment

    Returns:
        Formatted system prompt string
    """
    grievance_list = "\n".join(f"- {category}" for category in GRIEVANCE_TAXONOMY)
    return SYSTEM_PROMPT.format(
        grievance_categories=grievance_list,
        district_context=district_context or "standard Karnataka"
    )


def is_affirmation(text: str) -> bool:
    """
    Check if user's response is an affirmation.
    Supports multiple languages including Kannada, English, Hindi.
    """
    text_lower = text.lower().strip()

    # Check for negations first (high priority)
    negations = ['no', 'not', 'illa', 'ಇಲ್ಲ', 'nahi', 'नहीं', 'wrong', 'galat']
    if any(neg in text_lower for neg in negations):
        return False

    affirmative_words = [
        # English
        'yes', 'yeah', 'yep', 'correct', 'right', 'exactly', 'true', 'ok', 'okay',
        # Kannada
        'ಹೌದು', 'houdu', 'haudu', 'sari', 'ಸರಿ', 'ಸರಿ ಇದೆ', 'sari ide', 'aaythu', 'ಆಯ್ತು',
        # Hindi
        'haan', 'haa', 'ha', 'हां', 'सही', 'sahi', 'theek', 'ठीक',
        # Tamil
        'aam', 'sari', 'சரி',
    ]

    return any(word in text_lower for word in affirmative_words)


def is_denial_or_correction(text: str) -> bool:
    """
    Check if user's response is a denial or correction.
    """
    denial_words = [
        # English
        'no', 'nope', 'wrong', 'not', 'incorrect', 'actually',
        # Kannada
        'ಇಲ್ಲ', 'illa', 'ille', 'aagolla', 'ಆಗೊಲ್ಲ', 'beda', 'ಬೇಡ',
        # Hindi
        'nahi', 'nahin', 'नहीं', 'galat', 'गलत',
    ]

    text_lower = text.lower().strip()
    # Check for denials or if text is long enough to be a correction
    return any(word in text_lower for word in denial_words) or len(text.split()) > 10


async def entrypoint(ctx: JobContext):
    """
    Main entry point for the Samvaad-Setu Voice Agent with Verification Machine.

    Sets up STT, TTS, and LLM components and handles the conversation loop
    with session-state-based verification.
    """
    logger.info("Starting Samvaad-Setu Voice Agent with Verification Machine")

    # Connect to the room
    await ctx.connect()
    logger.info(f"Connected to room: {ctx.room.name}")

    # Session state for Verification Machine
    session_state = {
        'verified': False,
        'waiting_for_verification': False,
        'current_intent': None,
        'current_urgency': 0,
        'current_verification_question': None,
        'original_language': None,
        'grievance_data': None
    }

    # Initialize Sarvam STT (Speech-to-Text)
    # Using saaras:v3 model with language='unknown' for auto-detection
    stt = sarvam.STT(
        model="saaras:v3",
        language="unknown"  # Auto-detect language
    )
    logger.info("Initialized Sarvam STT with model saaras:v3")

    # Initialize Sarvam TTS (Text-to-Speech)
    # Using bulbul:v3 model with shubh (male) speaker
    # Change to 'shweta' for female voice
    tts = sarvam.TTS(
        model="bulbul:v3",
        speaker="shubh",  # Options: 'shubh' (male) or 'shweta' (female)
        target_language_code="kn-IN"  # Kannada (India)
    )
    logger.info("Initialized Sarvam TTS with model bulbul:v3, speaker: shubh")

    # Initialize Anthropic LLM (Claude)
    llm = anthropic.LLM(
        model="claude-3-5-sonnet-20241022"
    )
    logger.info("Initialized Anthropic LLM with Claude-3.5-Sonnet")

    # Create the VoiceAgent with chat context
    chat_ctx = agents.ChatContext()
    chat_ctx.add_message(
        role="system",
        content=get_system_prompt()
    )

    # OPTIMIZATION: Enable allow_interruptions=True for low latency
    assistant = agents.VoiceAssistant(
        vad=agents.silero.VAD.load(),  # Voice Activity Detection
        stt=stt,
        llm=llm,
        tts=tts,
        chat_ctx=chat_ctx,
        allow_interruptions=True  # LOW LATENCY: Allow user to interrupt at any time
    )

    logger.info("VoiceAssistant created and configured with interruptions enabled")

    # Start the assistant
    assistant.start(ctx.room)

    # Main conversation loop with Verification Machine
    @assistant.on("user_speech_committed")
    async def on_user_speech(msg: agents.llm.ChatMessage):
        """
        Handle user speech after it's been transcribed.
        Implements the Verification Machine logic.
        """
        transcript = msg.content if hasattr(msg, 'content') else str(msg)
        logger.info(f"User transcript: {transcript}")

        # If we're waiting for verification response
        if session_state['waiting_for_verification']:
            logger.info("Processing verification response...")

            # Check if user affirms
            if is_affirmation(transcript):
                logger.info("User AFFIRMED the verification")
                session_state['verified'] = True
                session_state['waiting_for_verification'] = False

                # Play ticket registered message
                confirmation_msg = (
                    f"Thank you for confirming. Your {session_state['current_intent']} "
                    f"grievance has been registered. Ticket number will be sent to you shortly. "
                    f"Dhanyavadagalu. 1092 Karnataka Helpline ge phone madidakke thanks."
                )
                await assistant.say(confirmation_msg, allow_interruptions=False)
                logger.info(f"✅ TICKET REGISTERED - Intent: {session_state['current_intent']}, "
                           f"Urgency: {session_state['current_urgency']}")

            # Check if user denies or provides correction
            elif is_denial_or_correction(transcript):
                logger.info("User DENIED or CORRECTED the verification")
                session_state['waiting_for_verification'] = False

                # Send correction back to LLM
                correction_prompt = f"The user has corrected their grievance. New information: {transcript}"
                await assistant.say(correction_prompt, allow_interruptions=True)
                logger.info("Sent correction back to LLM for re-analysis")

            else:
                # Unclear response, ask again
                logger.warning("Unclear verification response, asking again")
                clarification_msg = (
                    "I didn't quite understand. Please say 'Yes' or 'Sari' if the information "
                    "is correct, or provide the correction if something is wrong."
                )
                await assistant.say(clarification_msg, allow_interruptions=True)

    @assistant.on("agent_speech_committed")
    async def on_agent_response(msg: agents.llm.ChatMessage):
        """
        Handle agent's response after it's been generated.
        LOW LATENCY OPTIMIZATION: Parse complete JSON before playing any audio.
        This ensures we don't play partial responses while LLM is still generating.
        """
        text = msg.content if hasattr(msg, 'content') else str(msg)
        logger.info(f"Agent raw response: {text}")

        try:
            # OPTIMIZATION: Wait for complete JSON parsing before any TTS playback
            # This prevents playing partial content while LLM generates the full response
            response_data = json.loads(text)

            # Extract all fields
            intent = response_data.get("intent", "Unknown")
            urgency = response_data.get("urgency_score", 0)
            sentiment = response_data.get("sentiment", "neutral")
            language = response_data.get("original_language", "Unknown")
            verification_question = response_data.get("verification_question", "")

            # Store in session state
            session_state['current_intent'] = intent
            session_state['current_urgency'] = urgency
            session_state['original_language'] = language
            session_state['current_verification_question'] = verification_question
            session_state['grievance_data'] = response_data

            # ====================================================================
            # MODELING DATA LOG EVENT - Real-time console output for team visibility
            # ====================================================================
            logger.info("=" * 80)
            logger.info("📊 CLASSIFIED GRIEVANCE DATA - MODELING OUTPUT")
            logger.info("=" * 80)
            logger.info(f"��� FINAL JSON OUTPUT:\n{json.dumps(response_data, indent=2, ensure_ascii=False)}")
            logger.info(f"🎯 Intent Classification: {intent}")
            logger.info(f"🔥 Urgency Score: {urgency}/10")
            logger.info(f"😊 Sentiment Analysis: {sentiment}")
            logger.info(f"🗣️  Original Language: {language}")
            logger.info(f"✅ Verification Question Generated: {verification_question}")
            logger.info("=" * 80)

            # URGENT ESCALATION: If urgency_score > 8, bypass verification
            if urgency > 8:
                logger.warning(f"⚠️ URGENT ESCALATION - Urgency Score: {urgency}")
                urgent_msg = (
                    "This sounds urgent. I'm connecting you to a human supervisor immediately. "
                    "Please hold the line. "
                    "Idu urgent aagide. Nanu nimge human supervisor ge connect maadthini. "
                    "Dayavittu wait maadi."
                )
                await assistant.say(urgent_msg, allow_interruptions=False)
                logger.info("🚨 ESCALATED TO HUMAN SUPERVISOR")
                session_state['verified'] = True  # Mark as handled
                return

            # ONLY NOW play the verification question after complete JSON is parsed
            # This ensures low latency and prevents playing incomplete content
            if verification_question:
                logger.info("▶️  Playing verification question to user (after complete JSON parse)")
                await assistant.say(verification_question, allow_interruptions=True)
                session_state['waiting_for_verification'] = True
                logger.info("⏳ Waiting for user's verification response...")

        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse JSON response: {e}")
            logger.error(f"Raw text: {text}")
            # If not JSON, treat as regular conversation
            session_state['waiting_for_verification'] = False

        except Exception as e:
            logger.error(f"❌ Error processing agent response: {e}")
            session_state['waiting_for_verification'] = False

    logger.info("Voice Agent with Verification Machine is now active and listening...")

    # Greet the user
    await assistant.say(
        "Namaskara, 1092 Karnataka Helpline nalli nimge swagata. "
        "Nevu yava vishaya bagge mathadabekagide?",
        allow_interruptions=True
    )


if __name__ == "__main__":
    # Run the agent using LiveKit CLI
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint
        )
    )
