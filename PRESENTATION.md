# Samvaad-Setu — Complete Presentation Guide

> **"Conversation Bridge"** — Real-time multilingual voice assistant for Karnataka's 1092 citizen helpline.
> ASR → Dialect-Aware NLU → Multi-Modal Sentiment → Verification Loop → Confidence-Aware Escalation → TTS

---

## 1. The Problem

Karnataka's 1092 helpline receives thousands of calls daily from citizens reporting grievances — incorrect electricity bills, water supply failures, ration card issues, road damage, workplace harassment. The callers speak in:
- Multiple languages (Kannada, Hindi, English, code-mixed)
- Multiple dialects (Mangaluru coastal Kannada vs. Hyderabad-Karnataka Kannada vs. Bengaluru urban code-mix)
- Varying emotional states (calm to acute distress)

Current systems: IVR menus or human-only routing. Both fail at understanding context, detecting urgency, and routing accurately. A caller in distress navigates the same tree as someone asking for office hours.

---

## 2. What Samvaad-Setu Does

A citizen dials → the system:
1. Listens (ASR via Sarvam AI — best-in-class Kannada support)
2. Extracts intent, dialect, and sentiment simultaneously
3. **Restates the issue back** and waits for explicit confirmation
4. If the citizen says "Partly" or "No", it clarifies — up to 2 times
5. Scores composite confidence every turn
6. Escalates automatically if distress is high, confidence is too low, or clarification keeps failing
7. Creates a ticket and sends a reference number via SMS
8. If escalated — an agent gets the full enriched context before saying a word

---

## 3. What Makes It Stand Out

### 3.1 Verification Loop as First-Class Architecture
The single constraint that drives everything: **correct understanding before action**. After every AI turn, the citizen sees/hears a restatement of their issue and responds Yes / Partly / No. The system never commits to an intent or creates a ticket without an explicit "Yes." This is not a UI feature — it's a stateful engine (`VerificationEngine`) with three branches and an escalation path baked into the state machine.

### 3.2 Dialect-Aware NLU (Not Just Multilingual)
30 Karnataka districts are mapped to 9 dialect profiles with:
- 20–40 high-frequency dialect-specific vocabulary terms with standard Kannada equivalents
- Formality register (formal/informal)
- Common greeting and closing phrases
- Code-mixing patterns

The NLU prompt is conditioned on the caller's district before it reaches Gemini. Verification rephrasings are also dialect-conditioned — a Mangaluru caller hears `"Yenu helti..."` while a Bengaluru caller hears a different phrasing variant.

### 3.3 Multi-Modal Sentiment — Voice + Text
Sentiment is not text-only. Audio is processed through librosa to extract:
- Pitch mean and variance
- Energy mean
- Speaking rate
- Voice quality

A `prosodic_distress_score` is computed: high pitch variance + high energy + fast rate = high distress. This is fused with Gemini's text-based sentiment at 40% prosodic / 60% text weighting. A caller who speaks calmly about a dangerous situation still gets detected — the voice gives it away.

### 3.4 Composite Confidence Scoring with Four Signals

```
composite = (asr_confidence × 0.35)
          + ((1 - intent_entropy) × 0.35)
          + ((1 - sentiment_intensity) × 0.20)
          - (clarification_count × 0.15)
```

- **< 0.60** → ask for clarification
- **< 0.40** → escalate (low_confidence)
- **distress/fear/anger intensity > 0.70** → escalate immediately (high_distress)
- **clarification_count ≥ 2** → escalate (repeated_clarification)

This score appears live on the agent dashboard as a gauge and updates every turn.

### 3.5 PII Redaction Before Any LLM Call
Citizen data never reaches Gemini in raw form. Patterns redacted before the LLM call:
- Indian phone numbers (10-digit, +91 optional) → `PHONE_1`
- Aadhaar sequences (12-digit groups) → `AADHAAR_1`
- Honorific-prefixed names (`Mr./Smt./ಶ್ರೀ`) → `CITIZEN_NAME_1`
- Language-specific self-introduction patterns (e.g. "ನನ್ನ ಹೆಸರು...") → `CITIZEN_NAME_2`
- Door numbers + street keyword patterns → `ADDRESS_1`

A token map is kept in-session. The agent dashboard sees redacted text; Gemini sees redacted text. The citizen's own transcript display on their screen is the only place original text is shown.

Demo scenario `hi_water` explicitly shows this: caller says `"मेरा आधार 7845 1234 5678 है"` → displayed to agent as `"AADHAAR_1 के रूप में दर्ज"`.

### 3.6 Real-Time Human-Agent Loop
When a call escalates, the agent doesn't start blind:
- Full conversation transcript in the caller's language with multi-language toggle (KN / HI / EN)
- Rolling sentiment timeline chart
- Confidence score history
- Structured intent + responsible department from taxonomy
- One-line AI-generated escalation summary
- Agents can type a reply → backend synthesizes it via TTS → citizen hears it with a typewriter animation

### 3.7 Feedback Loop for Continuous Improvement
Every confirmed interaction writes to `verified_interactions` (Postgres). Agent corrections (intent edits) are tracked separately. The `/training-data/export?format=jsonl` endpoint streams the entire corpus for retraining. This closes the loop from live calls back to model improvement.

### 3.8 Karnataka-Specific Grievance Taxonomy
40 intent categories derived from Sevasindhu/Janasevaka public structures, each with Kannada/Hindi/English labels, responsible department, and escalation priority. NLU is constrained to these IDs — no free-form intent strings. If Gemini returns an unknown intent, the session is flagged for human review with `reason="intent_out_of_taxonomy"`.

### 3.9 Scripted Demo Scenarios with Pre-Cached TTS
5 realistic conversation flows (BESCOM billing, ration card correction, water supply, workplace harassment/auto-escalation, BBMP road) are scripted with keyword matching. When a demo transcript matches, the backend skips NLU/sentiment inference entirely and serves pre-synthesized audio from a disk cache (`ss_tts_cache.json`). This gives zero-latency, deterministic demos regardless of API availability.

### 3.10 Latency Budget Enforced
Total target: **< 1.5s** per turn. The pipeline front-loads the conversational response (fast Gemini call) → synthesizes TTS → sends audio to citizen. Full NLU, sentiment, and escalation evaluation run **in a background async task** while the citizen is already listening. The agent dashboard receives the enriched data shortly after.

---

## 4. Screens & Features

### Screen 1 — Citizen View (`/`)

The primary citizen-facing interface. Built for accessibility — large touch targets, localized text everywhere, no complex navigation.

**Header bar**
- Brand mark: `Samvaad-Setu / Karnataka 1092`
- 3-way language toggle: `ಕನ್ನಡ KAN / हिन्दी HIN / English ENG` — animated with active state in teal
- Help (?) button → modal explaining the verification loop in the citizen's language

**Mic visualizer**
- 320×320 animated canvas: 3 concentric rings + 7 vertical animated bars
- Visual state machine driven by `PipelineState`:
  - **Idle/Ready** — static rings, muted bars, saffron dot
  - **Listening** — saffron glow, saffron bars bounce, rings pulse
  - **Processing** — teal subtle animate (AI thinking)
  - **Speaking** — teal glow + teal bars (AI talking, rings dim to signal "not your turn")
  - **Escalated** — sage/green color scheme throughout
  - **Error** — red dot, error banner with retry

**Transcript area** (large 26px text)
- Listening state: citizen's live transcript in their script (Noto Sans Kannada / Devanagari / Inter)
- Speaking/ready state: AI response in teal; agent replies in saffron with typewriter animation (22ms/char)
- Agent label ("Agent") shown above agent turns
- Localized placeholder text when idle

**Verification panel** (appears after every AI turn)
- White card with teal box-shadow
- Header chip: `ಪರಿಶೀಲನೆ / सत्यापन / Verification`
- AI restatement of citizen's issue (dialect-conditioned, 22px)
- Three color-coded response buttons:
  - `ಹೌದು / Yes` — green tint (`#F1F8F4`)
  - `ಕೊಂಚಕ್ಕೆ / Partly` — amber tint (`#FFF7E8`)
  - `ಇಲ್ಲ / No` — red tint (`#FFF4F2`)
- Each button shows primary label + subtitle (e.g. "Correct" / "ಸರಿಯಾಗಿದೆ")

**Escalation callout**
- Green left-border card (sage accent)
- Heart icon in green circle
- Localized escalation message ("Please don't hang up — an agent will be with you shortly")
- Shows district + escalation reason in monospace

**Ticket card**
- Shown after confirmed or escalated
- Ticket ID, intent label, department, status badge

**End Call button**
- Visible while session is active (not escalated)
- Red dot indicator + "ಕರೆ ಕೊನೆಗೊಳಿಸಿ / End call"
- Triggers: hold message → ticket creation → feedback overlay

**Feedback overlay** (after End Call)
- 5-star rating with hover state
- Submission triggers a farewell TTS message in the caller's language
- Rating is logged to audit trail

**Post-call transcript view**
- Full conversation summary with speaker avatars: C (citizen, saffron) / AI (teal) / A (agent, amber)
- "Start new call" button

**Help overlay**
- 3-step explanation of why the system verifies understanding
- Fully localized in all 3 languages
- Numbered steps with teal circle indicators

---

### Screen 2 — Agent Dashboard (`/agent`)

The ops-facing screen. Split layout: left queue, right conversation detail.

**Left panel — Live queue**
- Cards for all active + escalated sessions, sorted by distress intensity DESC
- Each card shows: district badge, language tag, sentiment label + colored dot, escalation reason, time elapsed, one-line AI summary
- Escalated sessions shown in red/sage accent
- Active (non-escalated) live sessions shown in teal
- Auto-refreshes every 15s via HTTP + real-time via WebSocket
- Clicking a card loads full context into the right panel

**Right panel — Session detail**
- Session metadata: session ID (monospace), district, dialect tag, language, verification state, clarification count, composite confidence
- Language toggle (EN / HI / KN) to switch transcript display language
- **Conversation pane**: turn-by-turn transcript with speaker labels, timestamps, and sentiment tags
- **Confidence gauge**: live composite score (circular or bar) updating each turn
- **Sentiment timeline chart**: rolling visualization of sentiment label + intensity across turns
- **Structured intent panel**: intent ID, English/Kannada labels, responsible department, escalation priority from taxonomy
- **Agent reply box**: text field + send button → triggers HTTP POST to `/sessions/{id}/agent-reply` → Sarvam TTS → citizen hears it
- **Mark Reviewed** toggle → enables "Resolve" button
- **Resolve** → removes from queue, creates/updates ticket, logs to audit trail, increments analytics counter
- **Resolved by Human** → same but increments the `resolved_by_human` analytics metric

**Toast notifications**
- Slide-in from top-right for new escalations and resolve confirmations
- Tapping a toast auto-selects that session in the queue

**Real-time WebSocket feed** (`/ws/agent/{agent_id}`)
- On connect: receives full queue snapshot
- Receives `new_escalation`, `queue_update`, `session_live_update`, `session_ended` events
- Live confidence + sentiment updates push to the active session detail without a reload

**Demo queue pre-seeded at startup**
Six demo sessions are seeded on backend startup and appear in the queue immediately:
1. Mangaluru — water supply crisis (distress, Tulu Coast dialect)
2. Bengaluru — workplace harassment / women's safety (fear, urban code-mix)
3. Kalaburagi — pension stopped, senior citizen (repeated clarification, Hindi)
4. Mysuru — ration card address transfer (low ASR confidence)
5. Belagavi — garbage not collected (medium urgency, North Karnataka)
6. PII redaction demo session

---

### Screen 3 — Analytics Dashboard (`/analytics`)

Regional overview, auto-refreshes every 10 seconds.

**Stat cards row (5 cards)**
- Total Calls today
- Escalated % (count)
- Resolved % (with "N by human agent" sub-label, live-updating when agents click Resolve)
- Avg Confidence (pipeline score)
- Avg Distress (sentiment intensity)

**Hotspot alerts strip**
- Districts with escalation rate > 30% shown as red alert chips
- Pulls from per-district data

**Karnataka map** (flutter_map + OpenStreetMap tiles)
- Each district rendered as a bubble marker
- Bubble color: green (calm) → amber (concerned) → red (high distress), threshold-based
- Bubble size scales with call volume
- Tap → tooltip showing district name, calls, escalated count, primary intent

**District bar chart**
- Horizontal bars, calls total + escalated overlay
- Sorted by call volume

**Intent distribution — pie chart** (fl_chart)
- 8 categories: Ration Card, Water Supply, Police/Safety, Road Repair, Pension, Sanitation, BESCOM Billing, Other

**Escalation reasons — bar chart**
- High Distress / Repeated Clarification / Low Confidence breakdown

**Language distribution — donut chart**
- Kannada 68% / Hindi 22% / English 10%

**Hourly trend — line chart**
- Calls vs. escalated per hour, 8am–9pm

**Seasonal trends** (BBMP 2020–2025 public data reference)
- Pre-built chart showing monsoon/festival seasonality

**Ticket log section**
- Recent tickets with status, district, intent, created-at
- Filters by status and district

---

### Screen 4 — Call Detail Screen

Deep-dive view for a single session, accessible from the agent dashboard.

- Full audit log: every state transition, actor (system/citizen/agent), timestamp, payload
- Turn-by-turn view with ASR confidence per utterance
- Multi-language transcript toggle
- Confidence history chart (composite score over all turns)
- Sentiment timeline with prosodic vs. text component breakdown

---

## 5. Technical Deep Dive

### 5.1 Architecture

```
Flutter Web (app_frontend/)
  ├─ Citizen View        → WebSocket /ws/{session_id}
  ├─ Agent Dashboard     → WebSocket /ws/agent/{agent_id} + HTTP REST
  └─ Analytics Dashboard → HTTP REST /analytics/overview

FastAPI (backend/)
  ├─ WebSocket voice pipeline
  ├─ REST API (sessions, agent queue, analytics, audit, tickets)
  ├─ Services layer
  └─ Postgres + Redis

External APIs
  ├─ Sarvam AI   → ASR (transcribe) + TTS (synthesize)
  └─ Google Gemini → NLU (intent extraction, conversation turns, escalation summary)
```

### 5.2 Per-Turn Pipeline

```
Audio (base64 WAV)
    │
    ▼
1. ASR — Sarvam AI transcribe() → transcript + per-token confidence
    │
    ▼
2. FAST PATH CHECK — keyword match against 5 scripted scenarios
   → If hit: serve pre-baked turn + cached TTS audio, skip steps 3–7
    │
    ▼
3. Fast conversational response — Gemini nlu.generate_conversation_turn()
   (plain natural reply, ~200ms)
    │
    ▼
4. TTS synthesis — Sarvam AI synthesize(ai_text)
    │
    ▼
5. Send audio to citizen immediately via WebSocket (turn_update message)
    │
    ▼
6. Verification prompt — VerificationEngine.generate_verification_prompt()
   → TTS synthesized → sent as verification_prompt message
    │
    ▼
7. BACKGROUND TASK (async, non-blocking — citizen already listening):
   ├─ Full NLU — Gemini extract_intent_and_rephrase() with dialect context + PII redaction
   ├─ Sentiment — librosa prosodic features + Gemini text sentiment → fused
   ├─ Escalation evaluation — EscalationEngine.evaluate()
   ├─ ConfidenceScore build — 4-component composite
   ├─ nlu_update → sent to citizen WebSocket (updates agent dashboard gauges)
   ├─ broadcast_to_agents() → all connected agent dashboards get live update
   └─ If escalate: _do_escalation() → TTS escalation message → agent queue → citizen notified
```

### 5.3 Verification State Machine

```
                    citizen says "correct"
         ┌──────────────────────────────────────────────► confirmed
         │                                                    │
pending ─┤  citizen says "partial" / "incorrect"              │
         │        ┌──────────────────────────────► clarify    │
         │        │   clarification_count < 2                 │
         │        │                                           │
         │        └──────────────────────────────► escalate   │
         │             clarification_count ≥ 2                │
         │                                                    │
         └──────────────────────────────────────────────────► ticket created
```

Each branch is handled in `_handle_verification_response()` via `VerificationEngine.process_verification_response()`.

### 5.4 Confidence Score Calculation

```python
composite = (
    asr_confidence           * 0.35   # can we hear them?
    + (1.0 - intent_entropy) * 0.35   # do we understand?
    + (1.0 - sentiment_intensity) * 0.20  # are they calm?
    - clarification_count    * 0.15   # penalty per failed attempt
).clamp(0.0, 1.0)
```

Thresholds evaluated in priority order:
1. `sentiment_label in {distress, fear, anger} AND intensity > 0.70` → escalate: `high_distress`
2. `clarification_count >= 2` → escalate: `repeated_clarification`
3. `composite < 0.40` → escalate: `low_confidence`
4. `composite < 0.60` → clarify (ask again)
5. Otherwise → proceed

### 5.5 Dialect Context Injection

```python
DialectContextProvider.get_profile(district: str) → DialectProfile
  .dialect_tag         # e.g. "tulu_coast", "urban_bengaluru", "hyderabad_karnataka"
  .vocabulary_hints    # dict of dialect → standard Kannada equivalents
  .formality_register  # "formal" | "informal"
  .common_phrases      # list of greeting/closing phrases
  .code_mixing_patterns

inject_into_prompt(profile, base_prompt) → str
  # Prepends district vocabulary and register context to every Gemini system prompt
```

9 districts covered at minimum: Bengaluru Urban, Bengaluru Rural, Mysuru, Mangaluru (Dakshina Kannada), Udupi, Hubballi-Dharwad, Belagavi, Kalaburagi, Vijayapura.

### 5.6 PII Redaction Pipeline

Patterns applied in this order (order matters — Aadhaar before phone to prevent 12-digit overlap):
1. Aadhaar regex: `\d{4}[\s\-]?\d{4}[\s\-]?\d{4}` → `AADHAAR_N`
2. Phone regex: `(?:\+91|91|0)?[6-9]\d{9}` → `PHONE_N`
3. Address regex: door/house/flat prefixes + street keywords → `ADDRESS_N`
4. Honorific-prefixed names: `Mr./Smt./ಶ್ರೀ/श्री + name words` → `CITIZEN_NAME_N`
5. Language-specific self-introduction: `"ನನ್ನ ಹೆಸರು X" / "मेरा नाम X" / "my name is X"` → `CITIZEN_NAME_N`

Token map stored in session. `unredact(text, token_map)` restores original for display. Controlled by `PII_REDACTION_ENABLED` env var.

### 5.7 Multi-Modal Sentiment Fusion

```python
prosodic_features = extract_prosodic_features(audio_bytes)
  # librosa: pitch_mean, pitch_variance, energy_mean, speaking_rate, voice_quality

prosodic_distress_score = prosodic_distress_score(features)
  # high pitch_variance + high energy + fast rate → high distress

text_sentiment = gemini_classify(transcript)
  # label: calm / neutral / concerned / distress / fear / anger
  # intensity: 0.0–1.0

fused = {
    "label":               weighted vote text/prosodic,
    "intensity":           max(text_intensity, prosodic_distress) fused at 0.6/0.4,
    "text_component":      text_sentiment.intensity,
    "prosodic_component":  prosodic_distress_score,
}
```

Gated behind `ENABLE_PROSODY` flag; falls back to text-only if librosa too heavy.

### 5.8 Karnataka Grievance Taxonomy

40 intent categories with structured metadata:

```json
{
  "id": "water_supply_complaint",
  "kn_label": "ನೀರು ಸರಬರಾಜು ದೂರು",
  "hi_label": "जल आपूर्ति शिकायत",
  "en_label": "Water Supply Complaint",
  "responsible_department": "BWSSB / Zilla Panchayat Water Supply",
  "escalation_priority": 2
}
```

The NLU prompt injects the full taxonomy as a constrained-output schema. Gemini must return one of the `id` values — no free-form text. Unknown intents flag for human review.

Sample categories: `water_connection_new`, `water_supply_complaint`, `ration_card_application`, `ration_card_status`, `ration_card_correction`, `bbmp_property_tax`, `bbmp_khata_transfer`, `bbmp_birth_certificate`, `bescom_billing`, `bescom_new_connection`, `bescom_outage`, `road_repair`, `streetlight`, `garbage_sanitation`, `police_grievance`, `women_safety`, `pension_issue`, `school_admission`, `scholarship`, `distress_emergency` (always escalates).

### 5.9 Session State (Redis, ephemeral)

```python
SessionState:
  session_id, language, district, dialect_tag
  user_language          # explicitly chosen by citizen, preserved across turns
  detected_language      # from ASR
  verification_state     # pending | confirmed | partial | rejected | escalated
  clarification_count    # increments on partial/incorrect
  composite_confidence   # latest composite score
  final_intent           # committed intent ID
  is_escalated, is_resolved
  escalation_reason, escalation_summary
  conversation_stage     # idle | gathering_info | confirmed_ready | ended
  turns: list[Turn]      # full conversation history
  sentiment_timeline     # last 20 turns of sentiment data
  confidence_history     # last 20 turns of composite scores
```

### 5.10 Persistence (Postgres)

**`audit_log`** — immutable event log
- Every state transition: session_created, verification_confirmed, verification_partial, escalation_triggered, agent_correction_applied, call_ended, feedback_submitted
- Fields: id, session_id, timestamp, event_type, actor (system/citizen/agent), payload_json

**`verified_interactions`** — feedback loop corpus
- Written when verification_state becomes "confirmed"
- Fields: session_id, audio_hash, asr_text, intent, dialect, district, verification_state, agent_corrections_json, final_intent, created_at
- Exported as JSONL via `/training-data/export` for model retraining

**`tickets`** — citizen-facing ticket records
- ticket_id, session_id, intent, department, status, district, created_at

### 5.11 WebSocket Protocol

**Citizen client → Server:**
```json
{ "type": "audio", "data": "<base64 WAV>", "language": "kn", "district": "mangaluru" }
{ "type": "verification_response", "state": "correct|partial|incorrect", "correction_text": "..." }
{ "type": "end_call" }
{ "type": "feedback", "rating": 4 }
{ "type": "ping" }
```

**Server → Citizen client:**
```json
{ "type": "turn_update", "citizen_turn": {...}, "ai_turn": {...}, "session": {...} }
{ "type": "verification_prompt", "text": "...", "tts_audio_b64": "...", "language": "kn" }
{ "type": "nlu_update", "nlu": {...}, "confidence_score": {...}, "sentiment_timeline": [...] }
{ "type": "escalation", "packet": {...}, "tts_audio_b64": "...", "escalation_message": "..." }
{ "type": "verification_result", "state": "confirmed", "ai_response": "...", "tts_audio_b64": "..." }
{ "type": "hold_on", "ai_response": "...", "tts_audio_b64": "..." }
{ "type": "ticket_created", "ticket": {...} }
{ "type": "feedback_request", "text": "...", "tts_audio_b64": "..." }
{ "type": "agent_audio", "text": "...", "tts_audio_b64": "..." }
{ "type": "call_ended", "ai_response": "...", "rating": 4 }
{ "type": "pong" }
```

**Agent client → Server:**
```json
{ "type": "agent_reply", "session_id": "...", "text": "..." }
{ "type": "ping" }
```

**Server → Agent client:**
```json
{ "type": "queue_snapshot", "total": N, "items": [...], "connected_agents": N }
{ "type": "new_escalation", "packet": {...} }
{ "type": "session_live_update", "session_id": "...", "confidence_score": {...}, ... }
{ "type": "session_update", "session": {...} }
{ "type": "session_ended", "session_id": "..." }
{ "type": "pong" }
```

---

## 6. REST API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Backend + Redis + Postgres status |
| GET | `/health/latency` | Rolling p50/p95 per pipeline stage |
| POST | `/sessions` | Create session (idempotent via `Idempotency-Key` header) |
| GET | `/sessions/{id}` | Fetch session state |
| GET | `/sessions/{id}/full-context` | Agent dashboard — full transcript, sentiment, confidence, audit |
| GET | `/sessions/{id}/escalation-packet` | Escalation handoff packet |
| GET | `/sessions/{id}/ticket` | Ticket for a session |
| POST | `/sessions/{id}/agent-correction` | Agent edits a field (feeds feedback loop) |
| POST | `/sessions/{id}/agent-reply` | Agent sends a text reply to citizen (HTTP path) |
| POST | `/sessions/{id}/resolve` | Agent marks session resolved |
| GET | `/agent/queue` | Escalated sessions sorted by priority (sentiment DESC, created_at ASC) |
| GET | `/audit/{session_id}` | Full audit trail |
| GET | `/tickets` | List recent tickets with filters |
| GET | `/training-data/export` | Stream verified interactions as JSONL |
| GET | `/analytics/overview` | Regional analytics for the dashboard |
| WS | `/ws/{session_id}` | Citizen voice pipeline |
| WS | `/ws/agent/{agent_id}` | Agent real-time feed |

---

## 7. Demo Scenarios (5 scripted flows)

### S1 — `kn_bescom` — BESCOM Billing Dispute (Kannada)
- 5 turns: complaint → service connection number → usage discrepancy (PII demo: phone number redacted) → timeline → thank you
- Intent: `bescom_billing`
- Sentiment: neutral → concerned → neutral → calm
- Confidence: 0.85 → 0.79 → 0.91 → 0.94
- Demonstrates: PII redaction (`PHONE_1`)

### S2 — `kn_ration` — Ration Card Name Correction (Kannada)
- 5 turns: correction request → card number → father's name error → registration → office location
- Intent: `ration_card_correction`
- Demonstrates: multi-turn information gathering, ticket creation

### S3 — `hi_water` — Water Supply Complaint (Hindi)
- 5 turns: no water → ward + Aadhaar (PII demo) → area-level → timeline → thank you
- Intent: `water_supply_complaint`
- Demonstrates: Aadhaar redaction (`AADHAAR_1`), Hindi NLU

### S4 — `hi_safety` — Workplace Harassment / Auto-Escalation (Hindi)
- 5 turns: vague complaint → manager harassment → confirms unsafe → distress peak → escalation fires
- Escalation trigger at turn 4: sentiment_label=`distress`, intensity=`0.85` → `high_distress`
- Demonstrates: automatic escalation from vocal distress, escalation message in Hindi, ticket created, agent queue updated live

### S5 — `en_road` — BBMP Road Pothole (English)
- 5 turns: pothole → location → severity (2 people fallen) → timeline → thank you
- Intent: `road_repair`
- Demonstrates: English pipeline, priority escalation of severity

---

## 8. Failure Modes & Graceful Degradation

| Failure | Behavior |
|---------|----------|
| Sarvam ASR down | Falls back to Whisper (local); ASR confidence floor reduced |
| Gemini rate-limited | Falls back to rule-based taxonomy classifier; escalation threshold lowered |
| Sarvam TTS down | Falls back to Coqui/pyttsx3; degraded-mode banner shown |
| Redis disconnect | Session continues in-memory for active connection; new sessions blocked |
| Postgres disconnect | Audit + feedback writes queued in Redis; replayed on reconnect |
| WebSocket disconnect | Session preserved in Redis for 5 min; auto-resume on reconnect |
| Demo TTS cache miss | Falls back to live Sarvam synthesis; result cached for next run |

---

## 9. Latency Budget

Total target: **< 1.5s** per turn for live call feel.

| Stage | Budget |
|-------|--------|
| ASR (streaming) | 300ms |
| Prosodic features (librosa) | 50ms |
| Fast conversational response (Gemini) | 500ms |
| TTS (Sarvam, streaming) | 400ms |
| WebSocket overhead | 100ms |
| **Total (citizen hears response)** | **~1.35s** |
| Background NLU + full intent (non-blocking) | ~800ms (citizen already listening) |

Latency is logged per-stage via `LatencyMiddleware`. Rolling p50/p95 exposed at `/health/latency`.

---

## 10. Technology Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Frontend | Flutter Web | Single codebase for all 3 screens; deploys to mobile later without rewrite |
| Backend | FastAPI | Async-native, WebSocket-first, fast iteration |
| Session state | Redis | Sub-ms reads; sticky-session-friendly for multi-instance scale |
| Persistence | Postgres + SQLAlchemy + Alembic | Durable audit trail + SQL-queryable for compliance |
| ASR + TTS | Sarvam AI | Best-in-class Kannada dialect coverage, low latency |
| NLU | Google Gemini | Strong multilingual reasoning; cheap; grounded when given dialect context |
| Prosodic features | librosa | Lightweight; no GPU needed |
| Charts | fl_chart | Flutter-native charting |
| Maps | flutter_map + OpenStreetMap | No Google Maps API key required |

---

## 11. What Is Not In Scope (Prototype)

- Production telephony integration (PSTN / SIP)
- Coverage of all 31 Karnataka districts (9 dialect profiles built)
- Multi-tenant deployment
- Real-time barge-in interrupt handling
- Voice authentication
- Mobile app binary (web-only for demo)

---

## 12. Key Files Reference

| File | What to show |
|------|-------------|
| `backend/main.py` | Full pipeline, scripted scenarios, all REST + WS endpoints |
| `backend/services/verification_engine.py` | 3-state verification loop |
| `backend/services/confidence_scorer.py` | 4-component composite score formula |
| `backend/services/pii_redactor.py` | PII patterns, token map, unredact |
| `backend/services/escalation.py` | EscalationDecision, reason explanations, TTS messages |
| `backend/services/dialect_context.py` | DialectProfile, 9 district mappings |
| `backend/data/karnataka_grievance_taxonomy.json` | 40 intent categories |
| `backend/data/dialect_profiles.json` | Vocabulary hints per district |
| `backend/data/verification_phrasings.json` | Dialect-conditioned restatement variants |
| `backend/demo_fixtures/demo_sessions.py` | 6 pre-built escalated sessions |
| `app_frontend/lib/screens/citizen_view.dart` | Full citizen UI, state machine, verification panel |
| `app_frontend/lib/screens/agent_dashboard.dart` | Queue, context pane, live reply |
| `app_frontend/lib/screens/analytics_dashboard.dart` | Map, charts, stat cards |
