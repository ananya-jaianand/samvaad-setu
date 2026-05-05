import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../models/session_models.dart';

class TurnBubble extends StatelessWidget {
  final SessionTurn turn;

  const TurnBubble({super.key, required this.turn});

  @override
  Widget build(BuildContext context) {
    final isCitizen = turn.speaker == 'citizen';
    final bgColor = isCitizen ? const Color(0xFF826695) : Colors.white; 
    final textColor = isCitizen ? Colors.white : const Color(0xFF2D223A);
    final alignment = isCitizen ? CrossAxisAlignment.end : CrossAxisAlignment.start;
    final borderRadius = BorderRadius.only(
      topLeft: const Radius.circular(18),
      topRight: const Radius.circular(18),
      bottomLeft: Radius.circular(isCitizen ? 18 : 6),
      bottomRight: Radius.circular(isCitizen ? 6 : 18),
    );

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0, horizontal: 16.0),
      child: Column(
        crossAxisAlignment: alignment,
        children: [
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (!isCitizen && turn.detectedLanguage != null) ...[
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: const Color(0xFF826695).withOpacity(0.1),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    turn.detectedLanguage!,
                    style: const TextStyle(fontSize: 10, color: Color(0xFF826695), fontWeight: FontWeight.w600),
                  ),
                ),
                const SizedBox(width: 6),
              ],
              Text(
                isCitizen ? 'Citizen' : 'SageBot (1092)',
                style: TextStyle(
                  color: const Color(0xFF826695).withOpacity(0.7),
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
              if (isCitizen && turn.detectedLanguage != null) ...[
                const SizedBox(width: 6),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: const Color(0xFF826695).withOpacity(0.1),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    turn.detectedLanguage!,
                    style: const TextStyle(fontSize: 10, color: Color(0xFF826695), fontWeight: FontWeight.w600),
                  ),
                ),
              ],
            ],
          ).animate().fade(duration: 300.ms),
          const SizedBox(height: 4),
          Container(
            padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
            decoration: BoxDecoration(
              color: bgColor,
              borderRadius: borderRadius,
              boxShadow: [
                BoxShadow(
                  color: isCitizen
                      ? const Color(0xFF826695).withOpacity(0.10)
                      : const Color(0xFF826695).withOpacity(0.06),
                  blurRadius: 8,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  turn.rawTranscript,
                  style: TextStyle(color: textColor, fontSize: 15, fontWeight: FontWeight.w500, height: 1.5),
                ),
                if (turn.translation != null && turn.translation!.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: isCitizen ? Colors.white.withOpacity(0.15) : const Color(0xFFF5F5F7),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: isCitizen ? Colors.white.withOpacity(0.3) : const Color(0xFFEDEAF6)),
                    ),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Icon(Icons.translate, size: 14, color: isCitizen ? Colors.white70 : const Color(0xFF826695)),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(
                            turn.translation!,
                            style: TextStyle(color: isCitizen ? Colors.white.withOpacity(0.9) : const Color(0xFF2D223A).withOpacity(0.8), fontSize: 13, fontStyle: FontStyle.italic),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
                if (turn.aiRephrasing != null && turn.aiRephrasing!.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Divider(color: textColor.withOpacity(0.1), height: 1),
                  const SizedBox(height: 12),
                  Text(
                    'AI Interpretation: ${turn.aiRephrasing}',
                    style: TextStyle(color: textColor.withOpacity(0.7), fontSize: 13, fontStyle: FontStyle.italic),
                  ),
                ],
                if (turn.intent != null && turn.intent!.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: textColor.withOpacity(0.05),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      'Intent: ${turn.intent}',
                      style: TextStyle(color: textColor.withOpacity(0.8), fontSize: 11, fontWeight: FontWeight.w600),
                    ),
                  ),
                ]
              ],
            ),
          ).animate()
            .fade(duration: 400.ms)
            .slideY(begin: 0.1, end: 0, duration: 400.ms, curve: Curves.easeOutQuad),
        ],
      ),
    );
  }
}
