import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../models/session_models.dart';

class EscalationCard extends StatelessWidget {
  final EscalationPacket packet;
  final VoidCallback onCorrect;
  final VoidCallback onPartial;
  final VoidCallback onIncorrect;

  const EscalationCard({
    super.key,
    required this.packet,
    required this.onCorrect,
    required this.onPartial,
    required this.onIncorrect,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(
          top: BorderSide(color: Color(0xFFEDEAF6), width: 2),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Action Buttons (Matched Profile section removed)
          Row(
            children: [
              Expanded(
                child: _ActionButton(
                  icon: Icons.check_circle,
                  label: 'CORRECT',
                  color: const Color(0xFF10B981),
                  onTap: onCorrect,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: _ActionButton(
                  icon: Icons.help_outline,
                  label: 'PARTIAL',
                  color: const Color(0xFFF59E0B),
                  onTap: onPartial,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: _ActionButton(
                  icon: Icons.cancel,
                  label: 'INCORRECT',
                  color: const Color(0xFFEF4444),
                  onTap: onIncorrect,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),

          // Escalate Button
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: () {},
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFFEF4444),
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
                elevation: 0,
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: const [
                  Icon(Icons.person_add, size: 20),
                  SizedBox(width: 8),
                  Text(
                    'ESCALATE TO HUMAN AGENT',
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.5,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    ).animate().fadeIn(duration: 400.ms).slideY(begin: 0.2, end: 0);
  }

  Widget _buildInfoRow(String label, String value, {Color? statusColor}) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: const TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w500,
            color: Color(0xFF9E9E9E),
          ),
        ),
        Text(
          value,
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            color: statusColor ?? const Color(0xFF2D223A),
          ),
        ),
      ],
    );
  }
}

class _ActionButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;

  const _ActionButton({
    required this.icon,
    required this.label,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 12),
        decoration: BoxDecoration(
          color: color.withOpacity(0.1),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: color, width: 1.5),
        ),
        child: Column(
          children: [
            Icon(icon, size: 24, color: color),
            const SizedBox(height: 4),
            Text(
              label,
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w700,
                color: color,
                letterSpacing: 0.5,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// Made with Bob
