import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../services/voice_pipeline_service.dart';
import '../models/session_models.dart';
import '../widgets/call_header_bar.dart';
import '../widgets/live_chat_bubble.dart';
import '../widgets/live_mic_button.dart';
import '../widgets/ai_interpretation_panel.dart';
import '../widgets/confidence_gauge.dart';
import '../widgets/sentiment_timeline.dart';
import '../widgets/escalation_card.dart';
import '../widgets/status_banner.dart';

class CallDetailScreen extends StatefulWidget {
  const CallDetailScreen({super.key});

  @override
  State<CallDetailScreen> createState() => _CallDetailScreenState();
}

class _CallDetailScreenState extends State<CallDetailScreen> {
  final VoicePipelineService _pipelineService = VoicePipelineService();
  final ScrollController _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    // Auto-start session
    Future.delayed(const Duration(milliseconds: 500), () {
      _pipelineService.startSession();
    });
  }

  @override
  void dispose() {
    _pipelineService.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    if (_scrollController.hasClients) {
      Future.delayed(const Duration(milliseconds: 100), () {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F5F7),
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.menu, color: Color(0xFF2D223A)),
          onPressed: () {},
        ),
        title: const Text(
          'Samvaad-Setu',
          style: TextStyle(
            color: Color(0xFF2D223A),
            fontSize: 18,
            fontWeight: FontWeight.w600,
          ),
        ),
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.person_outline, color: Color(0xFF2D223A)),
            onPressed: () {},
          ),
        ],
      ),
      body: Column(
        children: [
          // Call Header Bar
          StreamBuilder<SessionMeta?>(
            stream: _pipelineService.sessionMetaStream,
            builder: (context, snapshot) {
              final meta = snapshot.data;
              return CallHeaderBar(
                callId: meta?.callId ?? 'CALL ID: N-8472',
                duration: meta?.callDuration ?? '04:12',
                language: meta?.currentLanguage ?? 'HINDI',
                matchCode: '04-12',
              );
            },
          ),

          // Status Banner (AI Actively Listening)
          StreamBuilder<PipelineState>(
            stream: _pipelineService.stateStream,
            builder: (context, snapshot) {
              final state = snapshot.data ?? PipelineState.idle;
              if (state == PipelineState.listening || state == PipelineState.processing) {
                return StatusBanner(
                  text: state == PipelineState.listening
                      ? 'AI IS ACTIVELY LISTENING'
                      : 'PROCESSING...',
                  subtitle: 'Speak now, the AI will transcribe and respond automatically',
                );
              }
              return const SizedBox.shrink();
            },
          ),

          // Chat Messages
          Expanded(
            child: StreamBuilder<List<SessionTurn>>(
              stream: _pipelineService.turnsStream,
              builder: (context, snapshot) {
                final turns = snapshot.data ?? [];
                WidgetsBinding.instance.addPostFrameCallback((_) => _scrollToBottom());

                return ListView.builder(
                  controller: _scrollController,
                  padding: const EdgeInsets.all(16),
                  itemCount: turns.length,
                  itemBuilder: (context, index) {
                    return LiveChatBubble(turn: turns[index]);
                  },
                );
              },
            ),
          ),

          // Mic Button
          Container(
            padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 24),
            decoration: BoxDecoration(
              color: Colors.white,
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.05),
                  blurRadius: 10,
                  offset: const Offset(0, -2),
                ),
              ],
            ),
            child: SafeArea(
              top: false,
              child: StreamBuilder<PipelineState>(
                stream: _pipelineService.stateStream,
                builder: (context, snapshot) {
                  final state = snapshot.data ?? PipelineState.idle;
                  return LiveMicButton(
                    state: state,
                    onStartRecord: () => _pipelineService.startRecording(),
                    onStopRecord: () => _pipelineService.stopRecording(),
                  );
                },
              ),
            ),
          ),

          // AI Interpretation Panel
          StreamBuilder<NluResult?>(
            stream: _pipelineService.nluResultStream,
            builder: (context, nluSnapshot) {
              return StreamBuilder<SessionMeta?>(
                stream: _pipelineService.sessionMetaStream,
                builder: (context, metaSnapshot) {
                  return StreamBuilder<EscalationPacket?>(
                    stream: _pipelineService.escalationStream,
                    builder: (context, escSnapshot) {
                      final nlu = nluSnapshot.data;
                      final meta = metaSnapshot.data;
                      final esc = escSnapshot.data;

                      if (nlu == null && esc == null) return const SizedBox.shrink();

                      return Container(
                        decoration: BoxDecoration(
                          color: Colors.white,
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withOpacity(0.1),
                              blurRadius: 20,
                              offset: const Offset(0, -4),
                            ),
                          ],
                        ),
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            // AI Voice Modulation
                            Container(
                              padding: const EdgeInsets.all(16),
                              decoration: const BoxDecoration(
                                border: Border(
                                  bottom: BorderSide(color: Color(0xFFEDEAF6)),
                                ),
                              ),
                              child: Row(
                                children: [
                                  const Icon(Icons.graphic_eq, size: 20, color: Color(0xFF826695)),
                                  const SizedBox(width: 8),
                                  const Text(
                                    'AI VOICE MODULATION',
                                    style: TextStyle(
                                      fontSize: 12,
                                      fontWeight: FontWeight.w600,
                                      color: Color(0xFF826695),
                                    ),
                                  ),
                                  const Spacer(),
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                    decoration: BoxDecoration(
                                      color: const Color(0xFF826695).withOpacity(0.1),
                                      borderRadius: BorderRadius.circular(4),
                                    ),
                                    child: Text(
                                      meta?.currentSentiment ?? 'Emotional Tone',
                                      style: const TextStyle(
                                        fontSize: 11,
                                        fontWeight: FontWeight.w600,
                                        color: Color(0xFF826695),
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),

                            // Sentiment & Confidence
                            Padding(
                              padding: const EdgeInsets.all(16),
                              child: Row(
                                children: [
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        const Text(
                                          'AI CONFIDENCE',
                                          style: TextStyle(
                                            fontSize: 11,
                                            fontWeight: FontWeight.w600,
                                            color: Color(0xFF9E9E9E),
                                          ),
                                        ),
                                        const SizedBox(height: 8),
                                        ConfidenceGauge(
                                          confidence: meta?.compositeConfidence ?? 0.92,
                                        ),
                                      ],
                                    ),
                                  ),
                                  const SizedBox(width: 16),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        const Text(
                                          'CURRENT SENTIMENT',
                                          style: TextStyle(
                                            fontSize: 11,
                                            fontWeight: FontWeight.w600,
                                            color: Color(0xFF9E9E9E),
                                          ),
                                        ),
                                        const SizedBox(height: 8),
                                        SentimentTimeline(
                                          timeline: meta?.sentimentTimeline ?? [],
                                        ),
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                            ),

                            // AI Interpretation
                            if (nlu?.aiSummary != null)
                              AiInterpretationPanel(
                                summary: nlu!.aiSummary!,
                                intent: nlu.intent,
                              ),

                            // Escalation Card
                            if (esc != null)
                              EscalationCard(
                                packet: esc,
                                onCorrect: () {},
                                onPartial: () {},
                                onIncorrect: () {},
                              ),
                          ],
                        ),
                      );
                    },
                  );
                },
              );
            },
          ),
        ],
      ),
    );
  }
}

// Made with Bob
