# Samvaad-Setu AI Models & Integration Guide

This document summarizes the 5 AI models built for the hackathon, their importance, and exactly how to integrate them into the existing backend architecture.

---

## Part 1: The AI Models

### 1. Semantic Ambiguity Detector ("The Wow Factor")
*   **Why it's important**: It directly solves the hackathon's core problem statement (misrouting tickets due to dialect nuance like *neeru bartilla* vs *neeru sariyaagilla*). It intercepts confusing statements and forces a clarification question instead of making a bad guess.
*   **Workflow**: `Transcript -> Zero-Shot Intent Classifier + Localized Keyword Dictionary -> Shannon Entropy Calculation -> Ambiguity Score -> Clarification Flag`.
*   **Example**: 
    *   *Input:* "ಇಂದಿರಾನಗರ ಪ್ರದೇಶದಲ್ಲಿ ನೀರು ಸರಿಯಾಗಿ ಸಿಗುತ್ತಿಲ್ಲ" (Indiranagar is not getting water properly / dirty water).
    *   *Output:* Model calculates high entropy between `water_supply` and `sanitation_garbage` -> Outputs `Requires Clarification: True`.

### 2. Text Sentiment Classifier
*   **Why it's important**: Accurately detects citizen distress across English, Kannada, and Hindi. It is much more robust than the old keyword-matching approach and is the foundation of the Escalation Engine.
*   **Workflow**: `Transcript -> mDeBERTa Multilingual Zero-Shot -> 6-class probability distribution`.
*   **Example**: 
    *   *Input:* "ನನ್ನ ಮಕ್ಕಳಿಗೆ ಕುಡಿಯಲು ನೀರಿಲ್ಲ ದಯವಿಟ್ಟು ಸಹಾಯ ಮಾಡಿ" (My children have no water, please help).
    *   *Output:* Dominant Emotion: `DISTRESS`.

### 3. openSMILE Prosodic Feature Extractor
*   **Why it's important**: Sometimes people are calm in their words but panicked in their voice. This model analyzes acoustic properties directly from the audio file, a unique feature most hackathon teams won't have.
*   **Workflow**: `.wav Audio File -> openSMILE eGeMAPSv02 -> Extract pitch/loudness/jitter -> Heuristic Mapping -> 6-class sentiment scores`.
*   **Example**: 
    *   *Input:* A citizen speaking very fast with a trembling, high-pitched voice.
    *   *Output:* Dominant Emotion: `FEAR` / `ANGER`.

### 4. Sentiment Fusion Engine
*   **Why it's important**: Creates a robust, holistic view of the citizen's emotional state by mathematically blending both what they say (text) and how they say it (audio).
*   **Workflow**: `Text Scores + Audio Scores -> 65/35 Weighted Average -> Distress Aggregate Calculation -> High Distress Escalation Flag`.
*   **Example**: Text is relatively calm (30% distress), but voice is trembling heavily (90% distress) -> Fusion mathematically averages to a high distress score, instantly triggering human agent handoff.

### 5. Feedback Store (Retraining Loop)
*   **Why it's important**: Proves to the judges that your verification loop isn't just a UI trick—it's an active data pipeline generating labeled training data to improve the system over time.
*   **Workflow**: `Final intent + verification status -> JSONL append to local dataset`.
*   **Example**: Citizen confirms "water supply complaint" -> System logs the full transcript and intent tuple for the next week's fine-tuning run.

---

## Part 2: Step-by-Step Integration Guide

You can integrate these models without breaking your teammate's code. Follow these steps:

### Step 1: Model Initialization (Warm-Up)
To prevent the AI models from loading into RAM every time a citizen speaks, initialize them *once* when the backend starts.

Open `backend/services/sentiment.py` and add this to the top of the file:
```python
import sys, os, tempfile

# Ensure the backend can see your models directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from models.sentiment.fusion import SentimentFusionModel
from models.intent.ambiguity_detector import SemanticAmbiguityDetector
from models.feedback.feedback_store import FeedbackStore

# Load models to memory on startup
print("Warming up AI Models...")
fusion_model = SentimentFusionModel()
ambiguity_detector = SemanticAmbiguityDetector()
feedback_store = FeedbackStore(storage_dir="../data/datasets")
```

### Step 2: Integrating Sentiment Fusion
In `backend/services/sentiment.py`, replace your teammate's existing `async def analyze` function with this wrapper that calls our AI model:

```python
async def analyze(transcript: str, audio_bytes: bytes, language: str) -> SentimentResult:
    # 1. Save incoming Base64 audio bytes to a temp WAV file for openSMILE
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        temp_audio_path = tmp.name
        
    # 2. Run our Fusion Model (Text + Audio)
    try:
        fusion_result = fusion_model.analyze(transcript, temp_audio_path)
    finally:
        # Clean up temp file
        if os.path.exists(temp_audio_path):
            os.unlink(temp_audio_path)
            
    # 3. Format the return object so the backend doesn't break
    prosodic_scores = fusion_result["components"]["prosodic"] or {}
    text_scores = fusion_result["components"]["text"] or {}
    dominant = fusion_result["dominant_label"]
    
    return SentimentResult(
        label=dominant,
        score=fusion_result["dominant_score"],
        prosodic_score=prosodic_scores.get(dominant, 0.0),
        text_score=text_scores.get(dominant, 0.0),
        all_scores=fusion_result["all_scores"]
    )
```

### Step 3: Integrating Ambiguity Detection
Open `backend/main.py`. Locate the `_handle_audio_turn()` function. Right after step 2 (NLU), add the Ambiguity check:

```python
    # ── 2b. Ambiguity Check (The Wow Factor) ───────────────────────────────
    print("[AMBIGUITY] Checking semantic entropy...")
    ambiguity_result = ambiguity_detector.analyze(asr_result.transcript)
    
    if ambiguity_result["requires_clarification"]:
        print("[AMBIGUITY] High ambiguity detected! Forcing clarification.")
        # Force the intent entropy to 1.0 so the Escalation engine knows the AI is confused
        nlu_result["intent_entropy"] = 1.0 
```

### Step 4: Integrating the Feedback Store
Open `backend/main.py`. Locate the `_handle_verification_turn()` function. Under `if state == "correct":`, log the data:

```python
    if state == "correct":
        # LOG TO FEEDBACK STORE!
        feedback_store.save_interaction({
            "transcript": session.citizen_turns()[-1].raw_transcript,
            "detected_language": session.detected_language,
            "district": session.district,
            "intent": session.final_intent,
            "sentiment_label": session.citizen_turns()[-1].sentiment.label,
            "verification_state": "correct"
        })
        # ... existing code continues
```

### Step 5: Frontend Integration
**Zero changes required!** 
Because we mapped our AI outputs exactly to the `SentimentResult` dataclass that your teammate defined, the Flutter frontend will automatically start displaying our real AI numbers on the Confidence Gauge and Sentiment Timeline instead of the hardcoded mock numbers.
