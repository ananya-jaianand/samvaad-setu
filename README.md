# Samvaad-Setu | ಸಂವಾದ ಸೇತು
**Real-time multilingual voice assistant for Karnataka 1092 citizen helpline**

---

## Architecture at a Glance

```
Browser Mic → WebSocket → FastAPI
                              ├─ ASR    (Sarvam Saarika + AI4Bharat fallback)
                              ├─ NLU    (Claude Sonnet — intent, rephrasing, summary)
                              ├─ Sentiment (prosodic + text fusion)
                              ├─ Verification Engine (3-state confirm loop)
                              ├─ Escalation Engine (multi-signal scoring)
                              └─ TTS    (Sarvam Bulbul, emotion-conditioned)
                                    ↓
                           Agent Dashboard (React + Tailwind)
                           └─ Confidence gauges, sentiment timeline,
                              AI interpretation panel (editable),
                              ticket draft, live transcript
```

---

## Quick Start (10 minutes)

### Option A — Docker (recommended)

```bash
git clone <repo>
cd samvaad-setu
cp .env.example .env
# Edit .env — at minimum add ANTHROPIC_API_KEY
docker compose up --build
```

Open http://localhost:5173

### Option B — Local (no Docker)

**Backend:**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env  # edit as needed
uvicorn main:app --reload --port 8000
```

**Redis (required for session state):**
```bash
redis-server  # or: brew install redis && redis-server
# Without Redis, falls back to in-memory (fine for hackathon)
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

---

## API Keys

| Service | Where to get | Required for |
|---------|-------------|--------------|
| `ANTHROPIC_API_KEY` | console.anthropic.com | NLU, summarization, ticket draft |
| `SARVAM_API_KEY` | api.sarvam.ai | Real ASR + TTS (Saarika + Bulbul) |
| `AI4BHARAT_API_KEY` | ai4bharat.iitm.ac.in | IndicConformer ASR fallback |

**Without any keys:** Set `ENVIRONMENT=mock` and the full pipeline runs with realistic synthetic data. Every layer works, escalation fires, gauges move. Demo-able immediately.

---

## Mock Mode vs Production Mode

| Feature | Mock Mode | Production Mode |
|---------|-----------|-----------------|
| ASR | Synthetic Kannada/Hindi/English sentences | Sarvam Saarika live |
| NLU | Keyword-based intent | Claude Sonnet |
| Sentiment | Keyword heuristics | Claude + openSMILE |
| TTS | Silent WAV placeholder | Sarvam Bulbul |
| Escalation | Fully real (signals computed) | Fully real |
| Dashboard | Fully real | Fully real |

Switch by setting `ENVIRONMENT=production` in `.env`.

---

## WebSocket Protocol

**Client → Server:**
```json
{ "type": "audio",        "data": "<base64 WebM>", "language": "kn", "district": "mysuru" }
{ "type": "verification", "data": "ಹೌದು" }
{ "type": "agent_correction", "turn_id": "abc12345", "correction": "...", "intent": "road_damage" }
{ "type": "ping" }
```

**Server → Client:**
```json
{ "type": "turn_update",       "citizen_turn": {...}, "ai_turn": {...}, "session": {...}, "nlu": {...} }
{ "type": "verification_result","state": "correct|partially_correct|incorrect", "ai_response": "..." }
{ "type": "escalation",        "packet": {...}, "escalation_message": "..." }
{ "type": "error",             "message": "..." }
```

---

## File Structure

```
samvaad-setu/
├── backend/
│   ├── main.py                  ← FastAPI app + WebSocket pipeline
│   ├── config.py                ← All settings, district map, taxonomy
│   ├── models/session_model.py  ← Turn, SessionState, EscalationPacket
│   ├── services/
│   │   ├── asr.py               ← Sarvam + AI4Bharat (REPLACE markers)
│   │   ├── nlu.py               ← Claude integration
│   │   ├── tts.py               ← Sarvam Bulbul (REPLACE markers)
│   │   ├── sentiment.py         ← Text + prosodic fusion (openSMILE stub)
│   │   ├── verification.py      ← 3-state confirmation engine
│   │   ├── escalation.py        ← Multi-signal escalation scorer
│   │   └── session_manager.py   ← Redis-backed session state
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── App.jsx              ← Split layout (citizen | agent)
│       ├── hooks/useVoicePipeline.js ← WebSocket + MediaRecorder hook
│       └── components/
│           ├── CitizenPanel.jsx       ← Voice interface + verification UI
│           ├── AgentDashboard.jsx     ← Full agent dashboard
│           ├── ConfidenceGauge.jsx    ← SVG ring gauge
│           ├── SentimentTimeline.jsx  ← Per-turn sentiment history
│           └── TranscriptPanel.jsx    ← Live scrolling transcript
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## What's Stubbed (and How to Upgrade)

### Sarvam ASR/TTS
Look for `# ── REPLACE WITH REAL API ──` in `services/asr.py` and `services/tts.py`.
The HTTP calls are already written — just add `SARVAM_API_KEY` to `.env`.

### openSMILE (prosodic sentiment)
Look for `# ── REPLACE WITH openSMILE ──` in `services/sentiment.py`.
```bash
pip install opensmile
```
Then replace the stub with:
```python
import opensmile
smile = opensmile.Smile(feature_set=opensmile.FeatureSet.eGeMAPSv02, feature_level=opensmile.FeatureLevel.Functionals)
features = smile.process_signal(audio_np, 16000)
# Map features to sentiment via trained regressor
```

### IndicBERT (intent/sentiment)
Replace the keyword heuristics in `services/sentiment.py` with AI4Bharat's hosted IndicBERT endpoint, or fine-tune locally on the Sevasindhu/Janasevaka taxonomy.

### Feedback Loop / Retraining
`_handle_agent_correction` in `main.py` has a `# TODO: write to labeled dataset` marker.
Connect to your Postgres audit log + weekly retraining trigger there.

---

## Escalation Tuning

All thresholds are in `.env`:
- `ASR_CONFIDENCE_THRESHOLD` (0.65) — below this, confidence gauge goes amber
- `INTENT_ENTROPY_THRESHOLD` (0.45) — above this, intent is ambiguous
- `DISTRESS_SCORE_THRESHOLD` (0.70) — above this, immediate human handoff
- `MAX_CLARIFICATION_TURNS` (3) — max failed verifications before escalation

---

## Supported Districts & Dialects

| District | Variant | Notes |
|----------|---------|-------|
| bengaluru_urban | Urban Kannada | Low formality, code-switching |
| mysuru | Mysuru | High formality |
| mangaluru | Tulu coast | Tulu influence |
| belagavi | North Karnataka | Marathi influence |
| kalaburagi | Hyderabad-Karnataka | Urdu influence |

Add new districts in `config.py → DISTRICT_DIALECT_MAP`.
