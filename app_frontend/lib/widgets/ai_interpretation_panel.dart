import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';

class AiInterpretationPanel extends StatelessWidget {
  final String summary;
  final String? intent;

  const AiInterpretationPanel({
    super.key,
    required this.summary,
    this.intent,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: const BoxDecoration(
        color: Color(0xFFFAFAFA),
        border: Border(
          top: BorderSide(color: Color(0xFFEDEAF6)),
          bottom: BorderSide(color: Color(0xFFEDEAF6)),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: const Color(0xFF10B981).withOpacity(0.1),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: const Icon(
                  Icons.verified,
                  size: 16,
                  color: Color(0xFF10B981),
                ),
              ),
              const SizedBox(width: 8),
              const Text(
                'Verified Understanding',
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  color: Color(0xFF2D223A),
                ),
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: const Color(0xFF10B981),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: const Text(
                  'AWAITING OPERATOR',
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                    color: Colors.white,
                    letterSpacing: 0.5,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          const Text(
            'AI Summary of Citizen\'s Request:',
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: Color(0xFF9E9E9E),
            ),
          ),
          const SizedBox(height: 8),
          Text(
            summary,
            style: const TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w500,
              color: Color(0xFF2D223A),
              height: 1.5,
            ),
          ),
        ],
      ),
    ).animate().fadeIn(duration: 400.ms).slideY(begin: 0.1, end: 0);
  }
}

// Made with Bob
