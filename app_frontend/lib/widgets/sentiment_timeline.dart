import 'package:flutter/material.dart';
import '../models/session_models.dart';

class SentimentTimeline extends StatelessWidget {
  final List<SentimentEntry> timeline;

  const SentimentTimeline({
    super.key,
    required this.timeline,
  });

  Color _getSentimentColor(String label) {
    switch (label.toLowerCase()) {
      case 'calm':
      case 'neutral':
        return const Color(0xFF10B981);
      case 'frustration':
      case 'confused':
        return const Color(0xFFF59E0B);
      case 'distress':
      case 'angry':
        return const Color(0xFFEF4444);
      default:
        return const Color(0xFF9E9E9E);
    }
  }

  String _getCurrentSentiment() {
    if (timeline.isEmpty) return 'Neutral';
    final latest = timeline.last;
    if (latest.label.toLowerCase().contains('distress')) {
      return 'Increasing Distress';
    }
    return latest.label;
  }

  @override
  Widget build(BuildContext context) {
    if (timeline.isEmpty) {
      return Container(
        height: 60,
        alignment: Alignment.center,
        child: const Text(
          'No data',
          style: TextStyle(
            fontSize: 12,
            color: Color(0xFF9E9E9E),
          ),
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Current sentiment with arrow
        Row(
          children: [
            Icon(
              Icons.trending_up,
              size: 16,
              color: _getSentimentColor(timeline.last.label),
            ),
            const SizedBox(width: 4),
            Text(
              _getCurrentSentiment(),
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: _getSentimentColor(timeline.last.label),
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        // Timeline bars
        SizedBox(
          height: 40,
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: timeline.map((entry) {
              final height = 40 * entry.score;
              return Expanded(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 2),
                  child: Container(
                    height: height,
                    decoration: BoxDecoration(
                      color: _getSentimentColor(entry.label),
                      borderRadius: const BorderRadius.vertical(
                        top: Radius.circular(2),
                      ),
                    ),
                  ),
                ),
              );
            }).toList(),
          ),
        ),
        const SizedBox(height: 4),
        // Timeline labels
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'CALL SENTIMENT TIMELINE',
              style: TextStyle(
                fontSize: 9,
                fontWeight: FontWeight.w600,
                color: const Color(0xFF9E9E9E),
              ),
            ),
            Text(
              '04:12',
              style: TextStyle(
                fontSize: 9,
                fontWeight: FontWeight.w600,
                color: const Color(0xFF9E9E9E),
              ),
            ),
          ],
        ),
      ],
    );
  }
}

// Made with Bob
