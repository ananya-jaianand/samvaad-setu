import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../services/voice_pipeline_service.dart';

class LiveMicButton extends StatefulWidget {
  final PipelineState state;
  final VoidCallback onStartRecord;
  final VoidCallback onStopRecord;

  const LiveMicButton({
    super.key,
    required this.state,
    required this.onStartRecord,
    required this.onStopRecord,
  });

  @override
  State<LiveMicButton> createState() => _LiveMicButtonState();
}

class _LiveMicButtonState extends State<LiveMicButton> {
  @override
  Widget build(BuildContext context) {
    final isListening = widget.state == PipelineState.listening;
    final isProcessing = widget.state == PipelineState.processing;
    final isReady = widget.state == PipelineState.ready;

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        GestureDetector(
          onTapDown: isReady ? (_) => widget.onStartRecord() : null,
          onTapUp: isListening ? (_) => widget.onStopRecord() : null,
          onTapCancel: isListening ? () => widget.onStopRecord() : null,
          child: Container(
            width: 72,
            height: 72,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: const Color(0xFF10B981), // Always green
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFF10B981).withOpacity(0.3),
                  blurRadius: 20,
                  spreadRadius: isListening ? 8 : 4,
                ),
              ],
            ),
            child: Icon(
              isListening ? Icons.mic : Icons.mic_none,
              size: 32,
              color: Colors.white,
            ),
          )
              .animate(
                onPlay: (controller) =>
                    isListening ? controller.repeat() : controller.stop(),
              )
              .scale(
                begin: const Offset(1.0, 1.0),
                end: const Offset(1.1, 1.1),
                duration: 800.ms,
              )
              .then()
              .scale(
                begin: const Offset(1.1, 1.1),
                end: const Offset(1.0, 1.0),
                duration: 800.ms,
              ),
        ),
        const SizedBox(height: 12),
        Text(
          isListening
              ? 'LISTENING...'
              : isProcessing
                  ? 'PROCESSING...'
                  : 'TAP TO MUTE',
          style: TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w700,
            color: const Color(0xFF9E9E9E),
            letterSpacing: 0.5,
          ),
        ),
      ],
    );
  }
}

// Made with Bob
