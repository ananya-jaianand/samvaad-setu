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

---

## 📋 Prerequisites

### Backend Requirements
- **Python**: 3.9 or higher
- **pip**: Latest version
- **Redis**: 6.0+ (for session management)

### Frontend Requirements
- **Flutter**: 3.0.0 or higher
- **Dart**: 2.17.0 or higher
- **Chrome/Edge**: For web development

### API Keys Required
- **Sarvam AI API Key** (for ASR & TTS)
- **Google Gemini API Key** (for NLU)

---

## 🚀 Quick Start

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

Edit `.env` with your API keys:

```env
# Environment
ENVIRONMENT=production

# API Keys
SARVAM_API_KEY=your_sarvam_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here

# Sarvam Configuration
SARVAM_ASR_MODEL=saarika:v2.5
SARVAM_TTS_MODEL=bulbul:v1

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Server Configuration
CORS_ORIGINS=["http://localhost:8081","http://localhost:3000"]
MAX_CLARIFICATION_TURNS=3
```

### Step 5: Start Redis (if not running)

```bash
# On macOS (using Homebrew):
brew services start redis

# On Linux:
sudo systemctl start redis

# On Windows (using WSL or Docker):
docker run -d -p 6379:6379 redis:latest
```

### Step 6: Run the Backend Server

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
  "redis_connected": true
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
├── backend/                    # Python FastAPI backend
│   ├── main.py                # Main server entry point
│   ├── config.py              # Configuration & settings
│   ├── requirements.txt       # Python dependencies
│   ├── .env                   # Environment variables (create this)
│   ├── models/
│   │   └── session_model.py   # Data models
│   └── services/
│       ├── asr.py             # Sarvam ASR integration
│       ├── tts.py             # Sarvam TTS integration
│       ├── nlu.py             # Google Gemini NLU
│       ├── sentiment.py       # Sentiment analysis
│       ├── verification.py    # Verification logic
│       ├── escalation.py      # Escalation rules
│       └── session_manager.py # Redis session management
│
├── app_frontend/              # Flutter frontend
│   ├── lib/
│   │   ├── main.dart          # App entry point
│   │   ├── config/
│   │   │   └── app_config.dart # Backend URL configuration
│   │   ├── models/
│   │   │   └── session_models.dart # Data models
│   │   ├── screens/
│   │   │   └── home_screen.dart # Main call interface
│   │   ├── services/
│   │   │   └── voice_pipeline_service.dart # Backend communication
│   │   ├── theme/
│   │   │   └── app_theme.dart # UI theme
│   │   └── widgets/
│   │       ├── call_header_bar.dart
│   │       ├── live_chat_bubble.dart
│   │       ├── live_mic_button.dart
│   │       ├── ai_interpretation_panel.dart
│   │       ├── confidence_gauge.dart
│   │       ├── sentiment_timeline.dart
│   │       └── escalation_card.dart
│   ├── pubspec.yaml           # Flutter dependencies
│   └── web/                   # Web-specific files
│
├── README.md                  # This file
├── SETUP_GUIDE.md            # Detailed setup instructions
├── TESTING_GUIDE.md          # Testing documentation
└── API_INTEGRATION_FIXES.md  # API integration notes
```

---

## 🔑 API Keys Setup

### Getting Sarvam AI API Key

1. Visit [Sarvam AI](https://www.sarvam.ai/)
2. Sign up for an account
3. Navigate to API Keys section
4. Generate a new API key
5. Copy and paste into `.env` file

### Getting Google Gemini API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy and paste into `.env` file

---

## 🐛 Troubleshooting

### Backend Issues

**Problem: Redis connection failed**
```bash
# Check if Redis is running
redis-cli ping
# Should return: PONG

# If not running, start Redis
brew services start redis  # macOS
sudo systemctl start redis # Linux
```

**Problem: Import errors**
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

**Problem: API key errors**
```bash
# Verify .env file exists and has correct keys
cat .env | grep API_KEY
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

**Problem: WebSocket connection failed**
- Ensure backend is running on `http://localhost:8000`
- Check `lib/config/app_config.dart` has correct URLs
- Verify CORS settings in backend `.env`

**Problem: Audio recording not working**
- Grant microphone permissions in browser
- Use Chrome/Edge (Safari has limited support)
- Check browser console for errors

---

## 📊 Monitoring & Logs

### Backend Logs

The backend provides detailed logging for debugging:

```bash
# Watch logs in real-time
python main.py

# Look for these log prefixes:
# [WS] - WebSocket events
# [AUDIO] - Audio processing
# [ASR] - Speech recognition
# [NLU] - Intent extraction
# [SENTIMENT] - Sentiment analysis
# [TTS] - Text-to-speech
# [ESCALATION] - Escalation decisions
```

### Frontend Logs

```bash
# Run with verbose logging
flutter run -d chrome --web-port 8081 -v

# Check browser console (F12) for:
# [WS] - WebSocket messages
# Recording/playback events
# State changes
```

---

## 🚢 Deployment

### Backend Deployment (Docker)

```bash
cd backend
docker build -t samvaad-setu-backend .
docker run -p 8000:8000 --env-file .env samvaad-setu-backend
```

### Frontend Deployment (Web)

```bash
cd app_frontend
flutter build web --release
# Deploy the build/web directory to your hosting service
```

---

## 📚 Additional Documentation

- **[SETUP_GUIDE.md](./SETUP_GUIDE.md)** - Detailed setup instructions
- **[TESTING_GUIDE.md](./TESTING_GUIDE.md)** - Testing procedures
- **[API_INTEGRATION_FIXES.md](./API_INTEGRATION_FIXES.md)** - API integration notes
- **[GEMINI_MIGRATION.md](./GEMINI_MIGRATION.md)** - Gemini migration guide

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

- **Sarvam AI** for ASR and TTS services
- **Google Gemini** for NLU capabilities
- **Karnataka Government** for the 1092 helpline initiative

---

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Email: support@samvaad-setu.com
- Documentation: [Wiki](https://github.com/yourusername/samvaad-setu/wiki)

---

**Built with ❤️ for Karnataka's citizens**
