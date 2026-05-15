class SessionTurn {
  final String speaker; // 'citizen' | 'ai' | 'agent'
  final String rawTranscript;
  final String? aiRephrasing;
  final String? intent;
  final String? turnId;
  final String? detectedLanguage;
  final double asrConfidence;
  final String? stressLevel; // 'LOW' | 'MEDIUM' | 'HIGH'
  final String? sentimentLabel;
  final double? sentimentIntensity;
  final String? verificationState;

  SessionTurn({
    required this.speaker,
    required this.rawTranscript,
    this.aiRephrasing,
    this.intent,
    this.turnId,
    this.detectedLanguage,
    this.asrConfidence = 1.0,
    this.stressLevel,
    this.sentimentLabel,
    this.sentimentIntensity,
    this.verificationState,
  });

  factory SessionTurn.fromJson(Map<String, dynamic> json) {
    String? sentimentLabel;
    double? sentimentIntensity;
    String? stressLevel;

    if (json['sentiment'] != null && json['sentiment'] is Map) {
      final s = json['sentiment'] as Map<String, dynamic>;
      sentimentLabel = s['label'];
      // backend sends 'intensity' (TurnSentiment model), not 'score'
      sentimentIntensity = (s['intensity'] as num?)?.toDouble() ??
          (s['score'] as num?)?.toDouble();

      if (sentimentLabel != null) {
        if (sentimentLabel == 'distress' || sentimentLabel == 'anger') {
          stressLevel = 'HIGH';
        } else if (sentimentLabel == 'fear' || sentimentLabel == 'urgency') {
          stressLevel = 'MEDIUM';
        } else {
          stressLevel = 'LOW';
        }
      }
    }

    return SessionTurn(
      speaker: json['speaker'] ?? 'unknown',
      rawTranscript: json['raw_transcript'] ?? '',
      aiRephrasing: json['ai_rephrasing'],
      intent: json['intent'],
      turnId: json['turn_id'],
      detectedLanguage: json['detected_language'],
      asrConfidence: (json['asr_confidence'] as num?)?.toDouble() ?? 1.0,
      stressLevel: stressLevel,
      sentimentLabel: sentimentLabel,
      sentimentIntensity: sentimentIntensity,
      verificationState: json['verification_state'],
    );
  }

  String get displayText =>
      rawTranscript.isNotEmpty ? rawTranscript : (aiRephrasing ?? '');

  Map<String, dynamic> toAgentMap() => {
    'speaker': speaker,
    'raw_transcript': rawTranscript,
    'ai_rephrasing': aiRephrasing,
    'asr_confidence': asrConfidence,
    'verification_state': verificationState ?? 'pending',
    'intent': intent,
    'timestamp': DateTime.now().toIso8601String(),
    if (sentimentLabel != null)
      'sentiment': {'label': sentimentLabel, 'intensity': sentimentIntensity ?? 0.5},
  };
}

class VerificationPrompt {
  final String text;
  final String language;
  final String district;
  final String sessionId;

  const VerificationPrompt({
    required this.text,
    required this.language,
    required this.district,
    required this.sessionId,
  });

  factory VerificationPrompt.fromJson(Map<String, dynamic> json) {
    return VerificationPrompt(
      text: json['text'] ?? json['rephrasing'] ?? '',
      language: json['language'] ?? 'en',
      district: json['district'] ?? '',
      sessionId: json['session_id'] ?? '',
    );
  }
}

class ConfidenceScore {
  final double asrConfidence;
  final double intentEntropy;
  final double sentimentIntensity;
  final int clarificationCount;
  final double compositeScore;

  const ConfidenceScore({
    required this.asrConfidence,
    required this.intentEntropy,
    required this.sentimentIntensity,
    required this.clarificationCount,
    required this.compositeScore,
  });

  factory ConfidenceScore.fromJson(Map<String, dynamic> json) {
    return ConfidenceScore(
      asrConfidence: (json['asr_confidence'] as num?)?.toDouble() ?? 1.0,
      intentEntropy: (json['intent_entropy'] as num?)?.toDouble() ?? 0.0,
      sentimentIntensity: (json['sentiment_intensity'] as num?)?.toDouble() ?? 0.0,
      clarificationCount: json['clarification_count'] ?? 0,
      compositeScore: (json['composite_score'] as num?)?.toDouble() ?? 1.0,
    );
  }
}

class EscalationPacket {
  final String sessionId;
  final String reason;
  final String summary;
  final String district;
  final String detectedLanguage;
  final String? finalIntent;
  final double compositeConfidence;
  final String? escalationMessage;

  EscalationPacket({
    required this.sessionId,
    required this.reason,
    required this.summary,
    required this.district,
    required this.detectedLanguage,
    this.finalIntent,
    this.compositeConfidence = 0.0,
    this.escalationMessage,
  });

  factory EscalationPacket.fromJson(Map<String, dynamic> json) {
    return EscalationPacket(
      sessionId: json['session_id'] ?? '',
      reason: json['reason'] ?? '',
      summary: json['summary'] ?? '',
      district: json['district'] ?? '',
      detectedLanguage: json['detected_language'] ?? '',
      finalIntent: json['final_intent'],
      compositeConfidence:
          (json['composite_confidence'] as num?)?.toDouble() ?? 0.0,
      escalationMessage: json['escalation_message'],
    );
  }
}

class SentimentEntry {
  final String label;
  final double intensity;
  final String timestamp;

  SentimentEntry({
    required this.label,
    required this.intensity,
    required this.timestamp,
  });

  factory SentimentEntry.fromJson(Map<String, dynamic> json) {
    return SentimentEntry(
      label: json['label'] ?? 'calm',
      intensity: (json['intensity'] as num?)?.toDouble() ??
          (json['score'] as num?)?.toDouble() ??
          0.5,
      timestamp: json['timestamp'] ?? DateTime.now().toIso8601String(),
    );
  }
}

class SessionMeta {
  final double compositeConfidence;
  final int clarificationCount;
  final List<SentimentEntry> sentimentTimeline;
  final String? currentLanguage;
  final String? currentDialect;
  final String? currentSentiment;
  final String sessionId;
  final String district;
  final String verificationState;
  final bool isEscalated;

  SessionMeta({
    required this.compositeConfidence,
    required this.clarificationCount,
    required this.sentimentTimeline,
    this.currentLanguage,
    this.currentDialect,
    this.currentSentiment,
    this.sessionId = '',
    this.district = '',
    this.verificationState = 'pending',
    this.isEscalated = false,
  });

  factory SessionMeta.fromJson(Map<String, dynamic> json) {
    return SessionMeta(
      compositeConfidence:
          (json['composite_confidence'] as num?)?.toDouble() ?? 1.0,
      clarificationCount: json['clarification_count'] ?? 0,
      sentimentTimeline: (json['sentiment_timeline'] as List<dynamic>?)
              ?.map((e) => SentimentEntry.fromJson(e))
              .toList() ??
          [],
      currentLanguage: json['current_language'],
      currentDialect: json['current_dialect'],
      currentSentiment: json['current_sentiment'],
      sessionId: json['session_id'] ?? '',
      district: json['district'] ?? '',
      verificationState: json['verification_state'] ?? 'pending',
      isEscalated: json['is_escalated'] ?? false,
    );
  }
}

class NluResult {
  final String? intent;
  final double intentConfidence;
  final Map<String, dynamic>? structuredSummary;

  NluResult({
    this.intent,
    required this.intentConfidence,
    this.structuredSummary,
  });

  factory NluResult.fromJson(Map<String, dynamic> json) {
    return NluResult(
      intent: json['intent'],
      intentConfidence:
          (json['intent_confidence'] as num?)?.toDouble() ?? 1.0,
      structuredSummary: json['structured_summary'],
    );
  }
}

class AgentQueueItem {
  final String sessionId;
  final String district;
  final String language;
  final String sentiment;
  final double sentimentIntensity;
  final String reason;
  final String summary;
  final String? finalIntent;
  final String createdAt;

  const AgentQueueItem({
    required this.sessionId,
    required this.district,
    required this.language,
    required this.sentiment,
    required this.sentimentIntensity,
    required this.reason,
    required this.summary,
    this.finalIntent,
    required this.createdAt,
  });

  factory AgentQueueItem.fromJson(Map<String, dynamic> json) {
    return AgentQueueItem(
      sessionId: json['session_id'] ?? '',
      district: json['district'] ?? '',
      language: json['language'] ?? 'kn',
      sentiment: json['sentiment'] ?? 'calm',
      sentimentIntensity:
          (json['sentiment_intensity'] as num?)?.toDouble() ?? 0.5,
      reason: json['reason'] ?? '',
      summary: json['summary'] ?? '',
      finalIntent: json['final_intent'],
      createdAt: json['created_at'] ?? '',
    );
  }

  String get priorityLabel {
    if (sentiment == 'distress' || sentiment == 'anger') return 'high';
    if (sentimentIntensity > 0.5) return 'med';
    return 'low';
  }
}
