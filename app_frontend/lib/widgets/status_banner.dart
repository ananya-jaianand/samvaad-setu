import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';

class StatusBanner extends StatelessWidget {
  final String text;
  final String subtitle;

  const StatusBanner({
    super.key,
    required this.text,
    required this.subtitle,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF10B981).withOpacity(0.1),
        border: const Border(
          bottom: BorderSide(color: Color(0xFF10B981), width: 2),
        ),
      ),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                width: 8,
                height: 8,
                decoration: const BoxDecoration(
                  color: Color(0xFF10B981),
                  shape: BoxShape.circle,
                ),
              )
                  .animate(onPlay: (controller) => controller.repeat())
                  .fadeIn(duration: 600.ms)
                  .then()
                  .fadeOut(duration: 600.ms),
              const SizedBox(width: 8),
              Text(
                text,
                style: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  color: Color(0xFF10B981),
                  letterSpacing: 0.5,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            subtitle,
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w500,
              color: const Color(0xFF10B981).withOpacity(0.8),
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}

// Made with Bob
