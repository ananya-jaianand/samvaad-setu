import 'dart:async';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../services/voice_pipeline_service.dart';
import '../models/session_models.dart';
import '../config/app_config.dart';
import '../widgets/ticket_card.dart';

// ─── Language config ──────────────────────────────────────────────────────────

const _langs = [
  (code: 'kn', label: 'ಕನ್ನಡ', iso: 'KAN', family: 'Noto Sans Kannada'),
  (code: 'hi', label: 'हिन्दी', iso: 'HIN', family: 'Noto Sans Devanagari'),
  (code: 'en', label: 'English', iso: 'ENG', family: 'Inter'),
];

const _statusLabel = {
  'idle':       {'kn': 'ಸಿದ್ಧವಾಗಿದೆ',                  'hi': 'तैयार',                    'en': 'Ready'},
  'starting':   {'kn': 'ಸಂಪರ್ಕಿಸುತ್ತಿದೆ…',             'hi': 'जोड़ रहे हैं…',             'en': 'Connecting…'},
  'ready':      {'kn': 'ಮಾತನಾಡಲು ಸಿದ್ಧ',               'hi': 'बोलने के लिए तैयार',        'en': 'Tap to speak'},
  'listening':  {'kn': 'AI ಆಲಿಸುತ್ತಿದೆ',               'hi': 'AI सुन रहा है',             'en': 'AI is listening'},
  'processing': {'kn': 'AI ಅರ್ಥ ಮಾಡಿಕೊಳ್ಳುತ್ತಿದೆ',     'hi': 'AI समझ रहा है',            'en': 'AI is thinking'},
  'speaking':   {'kn': 'AI ಮಾತನಾಡುತ್ತಿದೆ',             'hi': 'AI बोल रहा है',             'en': 'AI is speaking'},
  'verifying':  {'kn': 'AI ಪರಿಶೀಲಿಸುತ್ತಿದೆ',           'hi': 'AI सत्यापन कर रहा है',     'en': 'Please confirm'},
  'escalated':  {'kn': 'ಮಾನವ ಸಹಾಯಕರಿಗೆ ಸಂಪರ್ಕ',        'hi': 'मानव सहायक से जोड़ रहे हैं', 'en': 'Connecting to agent'},
  'error':      {'kn': 'ದೋಷ ಸಂಭವಿಸಿದೆ',               'hi': 'त्रुटि हुई',                'en': 'Connection error'},
};

const _verifyBtns = {
  'yes':    {'kn': 'ಹೌದು',     'hi': 'हाँ',          'en': 'Yes',    'sub_kn': 'ಸರಿಯಾಗಿದೆ',      'sub_hi': 'सही है',      'sub_en': 'Correct'},
  'partly': {'kn': 'ಕೊಂಚಕ್ಕೆ', 'hi': 'कुछ हद तक',   'en': 'Partly', 'sub_kn': 'ಸ್ವಲ್ಪ ಮಟ್ಟಿಗೆ', 'sub_hi': 'थोड़ा-बहुत', 'sub_en': 'Partly correct'},
  'no':     {'kn': 'ಇಲ್ಲ',     'hi': 'नहीं',         'en': 'No',     'sub_kn': 'ತಪ್ಪಾಗಿದೆ',      'sub_hi': 'गलत है',      'sub_en': 'Not correct'},
};

// ─── CitizenView ──────────────────────────────────────────────────────────────

class CitizenView extends StatefulWidget {
  final VoicePipelineService svc;
  const CitizenView({super.key, required this.svc});

  @override
  State<CitizenView> createState() => _CitizenViewState();
}

class _CitizenViewState extends State<CitizenView>
    with TickerProviderStateMixin {
  VoicePipelineService get _svc => widget.svc;

  String _lang = 'kn';
  bool _showHelp = false;

  late final AnimationController _breathe;
  late final AnimationController _barsCtrl;

  @override
  void initState() {
    super.initState();
    _breathe = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1600),
    )..repeat(reverse: true);
    _barsCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1100),
    )..repeat(reverse: true);

    _svc.startSession(language: _lang, district: AppConfig.defaultDistrict);
  }

  @override
  void dispose() {
    _breathe.dispose();
    _barsCtrl.dispose();
    super.dispose();
  }

  void _onLangChanged(String lang) {
    setState(() => _lang = lang);
    _svc.endSession();
    _svc.startSession(language: lang, district: AppConfig.defaultDistrict);
  }

  void _endCall() {
    _svc.endCall();
  }

  void _newCall() {
    _svc.startSession(language: _lang, district: AppConfig.defaultDistrict);
  }

  String get _fontFamily {
    return _langs
            .firstWhere((l) => l.code == _lang,
                orElse: () => _langs.last)
            .family;
  }

  String _stateKey(PipelineState s) {
    switch (s) {
      case PipelineState.idle:       return 'idle';
      case PipelineState.starting:   return 'starting';
      case PipelineState.ready:      return 'ready';
      case PipelineState.listening:  return 'listening';
      case PipelineState.processing: return 'processing';
      case PipelineState.speaking:   return 'speaking';
      case PipelineState.verifying:  return 'verifying';
      case PipelineState.escalated:  return 'escalated';
      case PipelineState.error:      return 'error';
    }
  }

  @override
  Widget build(BuildContext context) {
    return StreamBuilder<PipelineState>(
      stream: _svc.stateStream,
      initialData: PipelineState.idle,
      builder: (context, stateSnap) {
        final state = stateSnap.data ?? PipelineState.idle;
        final stateKey = _stateKey(state);
        final isListening = state == PipelineState.listening;
        final isActive = isListening || state == PipelineState.speaking;
        final isEscalated = state == PipelineState.escalated;
        final canRecord = state == PipelineState.ready;
        final isProcessing =
            state == PipelineState.processing || state == PipelineState.starting;

        return StreamBuilder<List<SessionTurn>>(
          stream: _svc.turnsStream,
          initialData: const [],
          builder: (context, turnsSnap) {
            final turns = turnsSnap.data ?? [];
            final lastCitizenTurn = turns.lastWhereOrNull(
                (t) => t.speaker == 'citizen');
            // Include 'agent' turns so human-agent replies are visible to the citizen
            final lastAiTurn = turns.lastWhereOrNull(
                (t) => t.speaker == 'ai' || t.speaker == 'agent');

            return StreamBuilder<VerificationPrompt?>(
              stream: _svc.verificationPromptStream,
              builder: (context, verifySnap) {
                final verifyPrompt = verifySnap.data;
                final showVerify = verifyPrompt != null;
                final isEnded = state == PipelineState.idle && turns.isNotEmpty;

                return Stack(
                  children: [
                    // Background gradient
                    Positioned.fill(
                      child: Container(
                        decoration: BoxDecoration(
                          gradient: RadialGradient(
                            center: const Alignment(0, -1.2),
                            radius: 1.8,
                            colors: [
                              const Color(0xFFFFF3DC),
                              AppTheme.ivory.withValues(alpha: 0.0),
                            ],
                          ),
                        ),
                      ),
                    ),
                    // Dot motif
                    Positioned.fill(
                        child: CustomPaint(painter: _DotMotifPainter())),

                    // Main content
                    Column(
                      children: [
                        // Header
                        Padding(
                          padding: const EdgeInsets.fromLTRB(28, 18, 28, 0),
                          child: Row(
                            children: [
                              _Brand(),
                              const Spacer(),
                              _LangToggle(
                                  lang: _lang, onChanged: _onLangChanged),
                              const SizedBox(width: 10),
                              _HelpBtn(
                                  onTap: () =>
                                      setState(() => _showHelp = true)),
                            ],
                          ),
                        ),

                        // Stage — transcript summary after call ends
                        if (isEnded)
                          Expanded(
                            child: _CallTranscript(
                              turns: turns,
                              lang: _lang,
                              fontFamily: _fontFamily,
                              onNewCall: _newCall,
                            ),
                          )
                        else ...[
                          Expanded(
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                // Mic visualizer
                                GestureDetector(
                                  onTap: () {
                                    if (isListening) {
                                      _svc.stopRecording();
                                    } else if (canRecord) {
                                      _svc.startRecording();
                                    }
                                  },
                                  child: SizedBox(
                                    width: 320,
                                    height: 320,
                                    child: Stack(
                                      alignment: Alignment.center,
                                      children: [
                                        _MicRings(
                                          state: state,
                                          breathe: _breathe,
                                        ),
                                        _MicBars(
                                          ctrl: _barsCtrl,
                                          active: isActive,
                                          isProcessing: isProcessing,
                                          isEscalated: isEscalated,
                                        ),
                                      ],
                                    ),
                                  ),
                                ),

                                const SizedBox(height: 16),

                                // Transcript / AI response
                                Padding(
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 28),
                                  child: ConstrainedBox(
                                    constraints: const BoxConstraints(
                                        maxWidth: 760, minHeight: 80),
                                    child: Column(
                                      children: [
                                        Text(
                                          _statusLabel[stateKey]?[_lang] ?? '',
                                          style: const TextStyle(
                                            fontSize: 11.5,
                                            letterSpacing: 0.14,
                                            color: AppTheme.muted,
                                            fontFamily: 'Inter',
                                          ),
                                        ),
                                        const SizedBox(height: 10),
                                        AnimatedSwitcher(
                                          duration: const Duration(
                                              milliseconds: 200),
                                          child: _buildTranscriptText(
                                            state: state,
                                            lastCitizenTurn: lastCitizenTurn,
                                            lastAiTurn: lastAiTurn,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ),

                                const SizedBox(height: 20),

                                // Verification panel
                                if (showVerify && !isEscalated)
                                  _VerifyPanel(
                                    lang: _lang,
                                    fontFamily: _fontFamily,
                                    promptText: verifyPrompt.text,
                                    onVerify: (s) =>
                                        _svc.sendVerificationResponse(s),
                                  ),

                                // Escalation callout
                                if (isEscalated)
                                  StreamBuilder<EscalationPacket?>(
                                    stream: _svc.escalationStream,
                                    builder: (ctx, escSnap) =>
                                        _EscalationCallout(
                                      lang: _lang,
                                      fontFamily: _fontFamily,
                                      packet: escSnap.data,
                                    ),
                                  ),

                                // Ticket card — shown after confirmed, escalated, or end-of-call
                                StreamBuilder<TicketInfo?>(
                                  stream: _svc.ticketStream,
                                  builder: (ctx, tickSnap) {
                                    final ticket = tickSnap.data;
                                    if (ticket == null) return const SizedBox.shrink();
                                    return Padding(
                                      padding: const EdgeInsets.only(top: 10),
                                      child: TicketCard(
                                        ticket: ticket,
                                        lang: _lang,
                                        fontFamily: _fontFamily,
                                      ),
                                    );
                                  },
                                ),

                                // Error banner
                                if (state == PipelineState.error)
                                  _ErrorBanner(
                                    lang: _lang,
                                    onRetry: () => _svc.startSession(
                                      language: _lang,
                                      district: AppConfig.defaultDistrict,
                                    ),
                                  ),

                                // End call button
                                if (canRecord ||
                                    isListening ||
                                    state == PipelineState.verifying)
                                  Padding(
                                    padding: const EdgeInsets.only(top: 12),
                                    child: GestureDetector(
                                      onTap: _endCall,
                                      child: Container(
                                        padding: const EdgeInsets.symmetric(
                                            horizontal: 18, vertical: 9),
                                        decoration: BoxDecoration(
                                          color: Colors.white,
                                          border: Border.all(
                                              color: const Color(0xFFF2D5CE)),
                                          borderRadius:
                                              BorderRadius.circular(999),
                                        ),
                                        child: Row(
                                          mainAxisSize: MainAxisSize.min,
                                          children: [
                                            Container(
                                              width: 8,
                                              height: 8,
                                              decoration: const BoxDecoration(
                                                shape: BoxShape.circle,
                                                color: AppTheme.red,
                                              ),
                                            ),
                                            const SizedBox(width: 8),
                                            Text(
                                              _lang == 'kn'
                                                  ? 'ಕರೆ ಕೊನೆಗೊಳಿಸಿ'
                                                  : _lang == 'hi'
                                                      ? 'कॉल समाप्त करें'
                                                      : 'End call',
                                              style: const TextStyle(
                                                fontSize: 13,
                                                color: AppTheme.red,
                                                fontWeight: FontWeight.w500,
                                              ),
                                            ),
                                          ],
                                        ),
                                      ),
                                    ),
                                  ),
                              ],
                            ),
                          ),

                          // Status row
                          Padding(
                            padding:
                                const EdgeInsets.fromLTRB(0, 14, 0, 28),
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                _StatusDot(state: state, breathe: _breathe),
                                const SizedBox(width: 10),
                                Text(
                                  _statusLabel[stateKey]?[_lang] ?? '',
                                  style: TextStyle(
                                    color: AppTheme.muted,
                                    fontSize: 13,
                                    letterSpacing: 0.04,
                                    fontFamily: _fontFamily,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ],
                    ),

                    // Help overlay
                    if (_showHelp)
                      _HelpOverlay(
                        lang: _lang,
                        fontFamily: _fontFamily,
                        onClose: () => setState(() => _showHelp = false),
                      ),
                  ],
                );
              },
            );
          },
        );
      },
    );
  }

  Widget _buildTranscriptText({
    required PipelineState state,
    required SessionTurn? lastCitizenTurn,
    required SessionTurn? lastAiTurn,
  }) {
    // While listening: show what citizen is saying (last citizen turn grows)
    if (state == PipelineState.listening && lastCitizenTurn != null) {
      return Text(
        lastCitizenTurn.rawTranscript,
        key: ValueKey('cit-${lastCitizenTurn.turnId}'),
        textAlign: TextAlign.center,
        style: TextStyle(
          fontSize: 26,
          height: 1.45,
          letterSpacing: -0.005,
          color: AppTheme.ink,
          fontWeight: FontWeight.w500,
          fontFamily: _fontFamily,
        ),
      );
    }

    // While speaking or after: show the last AI or agent response
    if ((state == PipelineState.speaking ||
            state == PipelineState.ready ||
            state == PipelineState.verifying ||
            state == PipelineState.escalated) &&
        lastAiTurn != null) {
      final isAgentTurn = lastAiTurn.speaker == 'agent';
      return Column(
        key: ValueKey('${isAgentTurn ? 'ag' : 'ai'}-${lastAiTurn.turnId}'),
        mainAxisSize: MainAxisSize.min,
        children: [
          if (isAgentTurn)
            const Padding(
              padding: EdgeInsets.only(bottom: 6),
              child: Text(
                'Agent',
                style: TextStyle(
                  fontSize: 11,
                  letterSpacing: 0.1,
                  color: AppTheme.muted,
                  fontFamily: 'Inter',
                ),
              ),
            ),
          if (isAgentTurn)
            _TypewriterText(
              text: lastAiTurn.displayText,
              style: TextStyle(
                fontSize: 26,
                height: 1.45,
                color: AppTheme.saffron2,
                fontWeight: FontWeight.w500,
                fontFamily: _fontFamily,
              ),
            )
          else
            Text(
              lastAiTurn.displayText,
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 26,
                height: 1.45,
                color: AppTheme.teal2,
                fontWeight: FontWeight.w500,
                fontFamily: _fontFamily,
              ),
            ),
        ],
      );
    }

    // Default placeholder
    return Text(
      _lang == 'kn'
          ? 'ಮಾತನಾಡಲು ಮೈಕ್ ಟ್ಯಾಪ್ ಮಾಡಿ…'
          : _lang == 'hi'
              ? 'बोलने के लिए माइक टैप करें…'
              : 'Tap the mic to speak…',
      textAlign: TextAlign.center,
      style: TextStyle(
        fontSize: 26,
        color: AppTheme.muted,
        fontFamily: _fontFamily,
      ),
    );
  }
}

// ─── Mic rings ────────────────────────────────────────────────────────────────

class _MicRings extends StatelessWidget {
  final PipelineState state;
  final AnimationController breathe;
  const _MicRings({required this.state, required this.breathe});

  @override
  Widget build(BuildContext context) {
    final isListening = state == PipelineState.listening;
    final isDistress = state == PipelineState.escalated;

    return AnimatedBuilder(
      animation: breathe,
      builder: (_, __) {
        final t = breathe.value;
        final scale = 0.95 + 0.13 * t;
        final opacity = 0.6 + 0.4 * t;
        return Stack(
          alignment: Alignment.center,
          children: [
            _ring(320, AppTheme.teal.withValues(alpha: 0.18)),
            _ring(260, AppTheme.teal.withValues(alpha: 0.14)),
            _ring(200, AppTheme.teal.withValues(alpha: 0.10)),
            if (isListening || isDistress)
              Transform.scale(
                scale: scale,
                child: Container(
                  width: 284,
                  height: 284,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: RadialGradient(
                      colors: isDistress
                          ? [
                              AppTheme.sage.withValues(alpha: 0.45 * opacity),
                              AppTheme.sage.withValues(alpha: 0),
                            ]
                          : [
                              AppTheme.saffron.withValues(alpha: 0.35 * opacity),
                              AppTheme.saffron.withValues(alpha: 0),
                            ],
                    ),
                  ),
                ),
              ),
          ],
        );
      },
    );
  }

  Widget _ring(double size, Color color) => Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          border: Border.all(color: color),
        ),
      );
}

// ─── Animated bars ────────────────────────────────────────────────────────────

class _MicBars extends StatelessWidget {
  final AnimationController ctrl;
  final bool active;
  final bool isProcessing;
  final bool isEscalated;
  const _MicBars({
    required this.ctrl,
    required this.active,
    required this.isProcessing,
    required this.isEscalated,
  });

  @override
  Widget build(BuildContext context) {
    const barHeights = [0.30, 0.60, 0.90, 0.70, 0.50, 0.80, 0.35];
    const delays = [0.0, 0.09, 0.18, 0.27, 0.36, 0.45, 0.54];

    return AnimatedBuilder(
      animation: ctrl,
      builder: (_, __) {
        return Row(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.center,
          children: List.generate(7, (i) {
            final phase = (ctrl.value + delays[i]) % 1.0;
            final scale = active
                ? 0.5 + 0.5 * math.sin(phase * math.pi)
                : isProcessing
                    ? 0.3 + 0.2 * math.sin((phase + i * 0.15) * math.pi)
                    : 0.15;
            final h = (120.0 * barHeights[i] * scale).clamp(4.0, 108.0);
            final topColor = isEscalated ? AppTheme.sage : AppTheme.saffron;
            final botColor = isEscalated ? AppTheme.teal2 : AppTheme.teal;
            return Padding(
              padding: const EdgeInsets.symmetric(horizontal: 4),
              child: Container(
                width: 10,
                height: h,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(6),
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [topColor, botColor],
                  ),
                ),
              ),
            );
          }),
        );
      },
    );
  }
}

// ─── Status dot ───────────────────────────────────────────────────────────────

class _StatusDot extends StatelessWidget {
  final PipelineState state;
  final AnimationController breathe;
  const _StatusDot({required this.state, required this.breathe});

  @override
  Widget build(BuildContext context) {
    Color color;
    if (state == PipelineState.processing || state == PipelineState.starting) {
      color = AppTheme.teal;
    } else if (state == PipelineState.speaking) {
      color = AppTheme.teal;
    } else if (state == PipelineState.escalated) {
      color = AppTheme.sage;
    } else if (state == PipelineState.error) {
      color = AppTheme.red;
    } else {
      color = AppTheme.saffron;
    }

    final pulse =
        state == PipelineState.listening || state == PipelineState.speaking;

    return AnimatedBuilder(
      animation: breathe,
      builder: (_, __) {
        final scale = pulse ? 1.0 + 0.3 * breathe.value : 1.0;
        return Transform.scale(
          scale: scale,
          child: Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: color,
              boxShadow: [
                BoxShadow(
                  color: color.withValues(alpha: 0.3),
                  blurRadius: 4,
                  spreadRadius: 2,
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

// ─── Brand ────────────────────────────────────────────────────────────────────

class _Brand extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 36,
          height: 36,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(10),
            gradient: const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [AppTheme.teal, AppTheme.teal2],
            ),
            boxShadow: [
              BoxShadow(
                color: AppTheme.teal.withValues(alpha: 0.18),
                blurRadius: 18,
                offset: const Offset(0, 6),
              ),
            ],
          ),
          child: const Icon(Icons.record_voice_over_outlined,
              color: Color(0xFFF6E2BF), size: 18),
        ),
        const SizedBox(width: 12),
        const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Samvaad-Setu',
                style: TextStyle(
                  fontWeight: FontWeight.w600,
                  color: AppTheme.teal2,
                  letterSpacing: 0.01,
                  fontSize: 14,
                )),
            Text('Karnataka 1092',
                style: TextStyle(
                  fontSize: 11.5,
                  color: AppTheme.muted,
                  letterSpacing: 0.04,
                )),
          ],
        ),
      ],
    );
  }
}

// ─── Language toggle ──────────────────────────────────────────────────────────

class _LangToggle extends StatelessWidget {
  final String lang;
  final ValueChanged<String> onChanged;
  const _LangToggle({required this.lang, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border.all(color: AppTheme.hair),
        borderRadius: BorderRadius.circular(14),
        boxShadow: [
          BoxShadow(
              color: AppTheme.ink.withValues(alpha: 0.04),
              blurRadius: 2,
              offset: const Offset(0, 1)),
        ],
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: _langs.map((l) {
          final active = lang == l.code;
          return GestureDetector(
            onTap: () => onChanged(l.code),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 150),
              padding:
                  const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
              decoration: BoxDecoration(
                color: active ? AppTheme.teal : Colors.transparent,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(l.label,
                      style: TextStyle(
                        fontFamily: l.family,
                        fontSize: 14,
                        fontWeight: active ? FontWeight.w600 : FontWeight.w500,
                        color: active
                            ? const Color(0xFFFFF7E5)
                            : AppTheme.ink2,
                      )),
                  const SizedBox(width: 8),
                  Text(l.iso,
                      style: TextStyle(
                        fontSize: 10.5,
                        letterSpacing: 0.08,
                        color: active
                            ? const Color(0xFFFFF7E5).withValues(alpha: 0.85)
                            : AppTheme.muted,
                      )),
                ],
              ),
            ),
          );
        }).toList(),
      ),
    );
  }
}

// ─── Help button ──────────────────────────────────────────────────────────────

class _HelpBtn extends StatelessWidget {
  final VoidCallback onTap;
  const _HelpBtn({required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 42,
        height: 42,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: Colors.white,
          border: Border.all(color: AppTheme.hair),
          boxShadow: [
            BoxShadow(
                color: AppTheme.ink.withValues(alpha: 0.05),
                blurRadius: 2,
                offset: const Offset(0, 1)),
          ],
        ),
        child: const Icon(Icons.help_outline_rounded,
            color: AppTheme.teal2, size: 20),
      ),
    );
  }
}

// ─── Verification panel ───────────────────────────────────────────────────────

class _VerifyPanel extends StatelessWidget {
  final String lang;
  final String fontFamily;
  final String promptText;
  final ValueChanged<String> onVerify;
  const _VerifyPanel({
    required this.lang,
    required this.fontFamily,
    required this.promptText,
    required this.onVerify,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 28),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 820),
        child: Container(
          padding: const EdgeInsets.fromLTRB(22, 22, 22, 18),
          decoration: BoxDecoration(
            color: Colors.white,
            border: Border.all(color: AppTheme.hair),
            borderRadius: BorderRadius.circular(24),
            boxShadow: [
              BoxShadow(
                color: AppTheme.teal.withValues(alpha: 0.08),
                blurRadius: 40,
                offset: const Offset(0, 12),
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 10, vertical: 5),
                    decoration: BoxDecoration(
                        color: AppTheme.tealSoft,
                        borderRadius: BorderRadius.circular(999)),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.check_circle_outline_rounded,
                            size: 14, color: AppTheme.teal),
                        const SizedBox(width: 8),
                        Text(
                          lang == 'kn'
                              ? 'ಪರಿಶೀಲನೆ'
                              : lang == 'hi'
                                  ? 'सत्यापन'
                                  : 'Verification',
                          style: const TextStyle(
                              color: AppTheme.teal,
                              fontWeight: FontWeight.w600,
                              fontSize: 12.5,
                              letterSpacing: 0.08),
                        ),
                      ],
                    ),
                  ),
                  const Spacer(),
                  Text(
                    lang == 'kn'
                        ? 'ನಾನು ಸರಿಯಾಗಿ ಅರ್ಥಮಾಡಿಕೊಂಡೆನೆ?'
                        : lang == 'hi'
                            ? 'क्या मैंने सही समझा?'
                            : 'Did I understand correctly?',
                    style: const TextStyle(
                        fontSize: 11.5,
                        color: AppTheme.muted,
                        letterSpacing: 0.08),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              Text(
                promptText,
                style: TextStyle(
                  fontSize: 22,
                  height: 1.5,
                  fontWeight: FontWeight.w500,
                  letterSpacing: -0.005,
                  color: AppTheme.ink,
                  fontFamily: fontFamily,
                ),
              ),
              const SizedBox(height: 14),
              Row(
                children: [
                  Expanded(
                      child: _VBtn(
                          type: 'yes',
                          lang: lang,
                          fontFamily: fontFamily,
                          onTap: () => onVerify('correct'))),
                  const SizedBox(width: 10),
                  Expanded(
                      child: _VBtn(
                          type: 'partly',
                          lang: lang,
                          fontFamily: fontFamily,
                          onTap: () => onVerify('partial'))),
                  const SizedBox(width: 10),
                  Expanded(
                      child: _VBtn(
                          type: 'no',
                          lang: lang,
                          fontFamily: fontFamily,
                          onTap: () => onVerify('incorrect'))),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _VBtn extends StatelessWidget {
  final String type;
  final String lang;
  final String fontFamily;
  final VoidCallback onTap;
  const _VBtn(
      {required this.type,
      required this.lang,
      required this.fontFamily,
      required this.onTap});

  @override
  Widget build(BuildContext context) {
    final data = _verifyBtns[type]!;
    Color bg, borderColor, textColor;
    if (type == 'yes') {
      bg = const Color(0xFFF1F8F4);
      borderColor = const Color(0xFFCFE1D6);
      textColor = const Color(0xFF1B4A3A);
    } else if (type == 'no') {
      bg = const Color(0xFFFFF4F2);
      borderColor = const Color(0xFFF2D5CE);
      textColor = const Color(0xFF7A1F1F);
    } else {
      bg = const Color(0xFFFFF7E8);
      borderColor = const Color(0xFFF1DDA7);
      textColor = const Color(0xFF7A5A14);
    }

    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 18, horizontal: 14),
        decoration: BoxDecoration(
          color: bg,
          border: Border.all(color: borderColor),
          borderRadius: BorderRadius.circular(16),
        ),
        child: Column(
          children: [
            Text(data[lang] ?? '',
                style: TextStyle(
                    fontSize: 19,
                    fontWeight: FontWeight.w600,
                    color: textColor,
                    fontFamily: fontFamily)),
            const SizedBox(height: 6),
            Text(data['sub_$lang'] ?? '',
                style: const TextStyle(
                    fontSize: 12.5,
                    color: AppTheme.muted,
                    letterSpacing: 0.02)),
          ],
        ),
      ),
    );
  }
}

// ─── Escalation callout ───────────────────────────────────────────────────────

class _EscalationCallout extends StatelessWidget {
  final String lang;
  final String fontFamily;
  final EscalationPacket? packet;
  const _EscalationCallout(
      {required this.lang, required this.fontFamily, this.packet});

  @override
  Widget build(BuildContext context) {
    final msg = packet?.escalationMessage ??
        (lang == 'kn'
            ? 'ನಾನು ನಿಮ್ಮನ್ನು ಮಾನವ ಸಹಾಯಕರಿಗೆ ಸಂಪರ್ಕಿಸುತ್ತಿದ್ದೇನೆ'
            : lang == 'hi'
                ? 'मैं आपको मानव सहायक से जोड़ रही हूँ'
                : 'Connecting you to a human agent');

    final sub = lang == 'kn'
        ? 'ದಯವಿಟ್ಟು ಲೈನ್ ಕಡಿಯಬೇಡಿ — ಸಹಾಯಕರು ಬರುತ್ತಾರೆ.'
        : lang == 'hi'
            ? 'कृपया लाइन मत छोड़िए — एक सहायक आपसे बात करेंगी।'
            : 'Please don\'t hang up — an agent will be with you shortly.';

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 28),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 760),
        child: Container(
          padding: const EdgeInsets.fromLTRB(12, 14, 16, 14),
          decoration: BoxDecoration(
            color: Colors.white,
            border: Border(
              top: BorderSide(color: AppTheme.hair),
              right: BorderSide(color: AppTheme.hair),
              bottom: BorderSide(color: AppTheme.hair),
              left: const BorderSide(color: AppTheme.sage, width: 4),
            ),
            borderRadius: BorderRadius.circular(14),
            boxShadow: [
              BoxShadow(
                color: AppTheme.sage.withValues(alpha: 0.1),
                blurRadius: 30,
                offset: const Offset(0, 10),
              ),
            ],
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 36,
                height: 36,
                decoration: const BoxDecoration(
                    shape: BoxShape.circle,
                    color: Color(0xFFE8F0EA)),
                child: const Icon(Icons.favorite_outline_rounded,
                    size: 18, color: Color(0xFF2E5640)),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(msg,
                        style: TextStyle(
                            fontWeight: FontWeight.w600,
                            fontSize: 14,
                            color: AppTheme.ink,
                            fontFamily: fontFamily)),
                    const SizedBox(height: 4),
                    Text(sub,
                        style: TextStyle(
                            fontSize: 12.5,
                            color: AppTheme.muted,
                            height: 1.5,
                            fontFamily: fontFamily)),
                    if (packet != null) ...[
                      const SizedBox(height: 4),
                      Text(
                        '${packet!.district} · ${packet!.reason}',
                        style: const TextStyle(
                            fontSize: 11.5,
                            color: AppTheme.muted,
                            fontFamily: 'JetBrains Mono'),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ─── Error banner ─────────────────────────────────────────────────────────────

class _ErrorBanner extends StatelessWidget {
  final String lang;
  final VoidCallback onRetry;
  const _ErrorBanner({required this.lang, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 28),
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: const Color(0xFFFFF4F2),
          border: Border.all(color: const Color(0xFFF2D5CE)),
          borderRadius: BorderRadius.circular(14),
        ),
        child: Row(
          children: [
            const Icon(Icons.wifi_off_rounded, color: AppTheme.red, size: 18),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                lang == 'kn'
                    ? 'ಬ್ಯಾಕೆಂಡ್‌ಗೆ ಸಂಪರ್ಕಿಸಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ'
                    : lang == 'hi'
                        ? 'बैकएंड से जुड़ नहीं पाए'
                        : 'Could not connect to backend',
                style: const TextStyle(fontSize: 13, color: AppTheme.red),
              ),
            ),
            GestureDetector(
              onTap: onRetry,
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: AppTheme.red,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Text('Retry',
                    style: TextStyle(
                        color: Colors.white,
                        fontSize: 12,
                        fontWeight: FontWeight.w600)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ─── End-of-call transcript ───────────────────────────────────────────────────

class _CallTranscript extends StatelessWidget {
  final List<SessionTurn> turns;
  final String lang;
  final String fontFamily;
  final VoidCallback onNewCall;
  const _CallTranscript({
    required this.turns,
    required this.lang,
    required this.fontFamily,
    required this.onNewCall,
  });

  @override
  Widget build(BuildContext context) {
    final title = lang == 'kn'
        ? 'ಸಂಭಾಷಣೆಯ ಸಾರಾಂಶ'
        : lang == 'hi'
            ? 'बातचीत का सारांश'
            : 'Conversation summary';
    final newCallLabel = lang == 'kn'
        ? 'ಹೊಸ ಕರೆ ಪ್ರಾರಂಭಿಸಿ'
        : lang == 'hi'
            ? 'नई कॉल शुरू करें'
            : 'Start new call';

    return Column(
      children: [
        // Header
        Container(
          padding: const EdgeInsets.fromLTRB(28, 20, 28, 16),
          child: Row(
            children: [
              Container(
                width: 8,
                height: 8,
                decoration: const BoxDecoration(
                  shape: BoxShape.circle,
                  color: AppTheme.sage,
                ),
              ),
              const SizedBox(width: 10),
              Text(
                title,
                style: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: AppTheme.ink,
                  letterSpacing: 0.04,
                ),
              ),
              const Spacer(),
              GestureDetector(
                onTap: onNewCall,
                child: Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  decoration: BoxDecoration(
                    color: AppTheme.teal,
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Text(
                    newCallLabel,
                    style: const TextStyle(
                      fontSize: 12.5,
                      color: Color(0xFFFFF7E5),
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
        // Turn list
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.fromLTRB(28, 0, 28, 28),
            itemCount: turns.length,
            itemBuilder: (_, i) {
              final t = turns[i];
              final isCit = t.speaker == 'citizen';
              final text = t.displayText;
              if (text.isEmpty) return const SizedBox.shrink();
              return Padding(
                padding: const EdgeInsets.only(bottom: 16),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      width: 28,
                      height: 28,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: isCit
                            ? const Color(0xFFFFF1DD)
                            : AppTheme.tealSoft,
                        border: Border.all(
                          color: isCit
                              ? const Color(0xFFF1DDA7)
                              : const Color(0xFFC9DCD5),
                        ),
                      ),
                      child: Center(
                        child: Text(
                          isCit ? 'C' : 'AI',
                          style: TextStyle(
                            fontSize: 9,
                            fontWeight: FontWeight.w700,
                            color: isCit
                                ? AppTheme.saffron2
                                : AppTheme.teal2,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        text,
                        style: TextStyle(
                          fontSize: 15,
                          height: 1.55,
                          color: AppTheme.ink,
                          fontFamily: isCit ? fontFamily : 'Inter',
                        ),
                      ),
                    ),
                  ],
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}

// ─── Help overlay ─────────────────────────────────────────────────────────────

class _HelpOverlay extends StatelessWidget {
  final String lang;
  final String fontFamily;
  final VoidCallback onClose;
  const _HelpOverlay(
      {required this.lang, required this.fontFamily, required this.onClose});

  static const _content = {
    'kn': (
      ttl: 'ನಾವೇಕೆ ಪರಿಶೀಲಿಸುತ್ತೇವೆ',
      body:
          'ನಿಮ್ಮ ಸಮಸ್ಯೆಯನ್ನು ಸರಿಯಾಗಿ ಅರ್ಥ ಮಾಡಿಕೊಳ್ಳಲು ನಾವು ಮೊದಲು ಪುನರುಚ್ಚರಿಸುತ್ತೇವೆ — ನೀವು "ಹೌದು" ಎಂದಾಗ ಮಾತ್ರ ಮುಂದುವರಿಯುತ್ತೇವೆ.',
      steps: [
        ('ಆಲಿಸುವುದು', 'ನೀವು ಹೇಳುವುದನ್ನು ಎಚ್ಚರಿಕೆಯಿಂದ ಆಲಿಸುತ್ತೇವೆ'),
        ('ಪುನರುಚ್ಚರಣೆ', 'ನಮಗೆ ಏನು ಅರ್ಥವಾಯಿತು ಎಂದು ನಿಮಗೆ ಹೇಳುತ್ತೇವೆ'),
        ('ನಿಮ್ಮ ದೃಢೀಕರಣ',
            'ನೀವು ಸರಿಯೆಂದು ಹೇಳಿದರೆ ಮಾತ್ರ ಮುಂದೆ ಸಾಗುತ್ತೇವೆ'),
      ],
      close: 'ಮುಚ್ಚಿ',
    ),
    'hi': (
      ttl: 'हम सत्यापन क्यों करते हैं',
      body:
          'आपकी बात ठीक से समझने के लिए हम पहले उसे दोहराते हैं — आपकी "हाँ" मिलने पर ही आगे बढ़ते हैं।',
      steps: [
        ('सुनना', 'हम आपकी बात ध्यान से सुनते हैं'),
        ('दोहराना', 'हमने जो समझा वह आपको बताते हैं'),
        ('आपकी पुष्टि', 'आपके सही कहने पर ही आगे बढ़ते हैं'),
      ],
      close: 'बंद करें',
    ),
    'en': (
      ttl: 'Why we verify',
      body:
          'To make sure we\'ve understood you correctly, we restate your concern — and only proceed when you say "Yes."',
      steps: [
        ('Listen', 'We listen carefully to what you\'re saying'),
        ('Restate', 'We tell you what we understood'),
        ('Your confirmation', 'We only proceed when you confirm'),
      ],
      close: 'Close',
    ),
  };

  @override
  Widget build(BuildContext context) {
    final c = _content[lang] ?? _content['en']!;
    return GestureDetector(
      onTap: onClose,
      child: Container(
        color: Colors.black.withValues(alpha: 0.55),
        child: Center(
          child: GestureDetector(
            onTap: () {},
            child: Container(
              margin: const EdgeInsets.all(20),
              constraints: const BoxConstraints(maxWidth: 560),
              padding: const EdgeInsets.all(28),
              decoration: BoxDecoration(
                color: AppTheme.ivory,
                border: Border.all(color: AppTheme.hair),
                borderRadius: BorderRadius.circular(24),
                boxShadow: const [
                  BoxShadow(
                      color: Color(0x4D000000),
                      blurRadius: 80,
                      offset: Offset(0, 30)),
                ],
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(c.ttl,
                      style: TextStyle(
                          fontSize: 22,
                          fontWeight: FontWeight.w600,
                          color: AppTheme.teal2,
                          fontFamily: fontFamily)),
                  const SizedBox(height: 6),
                  Text(c.body,
                      style: TextStyle(
                          color: AppTheme.ink2,
                          height: 1.55,
                          fontFamily: fontFamily)),
                  const SizedBox(height: 14),
                  ...c.steps.asMap().entries.map((e) {
                    final (title, desc) = e.value;
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Container(
                            width: 32,
                            height: 32,
                            decoration: const BoxDecoration(
                                shape: BoxShape.circle,
                                color: AppTheme.teal),
                            child: Center(
                              child: Text('${e.key + 1}',
                                  style: const TextStyle(
                                      color: Color(0xFFFFF7E5),
                                      fontWeight: FontWeight.w600,
                                      fontSize: 13,
                                      fontFamily: 'JetBrains Mono')),
                            ),
                          ),
                          const SizedBox(width: 14),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(title,
                                    style: TextStyle(
                                        fontWeight: FontWeight.w600,
                                        color: AppTheme.ink,
                                        fontFamily: fontFamily)),
                                Text(desc,
                                    style: TextStyle(
                                        fontSize: 13.5,
                                        color: AppTheme.muted,
                                        height: 1.5,
                                        fontFamily: fontFamily)),
                              ],
                            ),
                          ),
                        ],
                      ),
                    );
                  }),
                  const SizedBox(height: 8),
                  Align(
                    alignment: Alignment.centerRight,
                    child: GestureDetector(
                      onTap: onClose,
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 16, vertical: 10),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          border: Border.all(color: AppTheme.hair),
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: Text(c.close,
                            style: const TextStyle(
                                fontWeight: FontWeight.w500,
                                color: AppTheme.ink)),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

// ─── Background dot motif ─────────────────────────────────────────────────────

class _DotMotifPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    const spacing = 28.0;
    final cx = size.width / 2;
    final cy = size.height / 2;
    for (double x = 0; x < size.width; x += spacing) {
      for (double y = 0; y < size.height; y += spacing) {
        final dx = x - cx;
        final dy = y - cy;
        final dist = math.sqrt(dx * dx + dy * dy);
        final maxDist = math.sqrt(cx * cx + cy * cy);
        final fade = ((dist / maxDist) - 0.3).clamp(0.0, 0.7) / 0.7;
        if (fade > 0) {
          canvas.drawCircle(
            Offset(x, y),
            1.0,
            Paint()
              ..color = AppTheme.teal.withValues(alpha: 0.04 * fade)
              ..style = PaintingStyle.fill,
          );
        }
      }
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter old) => false;
}

// ─── Extension helper ─────────────────────────────────────────────────────────

extension _ListExt<T> on List<T> {
  T? lastWhereOrNull(bool Function(T) test) {
    for (var i = length - 1; i >= 0; i--) {
      if (test(this[i])) return this[i];
    }
    return null;
  }
}

// ─── Typewriter caption for live agent replies ────────────────────────────────

class _TypewriterText extends StatefulWidget {
  final String text;
  final TextStyle style;

  const _TypewriterText({required this.text, required this.style});

  @override
  State<_TypewriterText> createState() => _TypewriterTextState();
}

class _TypewriterTextState extends State<_TypewriterText> {
  int _visible = 0;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _start(widget.text);
  }

  @override
  void didUpdateWidget(_TypewriterText old) {
    super.didUpdateWidget(old);
    if (old.text != widget.text) {
      _timer?.cancel();
      _visible = 0;
      _start(widget.text);
    }
  }

  void _start(String text) {
    _timer = Timer.periodic(const Duration(milliseconds: 22), (_) {
      if (!mounted) return;
      if (_visible < text.length) {
        setState(() => _visible++);
      } else {
        _timer?.cancel();
      }
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final shown = widget.text.substring(0, _visible);
    final done = _visible >= widget.text.length;
    return Text(
      done ? shown : '$shown▌',
      textAlign: TextAlign.center,
      style: widget.style,
    );
  }
}
