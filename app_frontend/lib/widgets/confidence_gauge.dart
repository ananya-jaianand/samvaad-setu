import 'package:flutter/material.dart';
import 'dart:math' as math;

class ConfidenceGauge extends StatelessWidget {
  final double confidence;

  const ConfidenceGauge({
    super.key,
    required this.confidence,
  });

  @override
  Widget build(BuildContext context) {
    final percentage = (confidence * 100).toInt();
    final color = confidence >= 0.8
        ? const Color(0xFF10B981)
        : confidence >= 0.6
            ? const Color(0xFFF59E0B)
            : const Color(0xFFEF4444);

    return SizedBox(
      width: 100,
      height: 100,
      child: Stack(
        alignment: Alignment.center,
        children: [
          // Background circle
          CustomPaint(
            size: const Size(100, 100),
            painter: _GaugePainter(
              progress: 1.0,
              color: const Color(0xFFF5F5F7),
              strokeWidth: 8,
            ),
          ),
          // Progress circle
          CustomPaint(
            size: const Size(100, 100),
            painter: _GaugePainter(
              progress: confidence,
              color: color,
              strokeWidth: 8,
            ),
          ),
          // Center text
          Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                '$percentage%',
                style: TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.w700,
                  color: color,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _GaugePainter extends CustomPainter {
  final double progress;
  final Color color;
  final double strokeWidth;

  _GaugePainter({
    required this.progress,
    required this.color,
    required this.strokeWidth,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = (size.width - strokeWidth) / 2;
    final rect = Rect.fromCircle(center: center, radius: radius);

    final paint = Paint()
      ..color = color
      ..strokeWidth = strokeWidth
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    const startAngle = -math.pi / 2;
    final sweepAngle = 2 * math.pi * progress;

    canvas.drawArc(rect, startAngle, sweepAngle, false, paint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}

// Made with Bob
