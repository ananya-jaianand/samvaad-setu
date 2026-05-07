from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
import uuid

SentimentClass = Literal["distress", "anger", "fear", "urgency", "confusion", "calm"]
VerificationState = Literal["correct", "partially_correct", "incorrect", "pending"]
SessionVerificationState = Literal["pending", "confirmed", "partial", "rejected", "escalated"]
EscalationReason = Literal[
    "high_distress", "low_asr_confidence", "high_intent_entropy",
    "low_confidence", "repeated_clarification", "explicit_request", "none"
]

class TurnSentiment(BaseModel):
    label: SentimentClass
    intensity: float                 # 0–1, dominant emotion intensity
    prosodic_component: float = 0.0
    text_component: float = 0.0

class Turn(BaseModel):
    turn_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    speaker: Literal["citizen", "ai", "agent"]
    raw_transcript: str = ""
    asr_confidence: float = 1.0
    detected_language: str = "kn"
    intent: Optional[str] = None
    intent_entropy: float = 0.0
    sentiment: Optional[TurnSentiment] = None
    ai_rephrasing: str = ""
    verification_state: VerificationState = "pending"
    tts_audio_b64: str = ""         # base64 audio for playback

class SessionState(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    district: str = "default"
    detected_language: str = "kn"
    dialect_tag: Optional[str] = None          # populated from dialect_context on first audio turn
    turns: list[Turn] = []
    verification_state: SessionVerificationState = "pending"
    clarification_count: int = 0
    is_escalated: bool = False
    escalation_reason: EscalationReason = "none"
    escalation_summary: str = ""               # one-line context for human agent
    final_intent: Optional[str] = None
    composite_confidence: float = 1.0
    is_resolved: bool = False                  # set by agent via POST /sessions/{id}/resolve

    # Running timelines (for agent dashboard)
    sentiment_timeline: list[dict] = []
    confidence_history: list[dict] = []        # per-turn composite score breakdown

    def add_turn(self, turn: Turn):
        self.turns.append(turn)
        if turn.sentiment:
            self.sentiment_timeline.append({
                "turn_id": turn.turn_id,
                "timestamp": turn.timestamp.isoformat(),
                "label": turn.sentiment.label,
                "intensity": turn.sentiment.intensity,
                "prosodic_component": turn.sentiment.prosodic_component,
                "text_component": turn.sentiment.text_component,
            })
            # Cap at last 20 entries to bound memory and WebSocket payload size
            if len(self.sentiment_timeline) > 20:
                self.sentiment_timeline = self.sentiment_timeline[-20:]

    def citizen_turns(self) -> list[Turn]:
        return [t for t in self.turns if t.speaker == "citizen"]

    def to_transcript_text(self) -> str:
        lines = []
        for t in self.turns:
            prefix = {"citizen": "🧑 Citizen", "ai": "🤖 AI", "agent": "👤 Agent"}[t.speaker]
            lines.append(f"[{t.timestamp.strftime('%H:%M:%S')}] {prefix}: {t.raw_transcript or t.ai_rephrasing}")
        return "\n".join(lines)

class EscalationPacket(BaseModel):
    """Sent to agent dashboard on escalation."""
    session_id: str
    reason: EscalationReason
    summary: str
    district: str
    detected_language: str
    final_intent: Optional[str]
    composite_confidence: float
    transcript: str
    sentiment_timeline: list[dict]
    ai_interpretation: str
    ticket_draft: dict               # structured for 1092 intake form
