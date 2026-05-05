import 'package:flutter/material.dart';
import '../models/session_models.dart';
import 'confidence_gauge.dart';
import 'sentiment_timeline.dart';
import 'ai_interpretation_panel.dart';
import 'escalation_card.dart';

class AgentDashboardTab extends StatelessWidget {
  final SessionMeta? sessionMeta;
  final NluResult? nluResult;
  final EscalationPacket? escalationPacket;

  const AgentDashboardTab({
    Key? key,
    this.sessionMeta,
    this.nluResult,
    this.escalationPacket,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (escalationPacket != null) ...[
            EscalationCard(packet: escalationPacket!),
            const SizedBox(height: 16),
          ],
          
          // Gauges Section
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFFEDEAF6)),
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFF826695).withOpacity(0.05),
                  blurRadius: 10,
                  offset: const Offset(0, 4),
                )
              ],
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                ConfidenceGauge(
                  score: sessionMeta?.compositeConfidence ?? 1.0,
                  label: 'Composite',
                  size: 80,
                ),
                ConfidenceGauge(
                  score: nluResult?.intentConfidence ?? 1.0,
                  label: 'Intent',
                  size: 80,
                ),
                ConfidenceGauge(
                  score: sessionMeta != null ? 1.0 - (sessionMeta!.clarificationCount / 3).clamp(0.0, 1.0) : 1.0,
                  label: 'Clarity',
                  size: 80,
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // AI Interpretation Panel
          AiInterpretationPanel(
            nluResult: nluResult,
            escalationPacket: escalationPacket,
            onSave: (editedText) {
              // TODO: Send to backend for training
              print("Saved: $editedText");
            },
          ),
          const SizedBox(height: 16),

          // Sentiment Timeline
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFFEDEAF6)),
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFF826695).withOpacity(0.05),
                  blurRadius: 10,
                  offset: const Offset(0, 4),
                )
              ],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'SENTIMENT TIMELINE',
                  style: TextStyle(
                    color: Color(0xFF826695),
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 1.2,
                  ),
                ),
                const SizedBox(height: 16),
                SentimentTimeline(timeline: sessionMeta?.sentimentTimeline ?? []),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
