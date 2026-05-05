import 'package:flutter/material.dart';

class CallHeaderBar extends StatelessWidget {
  final String callId;
  final String duration;
  final String language;
  final String matchCode;

  const CallHeaderBar({
    super.key,
    required this.callId,
    required this.duration,
    required this.language,
    required this.matchCode,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(
          bottom: BorderSide(color: Color(0xFFEDEAF6), width: 1),
        ),
      ),
      child: Row(
        children: [
          // Call ID with indicator
          Row(
            children: [
              Container(
                width: 8,
                height: 8,
                decoration: const BoxDecoration(
                  color: Color(0xFFEF4444),
                  shape: BoxShape.circle,
                ),
              ),
              const SizedBox(width: 8),
              Text(
                callId,
                style: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: Color(0xFF2D223A),
                ),
              ),
            ],
          ),
          const SizedBox(width: 16),
          // Hindi badge
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: const Color(0xFF10B981),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(
              language,
              style: const TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w600,
                color: Colors.white,
              ),
            ),
          ),
          const Spacer(),
          // Match code
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: const Color(0xFFF5F5F7),
              borderRadius: BorderRadius.circular(4),
              border: Border.all(color: const Color(0xFFEDEAF6)),
            ),
            child: Row(
              children: [
                const Text(
                  'DIALECT MATCH: ',
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w500,
                    color: Color(0xFF9E9E9E),
                  ),
                ),
                Text(
                  matchCode,
                  style: const TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                    color: Color(0xFF2D223A),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          // Duration
          Text(
            duration,
            style: const TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w600,
              color: Color(0xFF2D223A),
            ),
          ),
        ],
      ),
    );
  }
}

// Made with Bob
