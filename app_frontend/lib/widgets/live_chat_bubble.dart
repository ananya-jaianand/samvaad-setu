import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../models/session_models.dart';

class LiveChatBubble extends StatelessWidget {
  final SessionTurn turn;

  const LiveChatBubble({super.key, required this.turn});

  Color _getStressColor() {
    if (turn.stressLevel == 'HIGH') return const Color(0xFFEF4444);
    if (turn.stressLevel == 'MEDIUM') return const Color(0xFFF59E0B);
    return const Color(0xFF10B981);
  }

  Color _getBubbleColor() {
    if (turn.speaker == 'citizen') {
      if (turn.stressLevel == 'HIGH') {
        return const Color(0xFFFEE2E2); // Light red
      }
      return const Color(0xFFEBF5FF); // Light blue
    }
    return Colors.white;
  }

  @override
  Widget build(BuildContext context) {
    final isCitizen = turn.speaker == 'citizen';
    final isHighStress = turn.stressLevel == 'HIGH';

    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Speaker label with ID
          Padding(
            padding: const EdgeInsets.only(left: 12, bottom: 4),
            child: Row(
              children: [
                Text(
                  isCitizen ? 'CITIZEN [00-95]' : 'AI [00-05]',
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                    color: isCitizen ? const Color(0xFF3B82F6) : const Color(0xFF826695),
                    letterSpacing: 0.5,
                  ),
                ),
                if (isHighStress) ...[
                  const SizedBox(width: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: const Color(0xFFEF4444),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: const [
                        Icon(Icons.warning, size: 10, color: Colors.white),
                        SizedBox(width: 4),
                        Text(
                          'HIGH STRESS',
                          style: TextStyle(
                            fontSize: 9,
                            fontWeight: FontWeight.w700,
                            color: Colors.white,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ],
            ),
          ),

          // Chat bubble
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: _getBubbleColor(),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: isHighStress
                    ? const Color(0xFFEF4444)
                    : isCitizen
                        ? const Color(0xFFBFDBFE)
                        : const Color(0xFFEDEAF6),
                width: isHighStress ? 2 : 1,
              ),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.05),
                  blurRadius: 8,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Main transcript
                Text(
                  turn.rawTranscript,
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w500,
                    color: const Color(0xFF2D223A),
                    height: 1.5,
                  ),
                ),

                // Translation if available
                if (turn.translation != null) ...[
                  const SizedBox(height: 12),
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.7),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: const Color(0xFFEDEAF6)),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.translate, size: 14, color: Color(0xFF9E9E9E)),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            turn.translation!,
                            style: const TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w400,
                              color: Color(0xFF6B7280),
                              fontStyle: FontStyle.italic,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],

                // Frustration indicator for high stress
                if (isHighStress) ...[
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: const Color(0xFFEF4444).withOpacity(0.1),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: const [
                            Icon(Icons.trending_up, size: 12, color: Color(0xFFEF4444)),
                            SizedBox(width: 4),
                            Text(
                              'Frustration: 98%',
                              style: TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                                color: Color(0xFFEF4444),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ],

                // Timestamp
                const SizedBox(height: 8),
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    Text(
                      'AI [00:05]',
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w500,
                        color: const Color(0xFF9E9E9E),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    ).animate().fadeIn(duration: 300.ms).slideY(begin: 0.1, end: 0);
  }
}

// Made with Bob
