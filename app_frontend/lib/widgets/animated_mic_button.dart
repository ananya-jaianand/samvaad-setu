import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../services/voice_pipeline_service.dart';

class AnimatedMicButton extends StatelessWidget {
  final PipelineState state;
  final VoidCallback onStartRecord;
  final VoidCallback onStopRecord;

  const AnimatedMicButton({
    super.key,
    required this.state,
    required this.onStartRecord,
    required this.onStopRecord,
  });

  @override
  Widget build(BuildContext context) {
    final bool isListening = state == PipelineState.listening;
    final bool isProcessing = state == PipelineState.processing || state == PipelineState.speaking;
    final bool isDisabled = state == PipelineState.idle || state == PipelineState.starting || state == PipelineState.escalated || state == PipelineState.error;

    return GestureDetector(
      onTapDown: isDisabled || isProcessing ? null : (_) => onStartRecord(),
      onTapUp: isDisabled || isProcessing ? null : (_) => onStopRecord(),
      onTapCancel: isDisabled || isProcessing ? null : () => onStopRecord(),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 300),
        width: isListening ? 90 : 80,
        height: isListening ? 90 : 80,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: isListening 
              ? const Color(0xFFEF4444) // Red
              : isDisabled 
                  ? const Color(0xFFE0E0E0) // Light Grey
                  : const Color(0xFF826695), // PocketSage Purple
          boxShadow: isListening 
              ? [BoxShadow(color: const Color(0xFFEF4444).withOpacity(0.6), blurRadius: 20, spreadRadius: 5)]
              : [
                  if (!isDisabled)
                    BoxShadow(color: const Color(0xFF826695).withOpacity(0.3), blurRadius: 15, spreadRadius: 2)
                ],
        ),
        child: Center(
          child: isProcessing
              ? const CircularProgressIndicator(color: Colors.white)
              : Icon(
                  LucideIcons.mic,
                  color: isDisabled ? const Color(0xFF9E9E9E) : Colors.white,
                  size: 32,
                ),
        ),
      ).animate(target: isListening ? 1 : 0)
        .scale(end: const Offset(1.1, 1.1), duration: 200.ms, curve: Curves.easeInOut)
        .shimmer(duration: 1000.ms, color: Colors.white24, angle: 45)
        .callback(callback: (_) {
           if (isListening) {
             // Maybe add continuous pulse if needed using loop
           }
        }),
    );
  }
}
