# Samvaad-Setu

**Multilingual Voice Assistant for Karnataka's 1092 Citizen Helpline**

---

## The Problem

Karnataka's 1092 helpline serves millions of citizens across 31 districts — speaking Kannada, Hindi, English, and a dozen regional dialects. When a distressed Mangaluru resident calls about a water supply failure, three things have to happen correctly and quickly: the system must *hear* them accurately, *understand* what they mean (not just what they said), and *confirm* it before taking any action.

Today, that handoff fails constantly. Dialect mismatches produce wrong intents. Low ASR confidence goes undetected. Agents receive escalation packets with no context. There is no audit trail, no feedback loop, and no way to tell if the system actually helped.

Samvaad-Setu is a real-time voice pipeline designed around a single constraint: **correct understanding before action.** Every component — the verification loop, the confidence scorer, the dialect-aware NLU — exists to enforce that constraint.

---

## Architecture

```mermaid
flowchart TD
    A[Citizen Voice Input] -->|Base64 WAV / WebSocket| B[FastAPI Backend]
    B --> C[Sarvam AI ASR]
    C -->|transcript + per-token confidence| D[Prosodic Feature Extraction\nlibrosa]
    D --> E[Dialect-Aware NLU\nGoogle Gemini]
    E --> F[Multi-Modal Sentiment\ntext + prosodic fusion]
    F --> G[Verification Engine\nrestate → 3-state confirm]
    G -->|confirmed| H[Confidence Scorer\nASR + entropy + sentiment + clarification]
    G -->|partial / incorrect| E
    H --> I{Escalation Engine}
    I -->|confidence OK| J[TTS Response\nSarvam AI]
    I -->|low confidence / distress| K[Agent Dashboard\nhandoff packet]
    J -->|audio stream| A
    K --> L[Human Agent]

    subgraph Persistence
        M[(Redis\nephemeral sessions)]
        N[(PostgreSQL\naudit trail + feedback)]
    end

    B <--> M
    B --> N
```

---

## Voice Pipeline — Per Turn

```mermaid
sequenceDiagram
    participant C as Citizen
    participant WS as WebSocket
    participant P as Pipeline
    participant V as Verification
    participant E as Escalation

    C->>WS: audio chunk (base64 WAV)
    WS->>P: ASR → transcript + confidence
    P->>P: prosodic features (pitch, energy, rate)
    P->>P: dialect-aware NLU → intent + entities
    P->>P: multi-modal sentiment fusion
    P->>V: generate verification prompt
    V-->>C: "Did I understand correctly? You are calling about..."
    C->>WS: verification_response (correct / partial / incorrect)
    V->>P: confirmed → composite confidence score
    P->>E: evaluate thresholds
    alt confidence OK
        E-->>C: TTS response in citizen's dialect
    else low confidence / distress / repeated failure
        E-->>Agent: escalation packet with full context
    end
```

---

## Features

### Analytics Dashboard

A regional overview screen at `/analytics`, auto-refreshing every 10 seconds.

**Stat cards:** Total Calls today · Escalated % · Resolved % (with "N resolved by human agent" sub-label) · Avg Confidence · Avg Distress

**Karnataka district map** (flutter_map + OpenStreetMap) — each district rendered as a bubble marker. Color encodes distress level (green → amber → red); size scales with call volume. Tap for a tooltip with district name, call count, escalation count, and primary intent.

**Charts:** District bar chart (calls + escalated overlay) · Intent distribution pie (8 categories) · Escalation reasons bar (High Distress / Repeated Clarification / Low Confidence) · Language distribution donut · Hourly trend line (8am–9pm) · Seasonal trends card (BBMP 2020–2025 public data)

**Hotspot alerts strip:** Districts with escalation rate > 30% shown as red chips.

**Ticket log section:** Recent tickets with status, district, intent, created-at — filterable by status and district.

---

### Scripted Demo Scenarios with TTS Pre-Cache

Five realistic conversation flows are scripted with keyword matching. When a demo transcript matches, the backend skips NLU/sentiment inference entirely and serves pre-synthesized audio from a disk cache (`ss_tts_cache.json`) — zero-latency, deterministic demos regardless of API availability.

**Scripted flows:** BESCOM billing dispute · Ration card correction · Water supply crisis · Workplace harassment / women's safety (auto-escalates) · BBMP road repair

Cache is loaded on startup and can be regenerated via `/tts-cache/regenerate`.

**Pre-seeded demo queue:** Six sessions are seeded in the agent queue at backend startup so demo day requires no live calls:
1. Mangaluru — water supply crisis (distress, Tulu Coast dialect)
2. Bengaluru — workplace harassment / women's safety (fear, urban code-mix)
3. Kalaburagi — pension stopped, senior citizen (repeated clarification, Hindi)
4. Mysuru — ration card address transfer (low ASR confidence)
5. Belagavi — garbage not collected (medium urgency, North Karnataka)
6. PII redaction demo (shows Aadhaar → `AADHAAR_1` masking in action)

---

### Fast-Path Pipeline

Conversational responses go out immediately — full NLU runs in the background while the citizen is already listening.

```
Audio → ASR → fast-path check (keyword match)
                 │ hit: serve cached turn + TTS, done
                 │
                 ▼
         Gemini conversational reply (~200ms) → TTS → sent to citizen
                 │
                 ▼
         Verification prompt → TTS → sent
                 │
                 ▼ (background, non-blocking)
         Full NLU + dialect context + PII redaction
         Sentiment fusion (text + prosodic)
         Confidence score + escalation evaluation
         nlu_update → citizen WebSocket
         broadcast_to_agents → all agent dashboards
```

End-to-end target: **< 1.5 s** before citizen hears the first word.

---

### Ticket Management

After a call is confirmed or escalated, a ticket is automatically created with: ticket ID, intent label, responsible department, status, and session ID. Citizens see the ticket card at the end of their call.

Agents can update ticket status from the dashboard. The ticket log in the Analytics Dashboard reflects live status.

**Endpoints:** `GET /tickets` · `GET /tickets/{id}` · `POST /sessions/{id}/create-ticket` · `PATCH /tickets/{id}/status`

---

### Dialect-Aware Understanding

The system maps each of Karnataka's districts to a dialect profile, injecting vocabulary hints, formality register, and code-mixing patterns into the Gemini prompt before any NLU call is made.

**9 district profiles covered:** Bengaluru Urban, Bengaluru Rural, Mysuru, Mangaluru (Tulu coast), Udupi, Hubballi-Dharwad, Belagavi, Kalaburagi, Vijayapura — each with 20–40 dialect terms, regional greetings, and observed code-mixing patterns (English, Hindi, Urdu).

Verification prompts are rendered in the citizen's dialect register, not generic Kannada — so a Mangaluru caller hears *"Yenu helti, naanu sariyaagi tagonde?"* rather than a Bengaluru-tuned phrasing.

### Verification Loop

After every turn, the system restates the citizen's issue back to them before committing to any intent. The citizen can respond with three states:

- **Correct** — confirmation recorded; pipeline proceeds
- **Partial** — clarification count increments; targeted follow-up question generated
- **Incorrect** — if fewer than 2 clarifications attempted, re-asks; otherwise escalates with reason `repeated_clarification`

This loop is the primary defense against wrong intent extraction. It runs before any escalation or final response decision.

### Composite Confidence Scoring

```mermaid
block-beta
    columns 4
    A["ASR Confidence\n× 0.35"]:1
    B["1 − Intent Entropy\n× 0.35"]:1
    C["1 − Sentiment Intensity\n× 0.20"]:1
    D["Clarification Penalty\n−0.15 per count"]:1
    E["Composite Score\n(0–1)"]:4
    A --> E
    B --> E
    C --> E
    D --> E
```

- **< 0.6** → trigger clarification
- **< 0.4** → escalate with reason `low_confidence`
- Sentiment label `distress / fear / anger` + intensity > 0.7 → escalate with reason `high_distress`
- Clarification count ≥ 2 → escalate with reason `repeated_clarification`

### Multi-Modal Sentiment

Text-based sentiment from Gemini is fused with prosodic signals extracted by librosa (pitch variance, energy, speaking rate). A caller who uses calm words but exhibits elevated vocal stress will produce a higher distress score than text alone would suggest.

Fusion weights: text 0.6, prosodic 0.4. Output includes per-component breakdown and a rolling timeline of the last 20 turns.

### Karnataka Grievance Taxonomy

30+ intent categories derived from Sevasindhu and Janasevaka — labeled in Kannada, Hindi, and English. Each category carries an escalation priority (1 = emergency, 5 = routine) and a responsible department mapping.

The Gemini NLU prompt is constrained to return only valid taxonomy IDs. Any out-of-taxonomy response triggers a human review flag.

Always-escalate categories: `distress_emergency`, `women_safety`, `hospital_complaint`, `food_adulteration`.

### PII Redaction

Before any text reaches Gemini, names, phone numbers, Aadhaar sequences, and addresses are replaced with tokens (`CITIZEN_NAME_N`, `PHONE_N`, `AADHAAR_N`, `ADDRESS_N`). Token maps are maintained in-memory; PII never appears in audit logs or training exports.

Controlled by `PII_REDACTION_ENABLED` in `.env`. Disabled automatically in mock mode.

### Agent Dashboard

When a call escalates, the agent receives a structured handoff packet and a live session view:

- Full conversation transcript with multi-language toggle (KN / HI / EN)
- Rolling sentiment timeline chart
- Composite confidence score history per turn
- Structured intent + responsible department + dialect tag
- One-line AI-generated escalation summary

**Agent reply:** Agents type a response directly in the dashboard → POST to `/sessions/{id}/agent-reply` → Sarvam TTS synthesizes it → citizen hears it with a typewriter animation on their screen.

**Session resolution:** Mark Reviewed → Resolve (removes from queue, creates/updates ticket, logs to audit trail) or Resolved by Human (increments the analytics `resolved_by_human` metric).

Agents can also correct misclassified intents from the dashboard. Corrections propagate to the feedback loop and are marked in the audit trail with actor and timestamp.

**Real-time updates** via `/ws/agent/{agent_id}` — agents receive `new_escalation`, `queue_update`, and `session_live_update` events without a page reload.

**Toast notifications** slide in from the top-right for new escalations; tapping a toast auto-selects that session.

---

### End Call & Feedback Flow

Citizens can end a call at any time. The flow: hold message → ticket creation → feedback overlay. The feedback overlay presents a 5-star rating; submission triggers a farewell TTS message in the caller's language. Ratings are logged to the audit trail.

### Feedback Loop + Audit Trail

Every confirmed interaction writes a row to `verified_interactions` in PostgreSQL. Agent corrections update the `final_intent` field. The full corpus is exportable as JSONL for retraining.

Every state transition — session creation, verification confirmation, escalation, agent correction — is appended to `audit_log` with an immutable timestamp and actor field.

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Frontend | Flutter Web | Single codebase for citizen view + agent dashboard + analytics; mobile-ready |
| Backend | FastAPI | Async-native, WebSocket-first, fast iteration |
| ASR / TTS | Sarvam AI (`bulbul:v2`) | Best-in-class Kannada/Hindi/English with dialect coverage |
| NLU | Google Gemini (`gemini-2.0-flash`) | Strong multilingual reasoning; cheap; constrained-output via taxonomy |
| Prosody | librosa | Lightweight pitch/energy/rate extraction; no GPU required |
| Session state | Redis | Sub-ms reads; ephemeral and sticky-session friendly |
| Audit + feedback | PostgreSQL | Durable, SQL-queryable for compliance and retraining |
| Maps | flutter_map + OpenStreetMap | District-level distress heatmap on analytics dashboard |
| Charts | fl_chart | Intent distribution, sentiment timeline, hourly trends |

---

## Running the Project

### Docker (recommended)

```bash
docker compose up
```

Backend on `:8000`, frontend on `:8081`, Redis and Postgres wired automatically.

### Manual

```bash
# Backend
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add API keys or set ENVIRONMENT=mock
alembic upgrade head
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (separate terminal)
cd app_frontend
flutter pub get
flutter run -d chrome --web-port 8081
```

Citizen view at `http://localhost:8081/`, agent dashboard at `http://localhost:8081/agent`, analytics at `http://localhost:8081/analytics`.

### Mock Mode

Set `ENVIRONMENT=mock` in `backend/.env` to run without API keys. All AI services return realistic fake data with simulated latency — useful for UI testing and demos.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ENVIRONMENT` | `production` | Set `mock` to skip real API calls |
| `SARVAM_API_KEY` | — | Sarvam AI (ASR + TTS) |
| `GEMINI_API_KEY` | — | Google AI Studio (NLU) |
| `REDIS_URL` | `redis://localhost:6379` | Session store |
| `POSTGRES_URL` | `postgresql://localhost:5432/samvaad_setu` | Audit + feedback DB |
| `CORS_ORIGINS` | `["http://localhost:8081"]` | JSON array — required for pydantic-settings |
| `PII_REDACTION_ENABLED` | `true` | Mask PII before LLM calls |
| `ENABLE_PROSODY` | `true` | Librosa feature extraction; falls back to neutral if `false` |
| `AUDIO_RETENTION_HOURS` | `0` | Audio not persisted by default |
| `LATENCY_LOGGING` | `true` | Per-stage timing logs |

---

## API Endpoints

```
GET  /health                              backend + Redis + Postgres status
GET  /health/latency                      rolling p50/p95 per pipeline stage
POST /sessions?district=...&language=...  create session (idempotent via Idempotency-Key)
GET  /sessions/{id}                       fetch session state
WS   /ws/{session_id}                     citizen voice pipeline

GET  /agent/queue                         escalations sorted by priority
GET  /sessions/{id}/escalation-packet     full handoff context
POST /sessions/{id}/agent-correction      write agent intent edit → feedback loop
POST /sessions/{id}/agent-reply           agent text → TTS → citizen
POST /sessions/{id}/resolve               mark session resolved
GET  /sessions/{id}/full-context          transcript + sentiment + confidence + audit summary
WS   /ws/agent/{agent_id}                 real-time agent queue feed
GET  /audit/{session_id}                  full audit trail

GET  /analytics/overview                  aggregated stats, district breakdown, intent distribution
GET  /tickets                             list tickets (filter by status, district)
GET  /tickets/{id}                        single ticket detail
POST /sessions/{id}/create-ticket         create ticket after confirmation or escalation
PATCH /tickets/{id}/status               update ticket status

GET  /tts-cache/load                      load pre-cached TTS audio for demo scenarios
POST /tts-cache/regenerate               force-regenerate TTS cache

GET  /training-data/export?format=jsonl   export verified interactions for retraining
GET  /docs                                Swagger UI
```

---

## Latency Budget

Target end-to-end: **< 1.5 s**

| Stage | Budget |
|---|---|
| ASR (streaming) | 300 ms |
| Prosodic features | 50 ms |
| NLU (Gemini) | 500 ms |
| Sentiment fusion | 30 ms |
| Verification logic | 20 ms |
| TTS (streaming) | 400 ms |
| WebSocket overhead | 100 ms |

Per-stage actuals available at `/health/latency`.

---

## Project Structure

```
samvaad-setu/
├── backend/
│   ├── main.py                          FastAPI app + WebSocket pipeline
│   ├── config.py                        Pydantic settings
│   ├── services/
│   │   ├── asr.py                       Sarvam AI ASR
│   │   ├── tts.py                       Sarvam AI TTS + local fallback
│   │   ├── nlu.py                       Gemini NLU with dialect + taxonomy injection
│   │   ├── prosody.py                   librosa pitch / energy / rate
│   │   ├── sentiment.py                 Text + prosodic fusion
│   │   ├── dialect_context.py           District → dialect profile mapping
│   │   ├── verification_engine.py       Restate → 3-state confirmation loop
│   │   ├── confidence_scorer.py         Composite score calculation
│   │   ├── intent_taxonomy.py           Karnataka grievance taxonomy
│   │   ├── escalation.py                Escalation rules engine
│   │   ├── audit_log.py                 PostgreSQL audit writes
│   │   ├── feedback_loop.py             Verified interactions + JSONL export
│   │   ├── pii_redactor.py              PII masking before LLM calls
│   │   └── session_manager.py           Redis session CRUD
│   ├── models/
│   │   ├── session_model.py             Session state, turns, confidence
│   │   └── audit_model.py               SQLAlchemy: AuditLog, VerifiedInteraction
│   ├── data/
│   │   ├── dialect_profiles.json        9 district profiles
│   │   ├── karnataka_grievance_taxonomy.json  30+ intent categories
│   │   └── verification_phrasings.json  Dialect-conditioned rephrasings
│   ├── migrations/                      Alembic migrations
│   └── tests/                           Unit tests for all services
│
├── app_frontend/
│   ├── lib/
│   │   ├── screens/
│   │   │   ├── citizen_view.dart        Voice call interface + feedback overlay
│   │   │   ├── agent_dashboard.dart     Live queue + agent reply + corrections
│   │   │   └── analytics_dashboard.dart Regional overview + district map + charts
│   │   ├── widgets/
│   │   │   ├── confidence_gauge.dart    Real-time confidence visualization
│   │   │   └── sentiment_timeline.dart  Rolling sentiment chart
│   │   └── services/
│   │       └── voice_pipeline_service.dart  WebSocket client
│   └── pubspec.yaml
│
├── docker-compose.yml
├── CLAUDE.md                            Architecture + implementation reference
├── PRESENTATION.md                      Full feature walkthrough for reviewers
└── DEMO.md                              Demo walkthrough
```

---

*Built for Karnataka's citizens — multilingual, dialect-aware, distress-sensitive.*