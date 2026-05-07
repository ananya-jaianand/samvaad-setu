import 'dart:convert';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:fl_chart/fl_chart.dart';
import '../theme/app_theme.dart';
import '../config/app_config.dart';

// ─── Data models ─────────────────────────────────────────────────────────────

class _OverviewData {
  final int totalCalls;
  final int escalatedCalls;
  final double avgConfidence;
  final double avgSentimentIntensity;
  final List<_DistrictStat> byDistrict;
  final List<_IntentStat> intentDistribution;
  final List<_ReasonStat> escalationReasons;
  final List<_LangStat> languageDistribution;
  final List<_HourStat> hourlyTrend;

  const _OverviewData({
    required this.totalCalls,
    required this.escalatedCalls,
    required this.avgConfidence,
    required this.avgSentimentIntensity,
    required this.byDistrict,
    required this.intentDistribution,
    required this.escalationReasons,
    required this.languageDistribution,
    required this.hourlyTrend,
  });

  factory _OverviewData.fromJson(Map<String, dynamic> json) {
    final s = json['summary'] as Map<String, dynamic>;
    return _OverviewData(
      totalCalls: (s['total_calls'] as num).toInt(),
      escalatedCalls: (s['escalated_calls'] as num).toInt(),
      avgConfidence: (s['avg_confidence'] as num).toDouble(),
      avgSentimentIntensity: (s['avg_sentiment_intensity'] as num).toDouble(),
      byDistrict: (json['by_district'] as List)
          .map((d) => _DistrictStat.fromJson(d as Map<String, dynamic>))
          .toList(),
      intentDistribution: (json['intent_distribution'] as List)
          .map((d) => _IntentStat.fromJson(d as Map<String, dynamic>))
          .toList(),
      escalationReasons: (json['escalation_reasons'] as List)
          .map((d) => _ReasonStat.fromJson(d as Map<String, dynamic>))
          .toList(),
      languageDistribution: (json['language_distribution'] as List)
          .map((d) => _LangStat.fromJson(d as Map<String, dynamic>))
          .toList(),
      hourlyTrend: (json['hourly_trend'] as List)
          .map((d) => _HourStat.fromJson(d as Map<String, dynamic>))
          .toList(),
    );
  }
}

class _DistrictStat {
  final String id;
  final String label;
  final double lat;
  final double lng;
  final int calls;
  final int escalated;
  final double avgSentiment;
  final String? primaryIntent;

  const _DistrictStat({
    required this.id,
    required this.label,
    required this.lat,
    required this.lng,
    required this.calls,
    required this.escalated,
    required this.avgSentiment,
    this.primaryIntent,
  });

  factory _DistrictStat.fromJson(Map<String, dynamic> j) => _DistrictStat(
        id: j['district'] as String,
        label: j['label'] as String,
        lat: (j['lat'] as num).toDouble(),
        lng: (j['lng'] as num).toDouble(),
        calls: (j['calls'] as num).toInt(),
        escalated: (j['escalated'] as num).toInt(),
        avgSentiment: (j['avg_sentiment'] as num).toDouble(),
        primaryIntent: j['primary_intent'] as String?,
      );
}

class _IntentStat {
  final String id;
  final String label;
  final int count;
  const _IntentStat({required this.id, required this.label, required this.count});
  factory _IntentStat.fromJson(Map<String, dynamic> j) => _IntentStat(
        id: j['intent_id'] as String,
        label: j['label'] as String,
        count: (j['count'] as num).toInt(),
      );
}

class _ReasonStat {
  final String reason;
  final String label;
  final int count;
  const _ReasonStat({required this.reason, required this.label, required this.count});
  factory _ReasonStat.fromJson(Map<String, dynamic> j) => _ReasonStat(
        reason: j['reason'] as String,
        label: j['label'] as String,
        count: (j['count'] as num).toInt(),
      );
}

class _LangStat {
  final String language;
  final String label;
  final int count;
  const _LangStat({required this.language, required this.label, required this.count});
  factory _LangStat.fromJson(Map<String, dynamic> j) => _LangStat(
        language: j['language'] as String,
        label: j['label'] as String,
        count: (j['count'] as num).toInt(),
      );
}

class _HourStat {
  final int hour;
  final int calls;
  final int escalated;
  const _HourStat({required this.hour, required this.calls, required this.escalated});
  factory _HourStat.fromJson(Map<String, dynamic> j) => _HourStat(
        hour: (j['hour'] as num).toInt(),
        calls: (j['calls'] as num).toInt(),
        escalated: (j['escalated'] as num).toInt(),
      );
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

Color _sentimentColor(double intensity) {
  if (intensity < 0.36) return AppTheme.sage;
  if (intensity < 0.56) return AppTheme.amber;
  return AppTheme.red;
}

// ─── Root widget ─────────────────────────────────────────────────────────────

class AnalyticsDashboard extends StatefulWidget {
  const AnalyticsDashboard({super.key});

  @override
  State<AnalyticsDashboard> createState() => _AnalyticsDashboardState();
}

class _AnalyticsDashboardState extends State<AnalyticsDashboard> {
  _OverviewData? _data;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _fetchData();
  }

  Future<void> _fetchData() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final res = await http
          .get(Uri.parse('${AppConfig.backendUrl}/analytics/overview'))
          .timeout(const Duration(seconds: 8));
      if (res.statusCode == 200 && mounted) {
        setState(() {
          _data = _OverviewData.fromJson(
              jsonDecode(res.body) as Map<String, dynamic>);
          _loading = false;
        });
      } else {
        if (mounted) {
          setState(() {
            _error = 'Server returned ${res.statusCode}';
            _loading = false;
          });
        }
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _loading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      color: AppTheme.agentBg,
      child: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? _ErrorView(error: _error!, onRetry: _fetchData)
              : _AnalyticsContent(data: _data!),
    );
  }
}

// ─── Error ────────────────────────────────────────────────────────────────────

class _ErrorView extends StatelessWidget {
  final String error;
  final VoidCallback onRetry;
  const _ErrorView({required this.error, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.wifi_off_rounded, color: AppTheme.muted, size: 40),
          const SizedBox(height: 12),
          const Text('Could not load analytics',
              style: TextStyle(
                  color: AppTheme.ink,
                  fontWeight: FontWeight.w600,
                  fontSize: 14)),
          const SizedBox(height: 4),
          Text(error,
              style: const TextStyle(color: AppTheme.muted, fontSize: 11)),
          const SizedBox(height: 16),
          OutlinedButton(onPressed: onRetry, child: const Text('Retry')),
        ],
      ),
    );
  }
}

// ─── Panel wrapper ────────────────────────────────────────────────────────────

class _Panel extends StatelessWidget {
  final String title;
  final String? subtitle;
  final Widget child;

  const _Panel({required this.title, this.subtitle, required this.child});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border.all(color: AppTheme.hair),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 14, 16, 0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title,
                    style: const TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: AppTheme.ink)),
                if (subtitle != null) ...[
                  const SizedBox(height: 2),
                  Text(subtitle!,
                      style: const TextStyle(
                          fontSize: 10, color: AppTheme.muted)),
                ],
              ],
            ),
          ),
          child,
        ],
      ),
    );
  }
}

// ─── Main content ─────────────────────────────────────────────────────────────

class _AnalyticsContent extends StatelessWidget {
  final _OverviewData data;
  const _AnalyticsContent({required this.data});

  @override
  Widget build(BuildContext context) {
    final escalationPct = data.totalCalls > 0
        ? (data.escalatedCalls / data.totalCalls * 100).round()
        : 0;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ── Header ──────────────────────────────────────────────────────
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Regional Analytics',
                    style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.ink),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    'Karnataka 1092 Helpline · ${data.totalCalls} calls · live overview',
                    style: const TextStyle(
                        fontSize: 11, color: AppTheme.muted),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 16),

          // ── Stat cards ──────────────────────────────────────────────────
          Row(
            children: [
              _StatCard(
                label: 'Total Calls',
                value: '${data.totalCalls}',
                sub: 'today',
                icon: Icons.phone_in_talk_rounded,
                iconColor: AppTheme.teal,
              ),
              const SizedBox(width: 12),
              _StatCard(
                label: 'Escalated',
                value: '$escalationPct%',
                sub: '${data.escalatedCalls} calls',
                icon: Icons.warning_amber_rounded,
                iconColor: AppTheme.red,
              ),
              const SizedBox(width: 12),
              _StatCard(
                label: 'Avg Confidence',
                value: '${(data.avgConfidence * 100).round()}%',
                sub: 'pipeline score',
                icon: Icons.analytics_outlined,
                iconColor: AppTheme.sage,
              ),
              const SizedBox(width: 12),
              _StatCard(
                label: 'Avg Distress',
                value: '${(data.avgSentimentIntensity * 100).round()}%',
                sub: 'sentiment intensity',
                icon: Icons.sentiment_dissatisfied_outlined,
                iconColor: AppTheme.amber,
              ),
            ],
          ),
          const SizedBox(height: 16),

          // ── Map + District bar ───────────────────────────────────────────
          IntrinsicHeight(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Expanded(
                  flex: 55,
                  child: _KarnatakaMapCard(districts: data.byDistrict),
                ),
                const SizedBox(width: 14),
                Expanded(
                  flex: 45,
                  child: _DistrictBarCard(districts: data.byDistrict),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),

          // ── Intent / Reasons / Language row ─────────────────────────────
          IntrinsicHeight(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Expanded(
                  flex: 4,
                  child: _IntentPieCard(intents: data.intentDistribution),
                ),
                const SizedBox(width: 14),
                Expanded(
                  flex: 4,
                  child: _EscalationReasonsCard(
                      reasons: data.escalationReasons),
                ),
                const SizedBox(width: 14),
                Expanded(
                  flex: 4,
                  child: _LanguageCard(languages: data.languageDistribution),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),

          // ── Hourly trend ────────────────────────────────────────────────
          _HourlyTrendCard(trend: data.hourlyTrend),
          const SizedBox(height: 8),
        ],
      ),
    );
  }
}

// ─── Stat card ────────────────────────────────────────────────────────────────

class _StatCard extends StatelessWidget {
  final String label;
  final String value;
  final String sub;
  final IconData icon;
  final Color iconColor;

  const _StatCard({
    required this.label,
    required this.value,
    required this.sub,
    required this.icon,
    required this.iconColor,
  });

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        decoration: BoxDecoration(
          color: Colors.white,
          border: Border.all(color: AppTheme.hair),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Row(
          children: [
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                color: iconColor.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(icon, color: iconColor, size: 18),
            ),
            const SizedBox(width: 12),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(value,
                    style: const TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.ink)),
                const SizedBox(height: 1),
                Text(label,
                    style: const TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w500,
                        color: AppTheme.muted)),
                Text(sub,
                    style: TextStyle(
                        fontSize: 10,
                        color: AppTheme.muted.withValues(alpha: 0.7))),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

// ─── Karnataka map ────────────────────────────────────────────────────────────

class _KarnatakaMapCard extends StatelessWidget {
  final List<_DistrictStat> districts;
  const _KarnatakaMapCard({required this.districts});

  @override
  Widget build(BuildContext context) {
    final maxCalls =
        districts.map((d) => d.calls).fold(0, (a, b) => a > b ? a : b);

    return _Panel(
      title: 'District Activity Map',
      subtitle: 'Karnataka — circle size = call volume · colour = distress',
      child: Column(
        children: [
          const SizedBox(height: 10),
          Container(
            margin: const EdgeInsets.symmetric(horizontal: 16),
            height: 360,
            decoration: BoxDecoration(
              color: const Color(0xFFF2EEE4),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: AppTheme.hair),
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: CustomPaint(
                painter: _KarnatakaMapPainter(
                    districts: districts, maxCalls: maxCalls),
                child: const SizedBox.expand(),
              ),
            ),
          ),
          // Legend
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 10, 16, 14),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const _LegendItem(color: AppTheme.sage, label: 'Calm'),
                const SizedBox(width: 18),
                const _LegendItem(color: AppTheme.amber, label: 'Concerned'),
                const SizedBox(width: 18),
                const _LegendItem(color: AppTheme.red, label: 'Distress'),
                const SizedBox(width: 18),
                Row(
                  children: [
                    Container(
                      width: 14,
                      height: 14,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: Colors.transparent,
                        border: Border.all(
                            color: AppTheme.muted.withValues(alpha: 0.5)),
                      ),
                    ),
                    const SizedBox(width: 4),
                    const Text('size = call volume',
                        style: TextStyle(fontSize: 10, color: AppTheme.muted)),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _LegendItem extends StatelessWidget {
  final Color color;
  final String label;
  const _LegendItem({required this.color, required this.label});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 9,
          height: 9,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 4),
        Text(label,
            style: const TextStyle(fontSize: 10, color: AppTheme.muted)),
      ],
    );
  }
}

// ─── Map painter ──────────────────────────────────────────────────────────────

class _KarnatakaMapPainter extends CustomPainter {
  final List<_DistrictStat> districts;
  final int maxCalls;

  const _KarnatakaMapPainter({required this.districts, required this.maxCalls});

  // Karnataka bounding box
  static const double _latMin = 11.4;
  static const double _latMax = 18.6;
  static const double _lngMin = 73.8;
  static const double _lngMax = 78.6;

  Offset _geo(double lat, double lng, Size size) {
    const padX = 0.07;
    const padY = 0.06;
    final nx = padX + (lng - _lngMin) / (_lngMax - _lngMin) * (1 - padX * 2);
    final ny = padY +
        (1 - (lat - _latMin) / (_latMax - _latMin)) * (1 - padY * 2);
    return Offset(nx * size.width, ny * size.height);
  }

  @override
  void paint(Canvas canvas, Size size) {
    // Subtle grid
    final gridPaint = Paint()
      ..color = const Color(0xFFDDD8CC)
      ..strokeWidth = 0.6;
    for (double lat = 12; lat <= 18; lat++) {
      final p = _geo(lat, _lngMin, size);
      canvas.drawLine(Offset(0, p.dy), Offset(size.width, p.dy), gridPaint);
    }
    for (double lng = 74; lng <= 78; lng++) {
      final p = _geo(_latMin, lng, size);
      canvas.drawLine(Offset(p.dx, 0), Offset(p.dx, size.height), gridPaint);
    }

    // Dots
    for (final d in districts) {
      final pos = _geo(d.lat, d.lng, size);
      final maxR = maxCalls > 0 ? maxCalls.toDouble() : 1;
      final radius = 5.0 + (d.calls / maxR) * 16.0;
      final color = _sentimentColor(d.avgSentiment);

      // Glow for high distress
      if (d.avgSentiment > 0.55) {
        canvas.drawCircle(
          pos,
          radius + 5,
          Paint()
            ..color = color.withValues(alpha: 0.15)
            ..maskFilter =
                const MaskFilter.blur(BlurStyle.normal, 7),
        );
      }

      // Fill
      canvas.drawCircle(
          pos, radius, Paint()..color = color.withValues(alpha: 0.75));

      // Border ring
      canvas.drawCircle(
          pos,
          radius,
          Paint()
            ..color = color
            ..style = PaintingStyle.stroke
            ..strokeWidth = 1.5);

      // Label for high-volume districts
      if (d.calls >= 5) {
        final shortName = d.label.split(' ').first;
        final tp = TextPainter(
          text: TextSpan(
            text: shortName,
            style: TextStyle(
              color: AppTheme.ink.withValues(alpha: 0.85),
              fontSize: 8.5,
              fontWeight: FontWeight.w500,
            ),
          ),
          textDirection: TextDirection.ltr,
        )..layout();
        tp.paint(canvas,
            Offset(pos.dx - tp.width / 2, pos.dy + radius + 2.5));
      }

      // Call count badge for top districts
      if (d.calls >= 9) {
        final badge = TextPainter(
          text: TextSpan(
            text: '${d.calls}',
            style: const TextStyle(
              color: Colors.white,
              fontSize: 8,
              fontWeight: FontWeight.w700,
            ),
          ),
          textDirection: TextDirection.ltr,
        )..layout();
        badge.paint(canvas,
            Offset(pos.dx - badge.width / 2, pos.dy - badge.height / 2));
      }
    }

    // Compass rose (bottom-right corner)
    _drawCompass(canvas, Offset(size.width - 22, size.height - 22));
  }

  void _drawCompass(Canvas canvas, Offset center) {
    final paint = Paint()
      ..color = const Color(0xFFADA89A)
      ..strokeWidth = 1.2
      ..style = PaintingStyle.stroke;
    const r = 9.0;
    canvas.drawCircle(center, r, paint);
    // N arrow
    canvas.drawLine(center, center.translate(0, -r + 2), paint);
    final tp = TextPainter(
      text: const TextSpan(
          text: 'N',
          style: TextStyle(
              color: Color(0xFF9C9786),
              fontSize: 7,
              fontWeight: FontWeight.w700)),
      textDirection: TextDirection.ltr,
    )..layout();
    tp.paint(canvas, center.translate(-tp.width / 2, -r - tp.height + 1));
  }

  @override
  bool shouldRepaint(_KarnatakaMapPainter old) =>
      old.districts != districts || old.maxCalls != maxCalls;
}

// ─── District bar chart ───────────────────────────────────────────────────────

class _DistrictBarCard extends StatelessWidget {
  final List<_DistrictStat> districts;
  const _DistrictBarCard({required this.districts});

  @override
  Widget build(BuildContext context) {
    final sorted = [...districts]
      ..sort((a, b) => b.calls.compareTo(a.calls));
    final top = sorted.take(10).toList();
    if (top.isEmpty) return const SizedBox();
    final maxY = top.first.calls.toDouble() * 1.25;

    return _Panel(
      title: 'Calls by District',
      subtitle: 'Top 10 · colour = avg distress',
      child: Padding(
        padding: const EdgeInsets.fromLTRB(4, 16, 16, 8),
        child: SizedBox(
          height: 400,
          child: BarChart(
            BarChartData(
              alignment: BarChartAlignment.spaceAround,
              maxY: maxY,
              barGroups: top.asMap().entries.map((e) {
                final d = e.value;
                return BarChartGroupData(
                  x: e.key,
                  barRods: [
                    BarChartRodData(
                      toY: d.calls.toDouble(),
                      color: _sentimentColor(d.avgSentiment),
                      width: 18,
                      borderRadius: const BorderRadius.vertical(
                          top: Radius.circular(4)),
                    ),
                  ],
                );
              }).toList(),
              titlesData: FlTitlesData(
                bottomTitles: AxisTitles(
                  sideTitles: SideTitles(
                    showTitles: true,
                    reservedSize: 64,
                    getTitlesWidget: (value, meta) {
                      final idx = value.toInt();
                      if (idx < 0 || idx >= top.length) {
                        return const SizedBox();
                      }
                      return Padding(
                        padding: const EdgeInsets.only(top: 4),
                        child: RotatedBox(
                          quarterTurns: 1,
                          child: Text(
                            top[idx].label,
                            style: const TextStyle(
                                fontSize: 9, color: AppTheme.muted),
                          ),
                        ),
                      );
                    },
                  ),
                ),
                leftTitles: AxisTitles(
                  sideTitles: SideTitles(
                    showTitles: true,
                    reservedSize: 28,
                    interval: math.max(1, (maxY / 5).roundToDouble()),
                    getTitlesWidget: (value, meta) => Text(
                      '${value.toInt()}',
                      style: const TextStyle(
                          fontSize: 9, color: AppTheme.muted),
                    ),
                  ),
                ),
                topTitles: const AxisTitles(
                    sideTitles: SideTitles(showTitles: false)),
                rightTitles: const AxisTitles(
                    sideTitles: SideTitles(showTitles: false)),
              ),
              gridData: FlGridData(
                show: true,
                drawVerticalLine: false,
                horizontalInterval: math.max(1, (maxY / 5).roundToDouble()),
                getDrawingHorizontalLine: (_) =>
                    const FlLine(color: AppTheme.hair, strokeWidth: 0.6),
              ),
              borderData: FlBorderData(show: false),
            ),
          ),
        ),
      ),
    );
  }
}

// ─── Intent pie ───────────────────────────────────────────────────────────────

class _IntentPieCard extends StatefulWidget {
  final List<_IntentStat> intents;
  const _IntentPieCard({required this.intents});

  @override
  State<_IntentPieCard> createState() => _IntentPieCardState();
}

class _IntentPieCardState extends State<_IntentPieCard> {
  int _touched = -1;

  static const _colors = [
    AppTheme.teal,
    AppTheme.saffron,
    AppTheme.sage,
    AppTheme.amber,
    AppTheme.red,
    Color(0xFF6D8BAA),
    Color(0xFF8A7D6E),
    Color(0xFF7AAB8C),
  ];

  @override
  Widget build(BuildContext context) {
    final top = widget.intents.take(7).toList();
    final total = top.fold<int>(0, (s, i) => s + i.count);

    return _Panel(
      title: 'Intent Distribution',
      subtitle: 'Across all calls today',
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
        child: Row(
          children: [
            SizedBox(
              width: 130,
              height: 130,
              child: PieChart(
                PieChartData(
                  pieTouchData: PieTouchData(
                    touchCallback: (event, response) {
                      setState(() {
                        _touched =
                            response?.touchedSection?.touchedSectionIndex ??
                                -1;
                      });
                    },
                  ),
                  centerSpaceRadius: 38,
                  sectionsSpace: 2,
                  sections: top.asMap().entries.map((e) {
                    final isTouched = e.key == _touched;
                    return PieChartSectionData(
                      value: e.value.count.toDouble(),
                      color: _colors[e.key % _colors.length],
                      radius: isTouched ? 46 : 38,
                      title: isTouched
                          ? '${(e.value.count / math.max(1, total) * 100).round()}%'
                          : '',
                      titleStyle: const TextStyle(
                          fontSize: 10,
                          color: Colors.white,
                          fontWeight: FontWeight.w700),
                    );
                  }).toList(),
                ),
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: top.asMap().entries.map((e) {
                  final pct = total > 0
                      ? (e.value.count / total * 100).round()
                      : 0;
                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 3),
                    child: Row(
                      children: [
                        Container(
                          width: 8,
                          height: 8,
                          decoration: BoxDecoration(
                            color: _colors[e.key % _colors.length],
                            shape: BoxShape.circle,
                          ),
                        ),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(e.value.label,
                              style: const TextStyle(
                                  fontSize: 10, color: AppTheme.muted),
                              overflow: TextOverflow.ellipsis),
                        ),
                        const SizedBox(width: 4),
                        Text('$pct%',
                            style: const TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.w600,
                                color: AppTheme.ink)),
                      ],
                    ),
                  );
                }).toList(),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ─── Escalation reasons ───────────────────────────────────────────────────────

class _EscalationReasonsCard extends StatefulWidget {
  final List<_ReasonStat> reasons;
  const _EscalationReasonsCard({required this.reasons});

  @override
  State<_EscalationReasonsCard> createState() => _EscalationReasonsCardState();
}

class _EscalationReasonsCardState extends State<_EscalationReasonsCard> {
  int _touched = -1;

  static const _colors = [AppTheme.red, AppTheme.amber, AppTheme.muted];

  @override
  Widget build(BuildContext context) {
    final total =
        widget.reasons.fold<int>(0, (s, r) => s + r.count);

    return _Panel(
      title: 'Escalation Triggers',
      subtitle: 'Why calls were escalated',
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
        child: Row(
          children: [
            SizedBox(
              width: 120,
              height: 120,
              child: PieChart(
                PieChartData(
                  pieTouchData: PieTouchData(
                    touchCallback: (event, response) {
                      setState(() {
                        _touched =
                            response?.touchedSection?.touchedSectionIndex ??
                                -1;
                      });
                    },
                  ),
                  centerSpaceRadius: 32,
                  sectionsSpace: 2,
                  sections: widget.reasons.asMap().entries.map((e) {
                    final isTouched = e.key == _touched;
                    return PieChartSectionData(
                      value: e.value.count.toDouble(),
                      color: _colors[e.key % _colors.length],
                      radius: isTouched ? 44 : 36,
                      title: isTouched
                          ? '${(e.value.count / math.max(1, total) * 100).round()}%'
                          : '',
                      titleStyle: const TextStyle(
                          fontSize: 10,
                          color: Colors.white,
                          fontWeight: FontWeight.w700),
                    );
                  }).toList(),
                ),
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: widget.reasons.asMap().entries.map((e) {
                  final pct = total > 0
                      ? (e.value.count / total * 100).round()
                      : 0;
                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 5),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Container(
                              width: 8,
                              height: 8,
                              decoration: BoxDecoration(
                                color: _colors[e.key % _colors.length],
                                shape: BoxShape.circle,
                              ),
                            ),
                            const SizedBox(width: 6),
                            Expanded(
                              child: Text(e.value.label,
                                  style: const TextStyle(
                                      fontSize: 10, color: AppTheme.muted),
                                  overflow: TextOverflow.ellipsis),
                            ),
                          ],
                        ),
                        const SizedBox(height: 3),
                        Row(
                          children: [
                            const SizedBox(width: 14),
                            Expanded(
                              child: ClipRRect(
                                borderRadius: BorderRadius.circular(3),
                                child: LinearProgressIndicator(
                                  value: total > 0
                                      ? e.value.count / total
                                      : 0,
                                  backgroundColor: AppTheme.hair,
                                  color: _colors[e.key % _colors.length],
                                  minHeight: 5,
                                ),
                              ),
                            ),
                            const SizedBox(width: 6),
                            Text('$pct%',
                                style: const TextStyle(
                                    fontSize: 10,
                                    fontWeight: FontWeight.w600,
                                    color: AppTheme.ink)),
                          ],
                        ),
                      ],
                    ),
                  );
                }).toList(),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ─── Language distribution ────────────────────────────────────────────────────

class _LanguageCard extends StatelessWidget {
  final List<_LangStat> languages;
  const _LanguageCard({required this.languages});

  static const _langColors = {
    'kn': AppTheme.teal,
    'hi': AppTheme.saffron,
    'en': AppTheme.sage,
  };

  @override
  Widget build(BuildContext context) {
    final total = languages.fold<int>(0, (s, l) => s + l.count);

    return _Panel(
      title: 'Language Mix',
      subtitle: 'Calls by language',
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
        child: Column(
          children: languages.map((lang) {
            final pct = total > 0 ? lang.count / total : 0.0;
            final color = _langColors[lang.language] ?? AppTheme.muted;
            return Padding(
              padding: const EdgeInsets.only(bottom: 14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(lang.label,
                          style: const TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w500,
                              color: AppTheme.ink)),
                      const Spacer(),
                      Text(
                        '${lang.count} · ${(pct * 100).round()}%',
                        style: const TextStyle(
                            fontSize: 11, color: AppTheme.muted),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(4),
                    child: LinearProgressIndicator(
                      value: pct,
                      backgroundColor: AppTheme.hair,
                      color: color,
                      minHeight: 7,
                    ),
                  ),
                ],
              ),
            );
          }).toList(),
        ),
      ),
    );
  }
}

// ─── Hourly trend ─────────────────────────────────────────────────────────────

class _HourlyTrendCard extends StatelessWidget {
  final List<_HourStat> trend;
  const _HourlyTrendCard({required this.trend});

  @override
  Widget build(BuildContext context) {
    if (trend.isEmpty) return const SizedBox();
    final maxY =
        trend.map((t) => t.calls).fold(0, (a, b) => a > b ? a : b).toDouble() *
            1.3;

    return _Panel(
      title: 'Hourly Call Volume',
      subtitle: 'Total calls (teal) vs escalated (dashed red) — today',
      child: Padding(
        padding: const EdgeInsets.fromLTRB(8, 16, 20, 12),
        child: SizedBox(
          height: 160,
          child: LineChart(
            LineChartData(
              lineBarsData: [
                LineChartBarData(
                  spots: trend
                      .map((t) =>
                          FlSpot(t.hour.toDouble(), t.calls.toDouble()))
                      .toList(),
                  isCurved: true,
                  color: AppTheme.teal,
                  barWidth: 2.2,
                  dotData: const FlDotData(show: false),
                  belowBarData: BarAreaData(
                    show: true,
                    color: AppTheme.teal.withValues(alpha: 0.08),
                  ),
                ),
                LineChartBarData(
                  spots: trend
                      .map((t) =>
                          FlSpot(t.hour.toDouble(), t.escalated.toDouble()))
                      .toList(),
                  isCurved: true,
                  color: AppTheme.red,
                  barWidth: 1.6,
                  dotData: const FlDotData(show: false),
                  dashArray: [5, 3],
                ),
              ],
              titlesData: FlTitlesData(
                bottomTitles: AxisTitles(
                  sideTitles: SideTitles(
                    showTitles: true,
                    reservedSize: 22,
                    interval: 2,
                    getTitlesWidget: (value, meta) {
                      final h = value.toInt();
                      final label = h < 12
                          ? '${h}am'
                          : h == 12
                              ? '12pm'
                              : '${h - 12}pm';
                      return Padding(
                        padding: const EdgeInsets.only(top: 4),
                        child: Text(label,
                            style: const TextStyle(
                                fontSize: 9, color: AppTheme.muted)),
                      );
                    },
                  ),
                ),
                leftTitles: AxisTitles(
                  sideTitles: SideTitles(
                    showTitles: true,
                    reservedSize: 28,
                    interval: 4,
                    getTitlesWidget: (value, meta) => Text(
                      '${value.toInt()}',
                      style: const TextStyle(
                          fontSize: 9, color: AppTheme.muted),
                    ),
                  ),
                ),
                topTitles: const AxisTitles(
                    sideTitles: SideTitles(showTitles: false)),
                rightTitles: const AxisTitles(
                    sideTitles: SideTitles(showTitles: false)),
              ),
              gridData: FlGridData(
                show: true,
                drawVerticalLine: false,
                horizontalInterval: 4,
                getDrawingHorizontalLine: (_) =>
                    const FlLine(color: AppTheme.hair, strokeWidth: 0.6),
              ),
              borderData: FlBorderData(show: false),
              minX: trend.first.hour.toDouble(),
              maxX: trend.last.hour.toDouble(),
              minY: 0,
              maxY: maxY,
            ),
          ),
        ),
      ),
    );
  }
}
