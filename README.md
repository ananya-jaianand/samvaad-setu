# Samvaad-Setu 🗣️

**Multilingual Voice Assistant for Karnataka's 1092 Citizen Helpline**

A real-time voice-based grievance management system supporting Kannada, Hindi, and English with AI-powered intent extraction, sentiment analysis, and intelligent escalation.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Flutter Frontend (Web/Mobile)             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Voice Input  │  │ Live Chat UI │  │ Agent Panel  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │ WebSocket
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (Python)                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Sarvam   │  │ Google   │  │ Sentiment│  │ Escalation│   │
│  │ ASR/TTS  │  │ Gemini   │  │ Analysis │  │ Logic     │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 🧠 Core Voice Pipeline

The system processes each turn through 9 stages:

1. **ASR** — Speech-to-text via Sarvam AI with per-token confidence
2. **Prosodic Analysis** — Extract pitch, energy, speaking rate using librosa
3. **Dialect-Aware NLU** — Intent extraction via Google Gemini, conditioned on district dialect profile
4. **Multi-Modal Sentiment** — Fuse text-based and prosodic signals; detect distress
5. **Verification Loop** — Auto-restate citizen issue back to them in their dialect; await confirmation
6. **Confidence Scoring** — Composite score from ASR + intent entropy + sentiment + clarification attempts
7. **Escalation Engine** — Route based on confidence thresholds and distress signals
8. **Text-to-Speech** — Sarvam AI TTS; falls back to local Coqui if unavailable
9. **Audit Trail** — Log every state transition to PostgreSQL for compliance and feedback

**Central Design Constraint:** Correct understanding before action. Every component serves the verification loop.

---

## 📋 Prerequisites

### Backend Requirements
- **Python**: 3.9 or higher
- **pip**: Latest version
- **Redis**: 6.0+ (for session management and ephemeral state)
- **PostgreSQL**: 12+ (for audit trail and feedback loop)

### Frontend Requirements
- **Flutter**: 3.0.0 or higher
- **Dart**: 2.17.0 or higher
- **Chrome/Edge**: For web development

---

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)

```bash
git clone https://github.com/yourusername/samvaad-setu.git
cd samvaad-setu

# One-command start: backend + Redis + Postgres + frontend
docker-compose up

# Access:
# Frontend: http://localhost:8081
# Backend:  http://localhost:8000
# Swagger:  http://localhost:8000/docs
```

### Option 2: Manual Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/samvaad-setu.git
cd samvaad-setu
```

---

## 🔧 Backend Setup

### Step 1: Navigate to Backend Directory

```bash
cd backend
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

Create a `.env` file in the `backend/` directory:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# ---- Environment ----
# Set to 'mock' to run without real API keys (all services return fake but realistic data)
ENVIRONMENT=production

# ---- API Keys (Get from https://www.sarvam.ai / https://makersuite.google.com) ----
SARVAM_API_KEY=your_sarvam_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here

# ---- Sarvam Configuration ----
SARVAM_ASR_MODEL=saarika:v2.5
SARVAM_TTS_MODEL=bulbul:v1

# ---- Redis Configuration ----
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# ---- PostgreSQL Configuration ----
POSTGRES_URL=postgresql://localhost:5432/samvaad_setu

# ---- Server Configuration ----
CORS_ORIGINS=["http://localhost:8081","http://localhost:3000"]
MAX_CLARIFICATION_TURNS=3

# ---- Feature Flags ----
PII_REDACTION_ENABLED=true
ENABLE_PROSODY=true
AUDIO_RETENTION_HOURS=0
LATENCY_LOGGING=true
```

**Important:** `CORS_ORIGINS` must be a JSON array string.

### Step 5: Set Up Database (PostgreSQL)

```bash
# On macOS (using Homebrew):
brew services start postgresql@15

# On Linux:
sudo systemctl start postgresql

# Create database
psql -c "CREATE DATABASE samvaad_setu;"
```

### Step 6: Start Redis (if not running)

```bash
# On macOS (using Homebrew):
brew services start redis

# On Linux:
sudo systemctl start redis

# On Windows (using WSL or Docker):
docker run -d -p 6379:6379 redis:latest
```

### Step 7: Initialize Database Tables

```bash
cd backend
alembic upgrade head
```

### Step 8: Run the Backend Server

```bash
python main.py
```

The backend will start on `http://localhost:8000`

**Verify it's running:**
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "ok",
  "mode": "production",
  "redis_connected": true,
  "postgres_connected": true
}
```

---

## 📱 Frontend Setup

### Step 1: Navigate to Frontend Directory

```bash
cd app_frontend
```

### Step 2: Install Flutter Dependencies

```bash
flutter pub get
```

### Step 3: Configure Backend URL

Edit `lib/config/app_config.dart`:

```dart
class AppConfig {
  // For local development
  static const String baseUrl = 'http://localhost:8000';
  static const String wsUrl = 'ws://localhost:8000/ws';
  
  // For production, update to your deployed backend URL
  // static const String baseUrl = 'https://your-backend.com';
  // static const String wsUrl = 'wss://your-backend.com/ws';
}
```

### Step 4: Run the Flutter App

#### For Web Development:

```bash
flutter run -d chrome --web-port 8081
```

The app will open in Chrome at `http://localhost:8081`

#### For Android:

```bash
# Connect Android device or start emulator
flutter run -d android
```

#### For iOS:

```bash
# Requires macOS with Xcode
flutter run -d ios
```

#### For macOS Desktop:

```bash
flutter run -d macos
```

---

## 🧪 Testing the Complete Flow

### 1. Start Backend
```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
python main.py
```

### 2. Start Frontend
```bash
cd app_frontend
flutter run -d chrome --web-port 8081
```

### 3. Test Voice Pipeline

1. **Click the microphone button** to start recording
2. **Speak clearly** in Kannada, Hindi, or English:
   - Example (Kannada): "ನನ್ನ ಪ್ರದೇಶದಲ್ಲಿ ಕಸ ಸಂಗ್ರಹಣೆ ಆಗುತ್ತಿಲ್ಲ"
   - Example (Hindi): "मेरे क्षेत्र में कचरा संग्रह नहीं हो रहा है"
   - Example (English): "Garbage is not being collected in my area"
3. **Click stop** to end recording
4. **Observe**:
   - Your transcript appears in a citizen bubble
   - AI response appears in an AI bubble
   - Verification buttons appear (CORRECT/PARTIAL/INCORRECT)
5. **Click a verification button** to confirm or correct

---

## 📁 Project Structure

```
samvaad-setu/
├── backend/                       # Python FastAPI backend
│   ├── main.py                   # FastAPI + WebSocket voice pipeline
│   ├── config.py                 # Pydantic settings (reads .env)
│   ├── db.py                     # Async SQLAlchemy engine + session factory
│   ├── requirements.txt          # Python dependencies
│   ├── .env                      # Environment variables (create from .env.example)
│   ├── alembic.ini               # Database migration config
│   ├── migrations/               # Alembic migrations for audit + feedback tables
│   ├── middleware/
│   │   └── latency.py            # Per-stage latency tracking (p50/p95)
│   ├── models/
│   │   ├── session_model.py      # Session state + turns + confidence
│   │   └── audit_model.py        # SQLAlchemy ORM: AuditLog, VerifiedInteraction
│   ├── data/                     # Static data (JSON)
│   │   ├── dialect_profiles.json # 9 Karnataka district dialect profiles
│   │   ├── karnataka_grievance_taxonomy.json # 30+ intent categories
│   │   └── verification_phrasings.json # Dialect-conditioned rephrasings
│   ├── services/
│   │   ├── asr.py               # Sarvam AI speech-to-text
│   │   ├── tts.py               # Sarvam AI text-to-speech (with local fallback)
│   │   ├── nlu.py               # Google Gemini NLU (intent extraction)
│   │   ├── prosody.py           # Librosa-based pitch/energy/rate features
│   │   ├── sentiment.py         # Text-based sentiment + multi-modal fusion
│   │   ├── dialect_context.py   # District → dialect profile mapping
│   │   ├── verification_engine.py # Restate + 3-state confirmation loop
│   │   ├── confidence_scorer.py # Composite confidence (ASR+entropy+sentiment+clarif)
│   │   ├── intent_taxonomy.py   # Constrained intent validation + escalation priority
│   │   ├── escalation.py        # Escalation rules engine
│   │   ├── audit_log.py         # Fire-and-forget DB writes (every state transition)
│   │   ├── feedback_loop.py     # Verified interactions export (JSONL for retraining)
│   │   ├── pii_redactor.py      # Redact PII before LLM calls (phone, Aadhaar, names)
│   │   ├── session_manager.py   # Redis session CRUD
│   │   └── agent_queue.py       # Priority queue for escalations + agent WebSocket registry
│   └── tests/                    # Unit tests for all services
│       ├── test_verification_engine.py
│       ├── test_confidence_scorer.py
│       ├── test_dialect_context.py
│       ├── test_sentiment_prosody.py
│       ├── test_intent_taxonomy.py
│       ├── test_audit_feedback.py
│       ├── test_pii_redactor.py
│       ├── test_latency.py
│       └── test_agent_dashboard.py
│
├── app_frontend/                 # Flutter frontend
│   ├── lib/
│   │   ├── main.dart            # App entry point
│   │   ├── config/
│   │   │   └── app_config.dart  # Backend URL configuration
│   │   ├── models/
│   │   │   └── session_models.dart # Data models
│   │   ├── screens/
│   │   │   ├── home_screen.dart # Main citizen call interface
│   │   │   └── agent_dashboard.dart # Agent queue + live correction
│   │   ├── services/
│   │   │   └── voice_pipeline_service.dart # WebSocket client
│   │   ├── theme/
│   │   │   └── app_theme.dart   # UI theme
│   │   └── widgets/
│   │       ├── call_header_bar.dart
│   │       ├── live_chat_bubble.dart
│   │       ├── live_mic_button.dart
│   │       ├── ai_interpretation_panel.dart
│   │       ├── confidence_gauge.dart # Real-time confidence visualization
│   │       ├── sentiment_timeline.dart # Rolling sentiment chart
│   │       └── escalation_card.dart
│   ├── pubspec.yaml             # Flutter dependencies
│   └── web/                     # Web-specific files
│
├── docker-compose.yml           # One-command start: backend + Redis + Postgres + frontend
├── README.md                    # This file
├── CLAUDE.md                    # Architecture + implementation guide
├── DEMO.md                      # Judge-facing demo walkthrough
└── API_INTEGRATION_FIXES.md     # API integration notes
```

---

### 🔑 API Keys Setup

You must obtain the following API keys before running the backend:

**Sarvam AI API Key** (for ASR & TTS: speech recognition and synthesis)
1. Visit [Sarvam AI](https://www.sarvam.ai/)
2. Sign up for an account
3. Navigate to API Keys section
4. Generate and copy your key to `.env` → `SARVAM_API_KEY`

**Google Gemini API Key** (for NLU: intent extraction and understanding)
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy and paste into `.env` → `GEMINI_API_KEY`

Alternatively, set `ENVIRONMENT=mock` in `.env` to run without real API keys — all AI services return plausible fake data with realistic latency simulation.

---

## ✅ Implemented Features

### Core Voice Pipeline
- ✅ **ASR** — Sarvam AI speech-to-text with per-token confidence scoring
- ✅ **Prosodic Analysis** — Pitch variance, energy, speaking rate via librosa
- ✅ **Dialect-Aware NLU** — Gemini-powered intent extraction conditioned on district dialect profiles
- ✅ **Multi-Modal Sentiment** — Text + prosodic fusion for distress detection
- ✅ **Verification Loop** — Restate citizen issue → 3-state confirmation (correct/partial/incorrect)
- ✅ **Confidence Scoring** — Composite score: ASR + intent entropy + sentiment + clarification count
- ✅ **Escalation Engine** — Route based on confidence thresholds, distress signals, repeated failures
- ✅ **TTS** — Sarvam AI + local fallback (Coqui)
- ✅ **Audit Trail** — Every state transition logged to PostgreSQL

### Dialect Handling
- ✅ **9 District Profiles** — Bengaluru Urban/Rural, Mysuru, Mangaluru (Tulu coast), Udupi, Hubballi-Dharwad, Belagavi, Kalaburagi, Vijayapura
- ✅ **Vocabulary Hints** — 20–40 dialect terms per district with standard equivalents
- ✅ **Code-Mixing Patterns** — Englsh, Hindi, Urdu influences per region
- ✅ **Dialect-Conditioned Rephrasings** — Verification prompts use local idiom + formality register

### Grievance Taxonomy
- ✅ **30+ Intent Categories** — Derived from Sevasindhu / Janasevaka (water, ration, property tax, electricity, road, health, police, etc.)
- ✅ **Multi-Lingual Labels** — Kannada, Hindi, English
- ✅ **Escalation Priority** — 5-level priority (1 = emergency, 5 = routine)
- ✅ **Always-Escalate Intents** — Distress, women's safety, food adulteration, hospital complaints
- ✅ **Responsible Department Mapping** — Automatic routing hint

### Privacy & Data Protection
- ✅ **PII Redaction** — Phone numbers, Aadhaar, names, addresses masked before LLM calls
- ✅ **Configurable Audio Retention** — Default 0 hours (not persisted); encrypted when retained
- ✅ **Audit Immutability** — Every action logged with actor + timestamp
- ✅ **Verified Interactions Export** — JSONL corpus for retraining

### Observability
- ✅ **Per-Stage Latency Tracking** — p50/p95 milliseconds for ASR, NLU, TTS, etc. via `/health/latency`
- ✅ **Rolling Buffer** — Last 200 samples per stage; ~5 min history
- ✅ **Audit Trail REST API** — Fetch full transaction history per session
- ✅ **Mock Mode** — No API keys required; realistic latency simulation

### Agent Dashboard (Backend)
- ✅ **Priority Queue** — Escalations sorted by sentiment intensity DESC, created_at ASC
- ✅ **Real-Time Notifications** — Agent WebSocket registry + broadcast on new escalation
- ✅ **Full-Context Endpoint** — Transcript, confidence, sentiment timeline, audit summary
- ✅ **Live Corrections** — Agent can correct intent → propagates to feedback loop
- ✅ **Session Resolution** — Mark escalated session as handled

### Testing
- ✅ **Unit Tests** — 8 comprehensive test suites covering all new services
- ✅ **Mock DB** — In-memory SQLite for testing without PostgreSQL
- ✅ **Fixtures** — Pre-recorded fixture audio paths for demo-day fallback

---

## 🐛 Troubleshooting

### Backend Issues

**Problem: PostgreSQL connection failed**
```bash
# Check if PostgreSQL is running
psql --version

# Verify database exists
psql -l | grep samvaad_setu

# If database missing, create it:
psql -c "CREATE DATABASE samvaad_setu;"

# Run migrations
cd backend
alembic upgrade head
```

**Problem: Redis connection failed**
```bash
# Check if Redis is running
redis-cli ping
# Should return: PONG

# If not running, start Redis
brew services start redis  # macOS
sudo systemctl start redis # Linux
```

**Problem: Alembic migration errors**
```bash
# Check migration status
alembic current

# If stuck, reset (DEV ONLY):
alembic downgrade base
alembic upgrade head
```

**Problem: Import errors for new services**
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies (includes librosa, sqlalchemy-asyncpg)
pip install -r requirements.txt --upgrade
```

**Problem: API key errors or rate-limiting**
```bash
# If using real API keys, switch to mock mode for testing
# Edit .env: ENVIRONMENT=mock
# All services return realistic fake data

# For rate limits on production, the backend has graceful degradation:
# - Sarvam ASR down → fallback to Whisper
# - Gemini rate-limited → fallback to rule-based intent classifier
# - Sarvam TTS down → fallback to local TTS
```

**Problem: Librosa not installed (prosody module)**
```bash
# prosody.py gates itself behind ENABLE_PROSODY flag
# If librosa is missing, features fall back to neutral values
# To enable, install: apt-get install libsndfile1
pip install librosa soundfile
```

**Problem: PII redaction not working**
```bash
# Verify feature flag in .env
grep PII_REDACTION_ENABLED .env
# Should be: PII_REDACTION_ENABLED=true

# For testing, set to false to see original text
```

### Frontend Issues

**Problem: Flutter not found**
```bash
# Install Flutter: https://docs.flutter.dev/get-started/install
flutter doctor
```

**Problem: Dependencies not installed**
```bash
flutter clean
flutter pub get
```

**Problem: WebSocket connection fails**
- Ensure backend is running on `http://localhost:8000`
- Verify CORS_ORIGINS in backend `.env` includes frontend URL
- Check `/health` endpoint responds
- Browser console (F12) will show WebSocket errors

**Problem: Audio recording not working**
- Grant microphone permissions in browser
- Use Chrome/Edge (Edge has best WebRTC support)
- Firefox also works (check permissions → Use microphone)
- Safari WebSocket is limited; use Chrome for best results

**Problem: ASR/TTS latency issues**
- Check `/health/latency` to see per-stage bottlenecks
- Sarvam API rate limits may cause longer waits
- In mock mode, latencies are simulated (helpful for UX testing)

---

## 📊 Monitoring & Logs

### Backend Latency Dashboard

```bash
# Real-time per-stage latency (p50/p95 ms):
curl http://localhost:8000/health/latency | jq

# Example output:
{
  "stages": {
    "asr": {
      "p50_ms": 287.3,
      "p95_ms": 412.1,
      "min_ms": 203.5,
      "max_ms": 518.0,
      "samples": 42
    },
    "nlu": {
      "p50_ms": 421.8,
      "p95_ms": 687.2,
      ...
    }
  }
}
```

### Audit Trail

```bash
# Fetch full audit log for a session:
curl http://localhost:8000/audit/{session_id} | jq

# Returns: array of audit events with timestamps, actors, and payloads
```

### Agent Queue

```bash
# Check escalation queue (highest priority first):
curl http://localhost:8000/agent/queue | jq

# Returns: list of escalated sessions with sentiment, reason, summary
```

### Backend Logs

The backend provides structured logging:

### Backend Logs

The backend provides structured logging:

```bash
# Watch logs in real-time
python main.py

# Key log prefixes:
# [WS] - WebSocket life cycle
# [AUDIO] - Audio stream processing
# [ASR] - Speech recognition responses
# [NLU] - Intent extraction results
# [SENTIMENT] - Sentiment analysis signals
# [VERIFICATION] - Rephrasing + confirmation flow
# [AUDIT] - Database write results
# [ESCALATION] - Escalation decisions and triggers
# [TTS] - Text-to-speech output
# [LATENCY] - Per-stage timing (when LATENCY_LOGGING=true)
```

### Frontend Logs

```bash
# Run with verbose logging
flutter run -d chrome --web-port 8081 -v

# Monitor in browser console (F12):
# [WS] - WebSocket messages
# [AUDIO] - Recording/playback state
# [UI] - State transitions
# [API] - HTTP request/response
```

### Exporting Training Data

```bash
# Export verified interactions as JSONL (for retraining):
curl 'http://localhost:8000/training-data/export?format=jsonl&since=2026-05-01' \
  | head -10 | jq

# Returns: newline-delimited JSON, one verified interaction per line
# Each row includes: asr_text, intent, agent_corrections, final_intent, etc.

# Save to file for use in fine-tuning NLU models
curl 'http://localhost:8000/training-data/export?format=jsonl' > feedback_corpus.jsonl
```

---

## 🐳 Docker Deployment

### One-Command Start (Recommended)

```bash
# Builds and runs backend + Redis + Postgres + frontend on shared network
docker-compose up

# Stops all services
docker-compose down

# Services available:
# Frontend: http://localhost:8081
# Backend:  http://localhost:8000
# Redis:    localhost:6379
# Postgres: localhost:5432
```

### Manual Backend Deployment

```bash
cd backend
docker build -t samvaad-setu-backend .
docker run -p 8000:8000 --env-file .env \
  --network samvaad-net \
  -e REDIS_HOST=redis \
  -e POSTGRES_URL=postgresql://postgres:password@postgres:5432/samvaad_setu \
  samvaad-setu-backend
```

### Frontend Deployment (Web)

```bash
cd app_frontend
flutter build web --release
# Deploy the build/web directory to your hosting service
```

---

## 🧪 Running Unit Tests

```bash
# Test all new services
cd backend
pytest tests/ -v

# Test a specific module
pytest tests/test_confidence_scorer.py -v

# Run with coverage
pytest tests/ --cov=services --cov-report=html
open htmlcov/index.html
```

Key test files:
- `test_verification_engine.py` — Restate + 3-state confirmation
- `test_confidence_scorer.py` — Composite scoring logic
- `test_dialect_context.py` — Dialect-conditioned rephrasings
- `test_sentiment_prosody.py` — Multi-modal fusion
- `test_intent_taxonomy.py` — Intent validation
- `test_audit_feedback.py` — DB persistence and JSONL export
- `test_pii_redactor.py` — PII pattern matching
- `test_latency.py` — Per-stage timing
- `test_agent_dashboard.py` — Queue ordering and agent endpoints

---

## 📚 Additional Documentation

- **[CLAUDE.md](./CLAUDE.md)** — Architecture, implementation prompts, API reference
- **[SETUP_GUIDE.md](./SETUP_GUIDE.md)** — Detailed setup instructions
- **[TESTING_GUIDE.md](./TESTING_GUIDE.md)** — Testing procedures and fixtures
- **[DEMO.md](./DEMO.md)** — Judge-facing demo walkthrough
- **Swagger UI** — Interactive API docs at `http://localhost:8000/docs`

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🙏 Acknowledgments

- **Sarvam AI** — Best-in-class Kannada/Hindi/English ASR and TTS
- **Google Gemini** — Multilingual reasoning for intent extraction
- **librosa** — Prosodic feature extraction
- **Karnataka Government** — 1092 helpline initiative
- **Sevasindhu & Janasevaka** — Grievance taxonomy reference

---

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Check the troubleshooting section above
- Review [CLAUDE.md](./CLAUDE.md) for architecture details
- Email: support@samvaad-setu.com

---

**Built with ❤️ for Karnataka's citizens — Multilingual, Dialect-Aware, Distress-Sensitive**
