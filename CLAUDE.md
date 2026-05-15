# Samvaad-Setu — Claude Code Guide

Multilingual voice assistant for Karnataka's 1092 citizen helpline. Real-time pipeline: ASR → Dialect-Aware NLU → Multi-Modal Sentiment → Verification Loop → Confidence-Aware Escalation → TTS.

The central design constraint: **correct understanding before action.** Every other component serves the verification loop.

## Architecture

```
Flutter Web (app_frontend/)  ←→  WebSocket  ←→  FastAPI (backend/)  ←→  Redis + Postgres
   ├─ Citizen View                                    ↓
   └─ Agent Dashboard                       Sarvam AI (ASR/TTS)
                                            Google Gemini (NLU)
                                            librosa (prosodic features)
```

## Core Pipeline (per turn)

1. **ASR** → text + per-token confidence
2. **Prosodic feature extraction** → pitch variance, speaking rate, energy
3. **Dialect-aware NLU** → intent, entities, dialect tag (district-conditioned)
4. **Multi-modal sentiment** → fused text + prosodic sentiment score
5. **Verification engine** → restate citizen issue → capture 3-state response
6. **Composite confidence score** → ASR + intent entropy + sentiment + clarification count
7. **Escalation engine** → continue / re-clarify / hand off to human
8. **TTS** → response in citizen's language and dialect register
9. **Audit log + verified-interactions write** → feedback loop closes

## Running the Project

### One-command start (recommended)

```bash
docker compose up
```

Brings up backend + Redis + Postgres + frontend on a shared network. Backend on `:8000`, frontend on `:8081`.

### Manual start

#### Backend

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # edit API keys if needed
alembic upgrade head          # create Postgres tables for audit + feedback loop
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Redis and Postgres must be running. On macOS:
```bash
brew services start redis
brew services start postgresql@15
```

#### Frontend

```bash
cd app_frontend
flutter pub get
flutter run -d chrome --web-port 8081
```

Citizen view at `/`, agent dashboard at `/agent`.

### Mock Mode

Set `ENVIRONMENT=mock` in `backend/.env` to run without API keys — all AI services return plausible fake data with realistic latency simulation.

## Key Files

| File | Purpose |
|------|---------|
| `backend/main.py` | FastAPI app + WebSocket voice pipeline |
| `backend/config.py` | Pydantic settings (reads `.env`) |
| `backend/services/asr.py` | Sarvam AI speech-to-text + confidence extraction |
| `backend/services/prosody.py` | **NEW** — pitch, energy, rate features via librosa |
| `backend/services/nlu.py` | Gemini intent extraction with dialect context injection |
| `backend/services/dialect_context.py` | **NEW** — district → dialect profile mapping |
| `backend/services/intent_taxonomy.py` | **NEW** — Karnataka grievance taxonomy (Sevasindhu/Janasevaka derived) |
| `backend/services/sentiment.py` | Multi-modal sentiment (text + prosodic fusion) |
| `backend/services/verification_engine.py` | **NEW** — restate, capture 3-state response, branch logic |
| `backend/services/confidence_scorer.py` | **NEW** — composite confidence calculation |
| `backend/services/escalation.py` | Escalation rules engine — confidence + sentiment + clarification count |
| `backend/services/tts.py` | Sarvam AI text-to-speech with local fallback |
| `backend/services/session_manager.py` | Redis session CRUD |
| `backend/services/audit_log.py` | **NEW** — Postgres audit trail for every state transition |
| `backend/services/feedback_loop.py` | **NEW** — verified-interactions write + JSONL export |
| `backend/services/pii_redactor.py` | **NEW** — strip PII before any LLM call |
| `backend/models/session_model.py` | Pydantic data models including `verification_state`, `confidence_score` |
| `backend/models/audit_model.py` | **NEW** — SQLAlchemy models for audit + feedback tables |
| `backend/migrations/` | **NEW** — Alembic migrations |
| `app_frontend/lib/views/citizen_view.dart` | Citizen-facing voice UI |
| `app_frontend/lib/views/agent_dashboard.dart` | **NEW** — agent dashboard with live transcript, gauges, edit |
| `app_frontend/lib/widgets/confidence_gauge.dart` | **NEW** — live confidence visualization |
| `app_frontend/lib/widgets/sentiment_timeline.dart` | **NEW** — rolling sentiment chart |
| `app_frontend/lib/services/voice_pipeline_service.dart` | WebSocket client |
| `DEMO.md` | **NEW** — judge-facing demo walkthrough |

## WebSocket Protocol

**Client → Server:**
```json
{ "type": "audio", "data": "<base64 WAV>", "language": "kn", "district": "mangaluru" }
{ "type": "verification_response", "state": "correct" | "partial" | "incorrect", "correction_text": "<optional>" }
{ "type": "agent_correction", "field": "intent", "value": "ration_card_status", "session_id": "..." }
{ "type": "ping" }
```

**Server → Client:**
```json
{
  "type": "turn_update",
  "citizen_turn": { "transcript": "...", "asr_confidence": 0.87 },
  "ai_turn": { "rephrasing": "...", "intent": "...", "dialect_tag": "mangaluru_kn" },
  "confidence_score": {
    "asr_confidence": 0.87,
    "intent_entropy": 0.31,
    "sentiment_intensity": 0.45,
    "clarification_count": 0,
    "composite_score": 0.79
  },
  "sentiment_timeline": [
    { "ts": "...", "label": "neutral", "intensity": 0.2 },
    { "ts": "...", "label": "concerned", "intensity": 0.5 }
  ],
  "verification_state": "pending" | "confirmed" | "partial" | "rejected" | "escalated",
  "session": {...}
}
{ "type": "verification_prompt", "rephrasing": "...", "language": "kn", "dialect": "mangaluru" }
{ "type": "escalation", "packet": {
    "trigger_reason": "low_confidence" | "high_distress" | "repeated_clarification" | "explicit_request",
    "transcript": [...],
    "sentiment_timeline": [...],
    "structured_intent": {...},
    "dialect_tag": "...",
    "confidence_history": [...]
}}
{ "type": "pong" }
```

## Environment Variables

`backend/.env` (copy from `.env.example`):

- `ENVIRONMENT` — `mock` or `production`
- `GEMINI_API_KEY` — Google AI Studio key (NLU)
- `SARVAM_API_KEY` — Sarvam AI key (ASR + TTS)
- `REDIS_URL` — defaults to `redis://localhost:6379`
- `POSTGRES_URL` — defaults to `postgresql://localhost:5432/samvaad_setu`
- `CORS_ORIGINS` — JSON array, e.g. `["http://localhost:8081"]`
- `PII_REDACTION_ENABLED` — `true` in production, masks names/numbers before LLM calls
- `AUDIO_RETENTION_HOURS` — default `0` (audio not persisted)
- `LATENCY_LOGGING` — `true` to enable per-stage latency logs

**Important:** `CORS_ORIGINS` must be a JSON array — pydantic-settings requires this for `list[str]` fields.

## API Endpoints

### Citizen-facing
- `GET /health` — backend + Redis + Postgres status
- `GET /health/latency` — rolling p50/p95 per pipeline stage
- `POST /sessions?district=mangaluru&language=kn` — create session (idempotent via `Idempotency-Key` header)
- `GET /sessions/{id}` — fetch session state
- `WS /ws/{session_id}` — voice pipeline WebSocket

### Agent-facing
- `GET /agent/queue` — incoming escalations sorted by priority
- `GET /sessions/{id}/escalation-packet` — full handoff context
- `POST /sessions/{id}/agent-correction` — write agent edit, feeds feedback loop
- `GET /audit/{session_id}` — full audit log for a session

### Operations
- `GET /training-data/export?format=jsonl&since=...` — export verified interactions for retraining
- `GET /docs` — interactive Swagger UI

## Data Model

### Session (Redis, ephemeral)
- `session_id`, `language`, `district`, `dialect_tag`
- `verification_state`: `pending | confirmed | partial | rejected | escalated`
- `clarification_count`, `confidence_history`, `sentiment_timeline`

### `audit_log` (Postgres)
- `id`, `session_id`, `timestamp`, `event_type`, `actor` (system/citizen/agent), `payload_json`

### `verified_interactions` (Postgres) — feedback loop
- `id`, `session_id`, `audio_hash`, `asr_text`, `intent`, `dialect`, `district`
- `verification_state`, `agent_corrections_json`, `final_intent`, `created_at`

## Privacy & PII Handling

- **Audio:** not persisted by default (`AUDIO_RETENTION_HOURS=0`). When retained, encrypted at rest.
- **PII redaction before LLM calls:** names → `CITIZEN_NAME`, phone numbers → `PHONE_N`, addresses → `ADDRESS_TOKEN`. Only redacted text reaches Gemini.
- **Audit log:** every state transition logged with actor and timestamp; immutable.
- **Citizen consent:** flagged at session creation; required for retention.

## Failure Modes & Graceful Degradation

| Failure | Behavior |
|---------|----------|
| Sarvam ASR down | Fallback to Whisper (local); confidence floor reduced; banner shown |
| Gemini rate-limited | Fallback to cached intent classifier (rule-based on taxonomy); escalation threshold lowered |
| Sarvam TTS down | Fallback to local TTS (Coqui/pyttsx3); degraded-mode banner |
| Redis disconnect | Session continues in-memory for active connection; new sessions blocked until reconnect |
| Postgres disconnect | Audit and feedback writes queued in Redis; replayed on reconnect |
| WebSocket disconnect | Session preserved in Redis for 5 min; auto-resume on reconnect |

## Latency Budget

Total turn-around target: **< 1.5s** for live call feel.

| Stage | Budget |
|-------|--------|
| ASR (streaming) | 300ms |
| Prosodic features | 50ms |
| NLU (Gemini) | 500ms |
| Sentiment fusion | 30ms |
| Verification logic | 20ms |
| TTS (streaming) | 400ms |
| WebSocket overhead | 100ms |
| **Total** | **~1.4s** |

Logged per-stage; rolling averages exposed on `/health/latency`.

## Why This Stack

- **FastAPI** — async-native, WebSocket-first, fast iteration. Right choice for real-time voice.
- **Redis** — ephemeral session state with sub-ms reads; sticky-session-friendly for multi-instance scale.
- **Postgres** — durable audit trail and feedback corpus; SQL-queryable for compliance reviews.
- **Sarvam AI** — best-in-class Kannada/Hindi/English ASR and TTS with dialect coverage; low latency.
- **Gemini** — strong multilingual reasoning; cheap; sufficient for grounded NLU when given dialect context and curated taxonomy.
- **librosa** — lightweight prosodic feature extraction; no GPU needed.
- **Flutter Web** — single codebase for citizen view + agent dashboard; deployable to mobile later without rewrite.

## Limitations (Prototype Scope)

We will demonstrate: full pipeline in Kannada, Hindi, English with Bengaluru and Mangaluru Kannada dialect handling; verification loop end-to-end; agent dashboard with live edits; feedback loop with export; latency tracking.

We will not demonstrate: production telephony integration; coverage of all 31 Karnataka districts; multi-tenant deployment; real-time barge-in interrupt handling; voice authentication.

---

## Implementation Prompts (for Claude Code)

The following prompts are ordered by demo-day priority. Run them in sequence — each builds on the previous.

### Prompt 1 — Verification Engine (HIGHEST PRIORITY)

```
Build a new service `backend/services/verification_engine.py` that owns the verification loop. Requirements:

1. Class `VerificationEngine` with method `generate_verification_prompt(intent, entities, language, district)` that returns a natural rephrasing of the citizen's issue back to them in their language, conditioned on the dialect of their district.

2. Phrasing variants stored in `backend/data/verification_phrasings.json` — at least 3 per language (kn, hi, en), with dialect-tagged variants for Mangaluru, Mysuru, Bengaluru, Hyderabad-Karnataka, North Karnataka. Example structure:
{
  "kn": {
    "default": ["Naanu ardhamaaḍikoṇḍiddu sariyaagideyaa? Neevu... bagge dūru helutta iddīra."],
    "mangaluru": ["Yenu helti, naanu sariyaagi tagonde? Neevu... bagge dūru kotruve."],
    "mysuru": [...]
  }
}

3. Method `process_verification_response(session_id, state, correction_text=None)` that handles the three branches:
   - "correct" → mark verification_state=confirmed, proceed to escalation/handoff decision
   - "partial" → increment clarification_count, generate clarifying question, return to citizen
   - "incorrect" → if clarification_count < 2, ask once more; else trigger escalation with reason="repeated_clarification"

4. Update `models/session_model.py` to add field `verification_state: Literal["pending", "confirmed", "partial", "rejected", "escalated"]` and `clarification_count: int`.

5. Add new WebSocket message types in `main.py`:
   - inbound `verification_response`
   - outbound `verification_prompt`

6. Wire into the main pipeline: after NLU produces intent, the verification_engine runs BEFORE any escalation or final response. The citizen must explicitly confirm before the system commits to an intent.

7. Write unit tests in `backend/tests/test_verification_engine.py` covering all three branches and the escalation-on-repeated-clarification path.
```

### Prompt 2 — Dialect Context

```
Build `backend/services/dialect_context.py`:

1. Class `DialectProfile` with fields: `district`, `dialect_tag`, `vocabulary_hints` (dict), `formality_register`, `common_phrases` (list).

2. Class `DialectContextProvider` with method `get_profile(district: str) -> DialectProfile`. Maps Karnataka districts to dialect profiles.

3. Static profile data in `backend/data/dialect_profiles.json`. Cover at minimum: Bengaluru Urban, Bengaluru Rural, Mysuru, Mangaluru (Dakshina Kannada), Udupi, Hubballi-Dharwad, Belagavi, Kalaburagi, Vijayapura. For each include:
   - 20-40 high-frequency dialect terms with standard Kannada equivalents
   - Common greeting/closing phrases
   - Formality register (formal/informal)
   - Code-mixing patterns observed in that region

4. Method `inject_into_prompt(profile: DialectProfile, base_prompt: str) -> str` that prepends dialect context to any LLM system prompt.

5. Update `services/nlu.py` to call `inject_into_prompt` before sending to Gemini, using the session's district.

6. Update `services/verification_engine.py` to use profile vocabulary in rephrasings.

7. Write a test that sends the same intent through the pipeline with district=mangaluru vs. district=bengaluru and asserts the rephrasings differ.
```

### Prompt 3 — Confidence Scorer

```
Build `backend/services/confidence_scorer.py`:

1. Pydantic model `ConfidenceScore`:
   - asr_confidence: float (0-1)
   - intent_entropy: float (0-1, normalized)
   - sentiment_intensity: float (0-1)
   - clarification_count: int
   - composite_score: float (0-1)

2. Function `compute_composite(asr_conf, intent_entropy, sentiment_intensity, clarification_count) -> float`. Weighted combination:
   - asr_confidence: 0.35
   - (1 - intent_entropy): 0.35
   - (1 - sentiment_intensity if sentiment is distress): 0.20
   - clarification_count penalty: -0.15 per count beyond 0

3. Function `should_clarify(score: ConfidenceScore) -> bool` — composite < 0.6.

4. Function `should_escalate(score: ConfidenceScore, sentiment_label: str) -> tuple[bool, str]` — returns (should_escalate, reason). Triggers:
   - composite < 0.4 → "low_confidence"
   - sentiment_label in {"distress", "fear", "anger"} and intensity > 0.7 → "high_distress"
   - clarification_count >= 2 → "repeated_clarification"

5. Include the full `ConfidenceScore` in every `turn_update` WebSocket message.

6. Wire into `services/escalation.py` — replace any existing rules with the new scorer.

7. Tests in `backend/tests/test_confidence_scorer.py` covering each escalation trigger.
```

### Prompt 4 — Multi-Modal Sentiment

```
Extend `backend/services/sentiment.py` to fuse text-based and prosodic sentiment:

1. Build new service `backend/services/prosody.py` using librosa:
   - Function `extract_prosodic_features(audio_bytes: bytes) -> dict` returning pitch_mean, pitch_variance, energy_mean, speaking_rate, voice_quality.
   - Function `prosodic_distress_score(features: dict) -> float (0-1)` — high pitch variance + high energy + fast rate = high distress signal.

2. In `services/sentiment.py`:
   - Keep existing text-based sentiment (Gemini or local classifier).
   - Add `fuse_sentiments(text_sentiment, prosodic_score) -> SentimentResult`. Weighted average: text 0.6, prosodic 0.4. Take max of intensities.
   - Output schema: `{ "label": str, "intensity": float, "text_component": float, "prosodic_component": float }`.

3. Update `models/session_model.py`: `sentiment_timeline: list[SentimentResult]` capped at last 20 turns.

4. Include the timeline in every `turn_update` payload.

5. Test: a clip with calm words but high vocal stress should produce intensity > text-only score.

6. If librosa is too heavy at runtime, gate prosodic extraction behind a feature flag `ENABLE_PROSODY` and fall back to text-only.
```

### Prompt 5 — Karnataka Intent Taxonomy

```
Build `backend/services/intent_taxonomy.py`:

1. Static taxonomy in `backend/data/karnataka_grievance_taxonomy.json` covering 30-40 common 1092 grievance categories. Derive from public Sevasindhu and Janasevaka category structures. Include:
   - water_connection, water_supply_issue
   - ration_card_application, ration_card_status, ration_card_correction
   - bbmp_property_tax, bbmp_khata_transfer, bbmp_birth_certificate
   - bescom_billing, bescom_new_connection, bescom_outage
   - public_health, encroachment, road_repair, streetlight, garbage
   - police_grievance, women_safety
   - government_employee_grievance, pension_issue
   - school_admission, scholarship
   - distress_emergency (special category that always escalates)
   ... etc.

2. Each category has: id, kn_label, hi_label, en_label, responsible_department, escalation_priority (1-5).

3. Class `IntentTaxonomy` with methods:
   - `get_categories(language: str) -> list[dict]` for prompt injection
   - `validate_intent(intent_id: str) -> bool`
   - `get_responsible_department(intent_id: str) -> str`

4. Update `services/nlu.py`: inject the taxonomy as a constrained-output schema in the Gemini prompt. The model must return one of the taxonomy intent_ids, not free-form text.

5. If the model returns an unknown intent, mark the session for human review with reason="intent_out_of_taxonomy".
```

### Prompt 6 — Audit Log + Feedback Loop

```
Build the persistence layer for auditability and the feedback loop.

1. Add Postgres dependency: SQLAlchemy + Alembic. Update `requirements.txt`.

2. Create `backend/models/audit_model.py` with SQLAlchemy models:
   - `AuditLog`: id, session_id, timestamp, event_type, actor, payload_json
   - `VerifiedInteraction`: id, session_id, created_at, audio_hash, asr_text, intent, dialect, district, verification_state, agent_corrections_json, final_intent

3. Initial Alembic migration creating both tables.

4. `backend/services/audit_log.py` with methods `log_event(session_id, event_type, actor, payload)`. Called from:
   - session creation
   - every verification_state transition
   - every escalation
   - every agent correction

5. `backend/services/feedback_loop.py`:
   - `write_verified_interaction(session_id, ...)` — called when verification_state becomes "confirmed".
   - `record_agent_correction(session_id, field, value)` — called from agent dashboard.
   - `export_jsonl(since: datetime) -> Iterator[str]` — yields verified interactions as JSONL lines.

6. New endpoints in `main.py`:
   - `GET /audit/{session_id}` — full audit trail
   - `POST /sessions/{id}/agent-correction`
   - `GET /training-data/export?format=jsonl&since=...`

7. Tests covering: verification confirmation writes a row, agent correction updates the row, export endpoint streams JSONL correctly.
```

### Prompt 7 — Agent Dashboard (Backend Support)

```
Backend support for the agent dashboard. UI work is in a separate prompt.

1. Endpoint `GET /agent/queue` — returns escalated sessions sorted by priority (sentiment intensity DESC, then created_at ASC). Pagination via `limit` and `offset`.

2. Endpoint `GET /sessions/{id}/full-context` — returns: full transcript, sentiment timeline, confidence history, structured intent, dialect tag, audit log summary. This is what the agent dashboard renders.

3. New WebSocket route `WS /ws/agent/{agent_id}` — agent connects to receive real-time queue updates. When a new escalation fires, all connected agents get a notification.

4. Endpoint `POST /sessions/{id}/agent-correction` — agent edits a field; writes to audit log and feedback loop.

5. Endpoint `POST /sessions/{id}/resolve` — agent marks the session resolved; audit logged.

6. Tests covering: queue ordering, real-time agent notifications via WebSocket, correction propagation to feedback loop.
```

### Prompt 8 — PII Redaction

```
Build `backend/services/pii_redactor.py`:

1. Function `redact(text: str, language: str) -> tuple[str, dict]` returning redacted_text and a token map.
2. Patterns to redact:
   - Indian phone numbers (10-digit, with optional +91 prefix) → `PHONE_N`
   - Aadhaar-like sequences (12 digits) → `AADHAAR_N`
   - Names: language-aware NER (use Indic NLP library or spaCy for Hindi/English; for Kannada use a small NER model or curated common-name list) → `CITIZEN_NAME_N`
   - Addresses: pattern-based detection (door numbers, street, area) → `ADDRESS_N`
3. Function `unredact(redacted_text: str, token_map: dict) -> str` to restore original tokens.
4. Wire into `services/nlu.py`: redact before sending to Gemini, unredact on the way out for any text shown to the user.
5. Feature flag `PII_REDACTION_ENABLED` in config.
6. Tests covering each pattern type.
```

### Prompt 9 — Operational Polish

```
1. Latency tracking middleware in `backend/middleware/latency.py`. Logs per-stage latency to a rolling buffer. Endpoint `GET /health/latency` returns p50/p95 per stage.

2. Idempotency on `POST /sessions`: accept `Idempotency-Key` header; cache response in Redis for 5 min.

3. Local TTS fallback in `services/tts.py`. Wrap Sarvam call in try/except; on failure use Coqui or pyttsx3 with degraded-mode flag in response.

4. ASR fallback to Whisper (local) when Sarvam fails. Same pattern.

5. `docker-compose.yml` at repo root: backend, frontend, redis, postgres on a shared network. Environment variables wired from a single `.env` at root.

6. `DEMO.md` at repo root — judge-facing walkthrough. Sections:
   - 90-second demo flow
   - Two scenarios: Mangaluru Kannada (verification loop) and distressed Hindi (auto-escalation)
   - What to look at: confidence gauge, sentiment timeline, agent dashboard handoff
   - Pre-recorded fixture audio paths for fallback if live mic fails
```

### Prompt 10 — Demo Fixtures

```
Create `backend/demo_fixtures/` with pre-recorded audio clips and a fixture loader:

1. Audio clips (record or synthesize via Sarvam TTS):
   - `bengaluru_kannada_routine.wav` — clear Bengaluru Kannada, simple ration card status query
   - `mangaluru_kannada_dialect.wav` — Mangaluru-dialect Kannada with verification needed
   - `distressed_hindi_emergency.wav` — Hindi caller in distress, should auto-escalate
   - `hinglish_codemix.wav` — code-mixed Hindi/English query
   - `kannada_low_audio_quality.wav` — noisy audio to test ASR confidence behavior

2. `backend/demo_fixtures/loader.py` with function `load_fixture(name: str)` returning audio bytes + expected metadata (district, language, expected behavior).

3. New endpoint `POST /demo/run-fixture/{fixture_name}` — runs the fixture through the full pipeline and returns the result. Useful for demo day if live mic input fails.

4. Document in `DEMO.md`.
```