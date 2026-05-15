import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../models/session_models.dart';
import '../theme/app_theme.dart';

// ─── Department label shortener ───────────────────────────────────────────────

String _shortDept(String dept) {
  // First word or known acronym, max ~28 chars for inline display
  const known = {
    'BWSSB': 'BWSSB',
    'BBMP': 'BBMP',
    'BESCOM': 'BESCOM',
    'HESCOM': 'HESCOM',
    'GESCOM': 'GESCOM',
    'MESCOM': 'MESCOM',
    'KSRTC': 'KSRTC',
    'BMTC': 'BMTC',
    'PWD': 'PWD',
  };
  for (final k in known.keys) {
    if (dept.contains(k)) return known[k]!;
  }
  final parts = dept.split(' ');
  final short = parts.take(4).join(' ');
  return short.length > 32 ? '${short.substring(0, 30)}…' : short;
}

// ─── Trigger-to-copy maps ─────────────────────────────────────────────────────

Map<String, String> _triggerLabel(String trigger, String lang) {
  switch (trigger) {
    case 'confirmed':
      return {
        'kn': 'ದೂರು ದಾಖಲಾಗಿದೆ',
        'hi': 'शिकायत दर्ज हुई',
        'en': 'Complaint submitted',
      };
    case 'escalated':
      return {
        'kn': 'ಏಜೆಂಟ್‌ಗೆ ವರ್ಗಾಯಿಸಲಾಗಿದೆ',
        'hi': 'एजेंट को भेजा गया',
        'en': 'Forwarded to agent',
      };
    default:
      return {
        'kn': 'ಕರೆ ದಾಖಲಾಗಿದೆ',
        'hi': 'कॉल दर्ज हुई',
        'en': 'Call recorded',
      };
  }
}

// ─── Inline ticket card ───────────────────────────────────────────────────────

class TicketCard extends StatelessWidget {
  final TicketInfo ticket;
  final String lang;
  final String fontFamily;

  const TicketCard({
    super.key,
    required this.ticket,
    required this.lang,
    required this.fontFamily,
  });

  Color get _accentColor {
    switch (ticket.trigger) {
      case 'confirmed':
        return AppTheme.teal;
      case 'escalated':
        return AppTheme.saffron;
      default:
        return AppTheme.muted;
    }
  }

  IconData get _icon {
    switch (ticket.trigger) {
      case 'confirmed':
        return Icons.check_circle_outline_rounded;
      case 'escalated':
        return Icons.support_agent_rounded;
      default:
        return Icons.receipt_long_rounded;
    }
  }

  @override
  Widget build(BuildContext context) {
    final accent = _accentColor;
    final labels = _triggerLabel(ticket.trigger, lang);
    final headline = labels[lang] ?? labels['en']!;
    final slaText = lang == 'kn'
        ? '${ticket.slaDays} ಕೆಲಸದ ದಿನಗಳಲ್ಲಿ ಉತ್ತರ'
        : lang == 'hi'
            ? '${ticket.slaDays} कार्य-दिवस में उत्तर'
            : 'Response in ${ticket.slaDays} working days';
    final detailsText =
        lang == 'kn' ? 'ವಿವರಗಳು ›' : lang == 'hi' ? 'विवरण ›' : 'Details ›';

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 28),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 760),
        child: Container(
          padding: const EdgeInsets.fromLTRB(12, 14, 16, 14),
          decoration: BoxDecoration(
            color: Colors.white,
            border: Border(
              top: BorderSide(color: AppTheme.hair),
              right: BorderSide(color: AppTheme.hair),
              bottom: BorderSide(color: AppTheme.hair),
              left: BorderSide(color: accent, width: 4),
            ),
            borderRadius: BorderRadius.circular(14),
            boxShadow: [
              BoxShadow(
                color: accent.withValues(alpha: 0.08),
                blurRadius: 24,
                offset: const Offset(0, 8),
              ),
            ],
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: accent.withValues(alpha: 0.1),
                ),
                child: Icon(_icon, size: 18, color: accent),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      headline,
                      style: TextStyle(
                        fontWeight: FontWeight.w600,
                        fontSize: 13.5,
                        color: AppTheme.ink,
                        fontFamily: fontFamily,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      '${ticket.ticketId}  ·  ${_shortDept(ticket.department)}',
                      style: const TextStyle(
                        fontSize: 12,
                        color: AppTheme.muted,
                        fontFamily: 'JetBrains Mono',
                        letterSpacing: 0.02,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      slaText,
                      style: TextStyle(
                        fontSize: 11.5,
                        color: AppTheme.muted,
                        fontFamily: fontFamily,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              GestureDetector(
                onTap: () => _showDetails(context),
                child: Text(
                  detailsText,
                  style: TextStyle(
                    fontSize: 12.5,
                    color: accent,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _showDetails(BuildContext context) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => _TicketDetailsSheet(
        ticket: ticket,
        lang: lang,
        fontFamily: fontFamily,
      ),
    );
  }
}

// ─── Bottom-sheet details ─────────────────────────────────────────────────────

class _TicketDetailsSheet extends StatelessWidget {
  final TicketInfo ticket;
  final String lang;
  final String fontFamily;

  const _TicketDetailsSheet({
    required this.ticket,
    required this.lang,
    required this.fontFamily,
  });

  @override
  Widget build(BuildContext context) {
    final accent = ticket.trigger == 'confirmed'
        ? AppTheme.teal
        : ticket.trigger == 'escalated'
            ? AppTheme.saffron
            : AppTheme.muted;

    return DraggableScrollableSheet(
      initialChildSize: 0.55,
      minChildSize: 0.35,
      maxChildSize: 0.85,
      expand: false,
      builder: (_, scrollCtrl) => Container(
        decoration: const BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        ),
        child: ListView(
          controller: scrollCtrl,
          padding: const EdgeInsets.fromLTRB(24, 0, 24, 32),
          children: [
            // Drag handle
            Center(
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 12),
                child: Container(
                  width: 36,
                  height: 4,
                  decoration: BoxDecoration(
                    color: const Color(0xFFDDE1E7),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
            ),

            // Status chip row
            Row(
              children: [
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: accent.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Container(
                        width: 6,
                        height: 6,
                        decoration: BoxDecoration(
                            shape: BoxShape.circle, color: accent),
                      ),
                      const SizedBox(width: 6),
                      Text(
                        lang == 'kn'
                            ? 'ಸಲ್ಲಿಸಲಾಗಿದೆ'
                            : lang == 'hi'
                                ? 'सबमिट हुआ'
                                : 'Submitted',
                        style: TextStyle(
                          fontSize: 11.5,
                          fontWeight: FontWeight.w600,
                          color: accent,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),

            // Reference
            _SheetSection(
              label: lang == 'kn'
                  ? 'ಉಲ್ಲೇಖ ಸಂಖ್ಯೆ'
                  : lang == 'hi'
                      ? 'संदर्भ संख्या'
                      : 'Reference number',
              child: Row(
                children: [
                  Text(
                    ticket.ticketId,
                    style: const TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.w700,
                      color: AppTheme.ink,
                      fontFamily: 'JetBrains Mono',
                      letterSpacing: 1.2,
                    ),
                  ),
                  const SizedBox(width: 10),
                  GestureDetector(
                    onTap: () {
                      Clipboard.setData(ClipboardData(text: ticket.ticketId));
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text(
                            lang == 'kn'
                                ? 'ಸಂಖ್ಯೆ ನಕಲು ಮಾಡಲಾಗಿದೆ'
                                : lang == 'hi'
                                    ? 'नंबर कॉपी हुआ'
                                    : 'Reference copied',
                            style: const TextStyle(fontSize: 13),
                          ),
                          duration: const Duration(seconds: 2),
                          behavior: SnackBarBehavior.floating,
                          shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(10)),
                        ),
                      );
                    },
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 10, vertical: 5),
                      decoration: BoxDecoration(
                        color: const Color(0xFFF3F4F6),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(Icons.copy_rounded,
                              size: 13, color: AppTheme.muted),
                          const SizedBox(width: 4),
                          Text(
                            lang == 'kn'
                                ? 'ನಕಲಿಸಿ'
                                : lang == 'hi'
                                    ? 'कॉपी'
                                    : 'Copy',
                            style: const TextStyle(
                                fontSize: 12, color: AppTheme.muted),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // Department
            _SheetSection(
              label: lang == 'kn'
                  ? 'ಇಲಾಖೆ'
                  : lang == 'hi'
                      ? 'विभाग'
                      : 'Department',
              child: Text(
                ticket.department,
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w500,
                  color: AppTheme.ink,
                  fontFamily: fontFamily,
                  height: 1.4,
                ),
              ),
            ),
            const SizedBox(height: 20),

            // Issue summary
            _SheetSection(
              label: lang == 'kn'
                  ? 'ದೂರಿನ ವಿಷಯ'
                  : lang == 'hi'
                      ? 'शिकायत का विषय'
                      : 'Issue',
              child: Text(
                ticket.summary,
                style: TextStyle(
                  fontSize: 13.5,
                  color: AppTheme.ink,
                  fontFamily: fontFamily,
                  height: 1.5,
                ),
              ),
            ),
            const SizedBox(height: 20),

            // Meta row: SLA + District
            Row(
              children: [
                Expanded(
                  child: _SheetSection(
                    label: lang == 'kn'
                        ? 'ಉತ್ತರದ ನಿರೀಕ್ಷಿತ ಅವಧಿ'
                        : lang == 'hi'
                            ? 'अपेक्षित समय'
                            : 'Expected response',
                    child: Text(
                      lang == 'kn'
                          ? '${ticket.slaDays} ಕೆಲಸದ ದಿನ'
                          : lang == 'hi'
                              ? '${ticket.slaDays} कार्य-दिवस'
                              : '${ticket.slaDays} working days',
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                        color: AppTheme.ink,
                        fontFamily: fontFamily,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: _SheetSection(
                    label: lang == 'kn'
                        ? 'ಜಿಲ್ಲೆ'
                        : lang == 'hi'
                            ? 'जिला'
                            : 'District',
                    child: Text(
                      ticket.district
                          .replaceAll('_', ' ')
                          .split(' ')
                          .map((w) =>
                              w.isEmpty ? '' : '${w[0].toUpperCase()}${w.substring(1)}')
                          .join(' '),
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                        color: AppTheme.ink,
                        fontFamily: fontFamily,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

// ─── Sheet section label + content ───────────────────────────────────────────

class _SheetSection extends StatelessWidget {
  final String label;
  final Widget child;
  const _SheetSection({required this.label, required this.child});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label.toUpperCase(),
          style: const TextStyle(
            fontSize: 10.5,
            letterSpacing: 0.08,
            color: AppTheme.muted,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 4),
        child,
      ],
    );
  }
}
