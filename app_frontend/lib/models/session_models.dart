class SessionTurn {
  final String speaker; // 'citizen' or 'ai'
  final String rawTranscript;
  final String? intent;
  final String? aiRephrasing;
  final String? turnId;
  final String? detectedLanguage;
  final String? translation;
  final String? stressLevel; // 'LOW', 'MEDIUM', 'HIGH'
  final String? sentimentLabel;
  final double? sentimentScore;

  SessionTurn({
    required this.speaker,
    required this.rawTranscript,
    this.intent,
    this.aiRephrasing,
    this.turnId,
    this.detectedLanguage,
    this.translation,
    this.stressLevel,
    this.sentimentLabel,
    this.sentimentScore,
  });

  factory SessionTurn.fromJson(Map<String, dynamic> json) {
    // Extract sentiment from nested structure
    String? sentimentLabel;
    double? sentimentScore;
    String? stressLevel;
    
    if (json['sentiment'] != null && json['sentiment'] is Map) {
      final sentiment = json['sentiment'] as Map<String, dynamic>;
      sentimentLabel = sentiment['label'];
      sentimentScore = (sentiment['score'] as num?)?.toDouble();
      
      // Map sentiment label to stress level
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
      intent: json['intent'],
      aiRephrasing: json['ai_rephrasing'],
      turnId: json['turn_id'],
      detectedLanguage: json['detected_language'],
      translation: json['translation'],
      stressLevel: stressLevel,
      sentimentLabel: sentimentLabel,
      sentimentScore: sentimentScore,
    );
  }
}

class MatchedAgent {
  final String initials;
  final String name;
  final String agentId;
  final String scheme;
  final String status;
  final double confidence;

  MatchedAgent({
    required this.initials,
    required this.name,
    required this.agentId,
    required this.scheme,
    required this.status,
    required this.confidence,
  });

  factory MatchedAgent.fromJson(Map<String, dynamic> json) {
    return MatchedAgent(
      initials: json['initials'] ?? 'XX',
      name: json['name'] ?? 'Agent',
      agentId: json['agent_id'] ?? '',
      scheme: json['scheme'] ?? '',
      status: json['status'] ?? 'Active',
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.9,
    );
  }
}

class EscalationPacket {
  final String sessionId;
  final String reason;
  final String summary;
  final String district;
  final String detectedLanguage;
  final String ticketDraft;
  final MatchedAgent? matchedAgent;

  EscalationPacket({
    required this.sessionId,
    required this.reason,
    required this.summary,
    required this.district,
    required this.detectedLanguage,
    required this.ticketDraft,
    this.matchedAgent,
  });

  factory EscalationPacket.fromJson(Map<String, dynamic> json) {
    // Handle ticket_draft as either string or map
    String ticketDraftStr = '';
    if (json['ticket_draft'] is String) {
      ticketDraftStr = json['ticket_draft'];
    } else if (json['ticket_draft'] is Map) {
      ticketDraftStr = json['ticket_draft'].toString();
    }

    return EscalationPacket(
      sessionId: json['session_id'] ?? '',
      reason: json['reason'] ?? '',
      summary: json['summary'] ?? '',
      district: json['district'] ?? '',
      detectedLanguage: json['detected_language'] ?? '',
      ticketDraft: ticketDraftStr,
      matchedAgent: json['matched_agent'] != null
          ? MatchedAgent.fromJson(json['matched_agent'])
          : null,
    );
  }
}

class SentimentEntry {
  final String label;
  final double score;
  final String timestamp;

  SentimentEntry({
    required this.label,
    required this.score,
    required this.timestamp,
  });

  factory SentimentEntry.fromJson(Map<String, dynamic> json) {
    return SentimentEntry(
      label: json['label'] ?? 'calm',
      score: (json['score'] as num?)?.toDouble() ?? 1.0,
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
  final String callId;
  final String callDuration;

  SessionMeta({
    required this.compositeConfidence,
    required this.clarificationCount,
    required this.sentimentTimeline,
    this.currentLanguage,
    this.currentDialect,
    this.currentSentiment,
    this.callId = 'IN-8472',
    this.callDuration = '00:00',
  });

  factory SessionMeta.fromJson(Map<String, dynamic> json) {
    return SessionMeta(
      compositeConfidence: (json['composite_confidence'] as num?)?.toDouble() ?? 1.0,
      clarificationCount: json['clarification_count'] ?? 0,
      sentimentTimeline: (json['sentiment_timeline'] as List<dynamic>?)
              ?.map((e) => SentimentEntry.fromJson(e))
              .toList() ??
          [],
      currentLanguage: json['current_language'],
      currentDialect: json['current_dialect'],
      currentSentiment: json['current_sentiment'],
      callId: json['call_id'] ?? 'IN-8472',
      callDuration: json['call_duration'] ?? '00:00',
    );
  }
}

class NluResult {
  final String? intent;
  final double intentConfidence;
  final Map<String, dynamic>? structuredSummary;
  final String? aiSummary;

  NluResult({
    this.intent,
    required this.intentConfidence,
    this.structuredSummary,
    this.aiSummary,
  });

  factory NluResult.fromJson(Map<String, dynamic> json) {
    return NluResult(
      intent: json['intent'],
      intentConfidence: (json['intent_confidence'] as num?)?.toDouble() ?? 1.0,
      structuredSummary: json['structured_summary'],
      aiSummary: json['ai_summary'],
    );
  }
}
