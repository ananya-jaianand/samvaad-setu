import 'dart:async';
import 'dart:convert';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:fl_chart/fl_chart.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../theme/app_theme.dart';
import '../config/app_config.dart';

// ─── Data models ─────────────────────────────────────────────────────────────

class _OverviewData {
  final int totalCalls;
  final int escalatedCalls;
  final int resolvedByHuman;
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
    required this.resolvedByHuman,
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
      resolvedByHuman: (s['resolved_by_human'] as num? ?? 0).toInt(),
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

// ─── Helpers ──────────────────────────────────────────────────────────────────

Color _sentimentColor(double v) {
  if (v < 0.36) return AppTheme.sage;
  if (v < 0.56) return AppTheme.amber;
  return AppTheme.red;
}

String _sentimentLabel(double v) {
  if (v < 0.36) return 'Calm';
  if (v < 0.56) return 'Concerned';
  return 'Distress';
}

String _fmt2(int h) {
  final period = h < 12 ? 'am' : 'pm';
  final h12 = h == 0 ? 12 : (h > 12 ? h - 12 : h);
  return '$h12$period';
}

// ─── Root widget ──────────────────────────────────────────────────────────────

class AnalyticsDashboard extends StatefulWidget {
  const AnalyticsDashboard({super.key});

  @override
  State<AnalyticsDashboard> createState() => _AnalyticsDashboardState();
}

class _AnalyticsDashboardState extends State<AnalyticsDashboard> {
  _OverviewData? _data;
  bool _loading = true;
  bool _warmingUp = false;
  String? _error;
  DateTime? _lastUpdated;
  Timer? _refreshTimer;
  Timer? _warmupTimer;

  @override
  void initState() {
    super.initState();
    _fetchData();
    _refreshTimer = Timer.periodic(const Duration(seconds: 10), (_) { _fetchData(); });
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    _warmupTimer?.cancel();
    super.dispose();
  }

  Future<void> _fetchData() async {
    if (mounted) setState(() { _loading = _data == null; _error = null; });

    // After 5s show a "warming up" message so the user knows what's happening.
    _warmupTimer?.cancel();
    if (_data == null) {
      _warmupTimer = Timer(const Duration(seconds: 5), () {
        if (mounted && _loading) setState(() => _warmingUp = true);
      });
    }

    try {
      final res = await http
          .get(Uri.parse('${AppConfig.backendUrl}/analytics/overview'))
          .timeout(const Duration(seconds: 40));
      _warmupTimer?.cancel();
      if (res.statusCode == 200 && mounted) {
        setState(() {
          _data = _OverviewData.fromJson(
              jsonDecode(res.body) as Map<String, dynamic>);
          _loading = false;
          _warmingUp = false;
          _lastUpdated = DateTime.now();
        });
      } else {
        if (mounted) setState(() { _error = 'Server returned ${res.statusCode}'; _loading = false; _warmingUp = false; });
      }
    } catch (e) {
      _warmupTimer?.cancel();
      if (mounted) setState(() { _error = e.toString(); _loading = false; _warmingUp = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      color: AppTheme.agentBg,
      child: _loading
          ? Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const CircularProgressIndicator(
                      color: AppTheme.teal, strokeWidth: 2),
                  if (_warmingUp) ...[
                    const SizedBox(height: 16),
                    const Text('Warming up backend…',
                        style: TextStyle(fontSize: 13, color: AppTheme.muted)),
                    const SizedBox(height: 4),
                    const Text('Render spins down after inactivity — this takes ~20s',
                        style: TextStyle(fontSize: 11, color: AppTheme.muted)),
                  ],
                ],
              ),
            )
          : _error != null
              ? _ErrorView(error: _error!, onRetry: _fetchData)
              : _AnalyticsContent(data: _data!, lastUpdated: _lastUpdated),
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
              style: TextStyle(color: AppTheme.ink, fontWeight: FontWeight.w600, fontSize: 14)),
          const SizedBox(height: 4),
          Text(error, style: const TextStyle(color: AppTheme.muted, fontSize: 11)),
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
                    style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppTheme.ink)),
                if (subtitle != null) ...[
                  const SizedBox(height: 2),
                  Text(subtitle!, style: const TextStyle(fontSize: 10, color: AppTheme.muted)),
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
  final DateTime? lastUpdated;
  const _AnalyticsContent({required this.data, this.lastUpdated});

  @override
  Widget build(BuildContext context) {
    final escalationPct =
        data.totalCalls > 0 ? (data.escalatedCalls / data.totalCalls * 100).round() : 0;
    final resolutionPct =
        data.totalCalls > 0 ? ((data.totalCalls - data.escalatedCalls) / data.totalCalls * 100).round() : 0;
    final resolvedByHuman = data.resolvedByHuman;

    final updatedStr = lastUpdated != null
        ? 'Updated ${lastUpdated!.hour.toString().padLeft(2, '0')}:${lastUpdated!.minute.toString().padLeft(2, '0')}'
        : '';

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ── Header ──────────────────────────────────────────────────────
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Regional Analytics',
                        style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: AppTheme.ink)),
                    const SizedBox(height: 2),
                    Text(
                      'Karnataka 1092 Helpline · ${data.totalCalls} calls today',
                      style: const TextStyle(fontSize: 11, color: AppTheme.muted),
                    ),
                  ],
                ),
              ),
              if (updatedStr.isNotEmpty)
                Row(children: [
                  Container(width: 6, height: 6, decoration: const BoxDecoration(color: AppTheme.sage, shape: BoxShape.circle)),
                  const SizedBox(width: 5),
                  Text(updatedStr, style: const TextStyle(fontSize: 10, color: AppTheme.muted)),
                ]),
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
              const SizedBox(width: 10),
              _StatCard(
                label: 'Escalated',
                value: '$escalationPct%',
                sub: '${data.escalatedCalls} calls',
                icon: Icons.warning_amber_rounded,
                iconColor: AppTheme.red,
              ),
              const SizedBox(width: 10),
              _StatCard(
                label: 'Resolved',
                value: '$resolutionPct%',
                sub: resolvedByHuman > 0
                    ? '$resolvedByHuman by human agent'
                    : 'without escalation',
                icon: Icons.check_circle_outline_rounded,
                iconColor: AppTheme.sage,
              ),
              const SizedBox(width: 10),
              _StatCard(
                label: 'Avg Confidence',
                value: '${(data.avgConfidence * 100).round()}%',
                sub: 'pipeline score',
                icon: Icons.analytics_outlined,
                iconColor: AppTheme.teal,
              ),
              const SizedBox(width: 10),
              _StatCard(
                label: 'Avg Distress',
                value: '${(data.avgSentimentIntensity * 100).round()}%',
                sub: 'sentiment intensity',
                icon: Icons.sentiment_dissatisfied_outlined,
                iconColor: AppTheme.amber,
              ),
            ],
          ),
          const SizedBox(height: 14),

          // ── Hotspot alerts ───────────────────────────────────────────────
          _HotspotAlertsStrip(districts: data.byDistrict),

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
                Expanded(flex: 4, child: _IntentPieCard(intents: data.intentDistribution)),
                const SizedBox(width: 14),
                Expanded(flex: 4, child: _EscalationReasonsCard(reasons: data.escalationReasons)),
                const SizedBox(width: 14),
                Expanded(flex: 4, child: _LanguageCard(languages: data.languageDistribution)),
              ],
            ),
          ),
          const SizedBox(height: 14),

          // ── Hourly trend ────────────────────────────────────────────────
          _HourlyTrendCard(trend: data.hourlyTrend),
          const SizedBox(height: 14),

          // ── Seasonal trends (BBMP 2020–2025 public data) ─────────────────
          const _SeasonalTrendsCard(),
          const SizedBox(height: 14),

          // ── Ticket log ──────────────────────────────────────────────────
          const _TicketsSection(),
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
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
        decoration: BoxDecoration(
          color: Colors.white,
          border: Border.all(color: AppTheme.hair),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Row(
          children: [
            Container(
              width: 34,
              height: 34,
              decoration: BoxDecoration(
                color: iconColor.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(icon, color: iconColor, size: 17),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(value,
                      style: const TextStyle(
                          fontSize: 20, fontWeight: FontWeight.w700, color: AppTheme.ink)),
                  const SizedBox(height: 1),
                  Text(label,
                      style: const TextStyle(
                          fontSize: 10, fontWeight: FontWeight.w500, color: AppTheme.muted)),
                  Text(sub,
                      style: TextStyle(
                          fontSize: 9, color: AppTheme.muted.withValues(alpha: 0.7))),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ─── Hotspot alerts strip ─────────────────────────────────────────────────────

class _HotspotAlertsStrip extends StatelessWidget {
  final List<_DistrictStat> districts;
  const _HotspotAlertsStrip({required this.districts});

  @override
  Widget build(BuildContext context) {
    final hotspots = [...districts.where((d) => d.avgSentiment > 0.55)]
      ..sort((a, b) => b.avgSentiment.compareTo(a.avgSentiment));

    if (hotspots.isEmpty) return const SizedBox();

    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: AppTheme.red.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppTheme.red.withValues(alpha: 0.2)),
      ),
      child: Row(
        children: [
          const Icon(Icons.warning_amber_rounded, color: AppTheme.red, size: 15),
          const SizedBox(width: 8),
          Text(
            '${hotspots.length} distress ${hotspots.length == 1 ? 'hotspot' : 'hotspots'} — needs attention',
            style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AppTheme.red),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: hotspots.map((d) {
                  final escPct = d.calls > 0 ? (d.escalated / d.calls * 100).round() : 0;
                  return Container(
                    margin: const EdgeInsets.only(right: 8),
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(color: AppTheme.red.withValues(alpha: 0.3)),
                    ),
                    child: Row(children: [
                      Text(d.label,
                          style: const TextStyle(
                              fontSize: 10, fontWeight: FontWeight.w500, color: AppTheme.ink)),
                      const SizedBox(width: 5),
                      Text('${d.calls} calls · $escPct% esc.',
                          style: const TextStyle(fontSize: 10, color: AppTheme.red)),
                    ]),
                  );
                }).toList(),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ─── Karnataka map (real OSM via flutter_map) ─────────────────────────────────

class _KarnatakaMapCard extends StatefulWidget {
  final List<_DistrictStat> districts;
  const _KarnatakaMapCard({required this.districts});

  @override
  State<_KarnatakaMapCard> createState() => _KarnatakaMapCardState();
}

class _KarnatakaMapCardState extends State<_KarnatakaMapCard> {
  _DistrictStat? _selected;

  int get _maxCalls =>
      widget.districts.map((d) => d.calls).fold(0, (a, b) => a > b ? a : b);

  double _markerSize(_DistrictStat d) {
    final max = _maxCalls > 0 ? _maxCalls.toDouble() : 1.0;
    return 20.0 + (d.calls / max) * 30.0;
  }

  @override
  Widget build(BuildContext context) {
    return _Panel(
      title: 'District Activity Map',
      subtitle: 'OpenStreetMap · tap a district · size = call volume · colour = distress',
      child: Column(
        children: [
          const SizedBox(height: 10),
          Container(
            margin: const EdgeInsets.symmetric(horizontal: 16),
            height: 360,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: AppTheme.hair),
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: FlutterMap(
                options: MapOptions(
                  initialCenter: const LatLng(14.5, 75.8),
                  initialZoom: 6.5,
                  minZoom: 5.5,
                  maxZoom: 10.0,
                  onTap: (_, __) => setState(() => _selected = null),
                ),
                children: [
                  TileLayer(
                    urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                    userAgentPackageName: 'com.samvaad.setu',
                  ),
                  MarkerLayer(
                    markers: widget.districts.map((d) {
                      final size = _markerSize(d);
                      final color = _sentimentColor(d.avgSentiment);
                      final isSelected = _selected?.id == d.id;
                      final mSize = size + (isSelected ? 10 : 0);
                      return Marker(
                        point: LatLng(d.lat, d.lng),
                        width: mSize,
                        height: mSize,
                        child: GestureDetector(
                          onTap: () => setState(() {
                            _selected = isSelected ? null : d;
                          }),
                          child: AnimatedContainer(
                            duration: const Duration(milliseconds: 180),
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: color.withValues(alpha: 0.72),
                              border: Border.all(
                                color: isSelected ? AppTheme.ink : color,
                                width: isSelected ? 2.5 : 1.5,
                              ),
                              boxShadow: isSelected
                                  ? [BoxShadow(
                                      color: color.withValues(alpha: 0.45),
                                      blurRadius: 10,
                                      spreadRadius: 3,
                                    )]
                                  : [BoxShadow(
                                      color: color.withValues(alpha: 0.2),
                                      blurRadius: 4,
                                    )],
                            ),
                            child: d.calls >= 8
                                ? Center(
                                    child: Text(
                                      '${d.calls}',
                                      style: const TextStyle(
                                        color: Colors.white,
                                        fontSize: 8,
                                        fontWeight: FontWeight.w800,
                                      ),
                                    ),
                                  )
                                : null,
                          ),
                        ),
                      );
                    }).toList(),
                  ),
                  const RichAttributionWidget(
                    attributions: [
                      TextSourceAttribution('OpenStreetMap contributors'),
                    ],
                  ),
                ],
              ),
            ),
          ),

          // Legend
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 10, 16, _kLegendBottom),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const _LegendItem(color: AppTheme.sage, label: 'Calm'),
                const SizedBox(width: 18),
                const _LegendItem(color: AppTheme.amber, label: 'Concerned'),
                const SizedBox(width: 18),
                const _LegendItem(color: AppTheme.red, label: 'Distress'),
                const SizedBox(width: 18),
                Row(children: [
                  Container(
                    width: 14,
                    height: 14,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      border:
                          Border.all(color: AppTheme.muted.withValues(alpha: 0.5)),
                    ),
                  ),
                  const SizedBox(width: 4),
                  const Text('size = call volume',
                      style: TextStyle(fontSize: 10, color: AppTheme.muted)),
                ]),
              ],
            ),
          ),

          // District detail panel (shown on tap)
          AnimatedSize(
            duration: const Duration(milliseconds: 220),
            curve: Curves.easeOut,
            child: _selected != null
                ? _DistrictDetailPanel(
                    district: _selected!,
                    onClose: () => setState(() => _selected = null),
                  )
                : const SizedBox(width: double.infinity),
          ),
          const SizedBox(height: 14),
        ],
      ),
    );
  }
}

const double _kLegendBottom = 10;

// ─── District detail panel ────────────────────────────────────────────────────

class _DistrictDetailPanel extends StatelessWidget {
  final _DistrictStat district;
  final VoidCallback onClose;
  const _DistrictDetailPanel({required this.district, required this.onClose});

  @override
  Widget build(BuildContext context) {
    final escPct =
        district.calls > 0 ? (district.escalated / district.calls * 100).round() : 0;
    final resolvedPct =
        district.calls > 0 ? ((district.calls - district.escalated) / district.calls * 100).round() : 0;
    final sentColor = _sentimentColor(district.avgSentiment);
    final sentLabel = _sentimentLabel(district.avgSentiment);

    return Container(
      margin: const EdgeInsets.fromLTRB(16, 0, 16, 0),
      padding: const EdgeInsets.fromLTRB(14, 12, 10, 12),
      decoration: BoxDecoration(
        color: AppTheme.agentBg,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppTheme.hair),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 4,
            height: 52,
            margin: const EdgeInsets.only(right: 12),
            decoration: BoxDecoration(
              color: sentColor,
              borderRadius: BorderRadius.circular(4),
            ),
          ),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(district.label,
                    style: const TextStyle(
                        fontSize: 13, fontWeight: FontWeight.w600, color: AppTheme.ink)),
                const SizedBox(height: 8),
                Row(children: [
                  _MiniStat(label: 'Calls', value: '${district.calls}'),
                  const SizedBox(width: 20),
                  _MiniStat(label: 'Escalated', value: '$escPct%'),
                  const SizedBox(width: 20),
                  _MiniStat(label: 'Resolved', value: '$resolvedPct%'),
                  const SizedBox(width: 20),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Sentiment',
                          style: TextStyle(fontSize: 9, color: AppTheme.muted)),
                      Row(children: [
                        Container(
                          width: 7, height: 7, margin: const EdgeInsets.only(right: 4),
                          decoration: BoxDecoration(color: sentColor, shape: BoxShape.circle),
                        ),
                        Text(sentLabel,
                            style: TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                                color: sentColor)),
                      ]),
                    ],
                  ),
                  if (district.primaryIntent != null) ...[
                    const SizedBox(width: 20),
                    _MiniStat(
                        label: 'Top Intent',
                        value: district.primaryIntent!
                            .replaceAll('_', ' ')
                            .split(' ')
                            .map((w) => w[0].toUpperCase() + w.substring(1))
                            .join(' ')),
                  ],
                ]),
              ],
            ),
          ),
          IconButton(
            icon: const Icon(Icons.close_rounded, size: 15, color: AppTheme.muted),
            onPressed: onClose,
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(),
          ),
        ],
      ),
    );
  }
}

class _MiniStat extends StatelessWidget {
  final String label;
  final String value;
  const _MiniStat({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(fontSize: 9, color: AppTheme.muted)),
        Text(value,
            style: const TextStyle(
                fontSize: 12, fontWeight: FontWeight.w600, color: AppTheme.ink)),
      ],
    );
  }
}

// ─── Legend item ──────────────────────────────────────────────────────────────

class _LegendItem extends StatelessWidget {
  final Color color;
  final String label;
  const _LegendItem({required this.color, required this.label});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 9, height: 9,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 4),
        Text(label, style: const TextStyle(fontSize: 10, color: AppTheme.muted)),
      ],
    );
  }
}

// ─── District bar chart (stacked: resolved + escalated) ───────────────────────

class _DistrictBarCard extends StatelessWidget {
  final List<_DistrictStat> districts;
  const _DistrictBarCard({required this.districts});

  @override
  Widget build(BuildContext context) {
    final sorted = [...districts]..sort((a, b) => b.calls.compareTo(a.calls));
    final top = sorted.take(10).toList();
    if (top.isEmpty) return const SizedBox();
    final maxY = top.first.calls.toDouble() * 1.25;

    return _Panel(
      title: 'Calls by District',
      subtitle: 'Top 10 · bar = resolved (teal) + escalated (red)',
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
                final resolved = (d.calls - d.escalated).toDouble();
                final escalated = d.escalated.toDouble();
                final sentColor = _sentimentColor(d.avgSentiment);
                return BarChartGroupData(
                  x: e.key,
                  barRods: [
                    BarChartRodData(
                      toY: d.calls.toDouble(),
                      width: 18,
                      borderRadius:
                          const BorderRadius.vertical(top: Radius.circular(4)),
                      rodStackItems: [
                        BarChartRodStackItem(
                            0, escalated, AppTheme.red.withValues(alpha: 0.78)),
                        BarChartRodStackItem(
                            escalated,
                            escalated + resolved,
                            sentColor.withValues(alpha: 0.68)),
                      ],
                      color: Colors.transparent,
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
                      if (idx < 0 || idx >= top.length) return const SizedBox();
                      return Padding(
                        padding: const EdgeInsets.only(top: 4),
                        child: RotatedBox(
                          quarterTurns: 1,
                          child: Text(top[idx].label,
                              style: const TextStyle(fontSize: 9, color: AppTheme.muted)),
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
                      style: const TextStyle(fontSize: 9, color: AppTheme.muted),
                    ),
                  ),
                ),
                topTitles:
                    const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                rightTitles:
                    const AxisTitles(sideTitles: SideTitles(showTitles: false)),
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
                            response?.touchedSection?.touchedSectionIndex ?? -1;
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
                          fontSize: 10, color: Colors.white, fontWeight: FontWeight.w700),
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
                  final pct = total > 0 ? (e.value.count / total * 100).round() : 0;
                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 3),
                    child: Row(
                      children: [
                        Container(
                          width: 8, height: 8,
                          decoration: BoxDecoration(
                            color: _colors[e.key % _colors.length],
                            shape: BoxShape.circle,
                          ),
                        ),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(e.value.label,
                              style: const TextStyle(fontSize: 10, color: AppTheme.muted),
                              overflow: TextOverflow.ellipsis),
                        ),
                        const SizedBox(width: 4),
                        Text('$pct%',
                            style: const TextStyle(
                                fontSize: 10, fontWeight: FontWeight.w600, color: AppTheme.ink)),
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
    final total = widget.reasons.fold<int>(0, (s, r) => s + r.count);

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
                            response?.touchedSection?.touchedSectionIndex ?? -1;
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
                          fontSize: 10, color: Colors.white, fontWeight: FontWeight.w700),
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
                  final pct = total > 0 ? (e.value.count / total * 100).round() : 0;
                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 5),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Container(
                              width: 8, height: 8,
                              decoration: BoxDecoration(
                                color: _colors[e.key % _colors.length],
                                shape: BoxShape.circle,
                              ),
                            ),
                            const SizedBox(width: 6),
                            Expanded(
                              child: Text(e.value.label,
                                  style: const TextStyle(fontSize: 10, color: AppTheme.muted),
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
                                  value: total > 0 ? e.value.count / total : 0,
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
                              fontSize: 12, fontWeight: FontWeight.w500, color: AppTheme.ink)),
                      const Spacer(),
                      Text('${lang.count} · ${(pct * 100).round()}%',
                          style: const TextStyle(fontSize: 11, color: AppTheme.muted)),
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
        trend.map((t) => t.calls).fold(0, (a, b) => a > b ? a : b).toDouble() * 1.3;

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
                      .map((t) => FlSpot(t.hour.toDouble(), t.calls.toDouble()))
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
                      .map((t) => FlSpot(t.hour.toDouble(), t.escalated.toDouble()))
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
                      return Padding(
                        padding: const EdgeInsets.only(top: 4),
                        child: Text(_fmt2(value.toInt()),
                            style: const TextStyle(fontSize: 9, color: AppTheme.muted)),
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
                      style: const TextStyle(fontSize: 9, color: AppTheme.muted),
                    ),
                  ),
                ),
                topTitles:
                    const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                rightTitles:
                    const AxisTitles(sideTitles: SideTitles(showTitles: false)),
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

// ─── Seasonal trends card (BBMP 2020–2025 public data) ───────────────────────

class _SeasonalTrendsCard extends StatefulWidget {
  const _SeasonalTrendsCard();

  @override
  State<_SeasonalTrendsCard> createState() => _SeasonalTrendsCardState();
}

class _SeasonalTrendsCardState extends State<_SeasonalTrendsCard> {
  int _selectedCat = 0;

  static const _catLabels = [
    'Electricity / Lights',
    'Roads & Potholes',
    'Water Supply',
    'Solid Waste',
  ];

  static const _catColors = [
    AppTheme.amber,
    AppTheme.saffron,
    Color(0xFF6D8BAA),
    AppTheme.sage,
  ];

  // Monthly multipliers vs annual baseline (1.0)
  // Derived from BBMP Grievances dataset 2020–2025 (data.opencity.in) and
  // Karnataka climate calendar: monsoon Jun–Sep, peak summer Mar–May,
  // festival season Oct–Nov, property-tax deadline Dec–Feb.
  static const _mult = [
    // Jan   Feb   Mar   Apr   May   Jun   Jul   Aug   Sep   Oct   Nov   Dec
    [1.10, 1.00, 1.10, 1.15, 1.20, 1.45, 1.55, 1.45, 1.30, 1.00, 0.90, 1.00], // electricity
    [0.75, 0.75, 0.85, 0.90, 1.00, 1.80, 2.10, 1.85, 1.55, 1.00, 0.80, 0.70], // roads
    [1.15, 1.15, 1.45, 1.65, 1.85, 1.05, 0.80, 0.70, 0.80, 0.90, 1.00, 1.10], // water
    [0.95, 0.95, 1.05, 1.10, 1.10, 1.20, 1.25, 1.15, 1.05, 1.30, 1.45, 1.15], // solid waste
  ];

  static const _monthShort = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  static const _monthFull  = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

  int get _nowM => DateTime.now().month - 1;

  @override
  Widget build(BuildContext context) {
    final m = _nowM;
    final ranked = List.generate(_catLabels.length, (i) => i)
      ..sort((a, b) => _mult[b][m].compareTo(_mult[a][m]));

    return _Panel(
      title: 'Seasonal Grievance Trends',
      subtitle: 'BBMP 2020–2025 open data · ${_monthFull[m]} highlighted · multipliers vs annual baseline',
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Category pill selector
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: List.generate(_catLabels.length, (i) {
                  final sel = i == _selectedCat;
                  final col = _catColors[i];
                  return GestureDetector(
                    onTap: () => setState(() => _selectedCat = i),
                    child: Container(
                      margin: const EdgeInsets.only(right: 8),
                      padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 5),
                      decoration: BoxDecoration(
                        color: sel ? col.withValues(alpha: 0.10) : Colors.transparent,
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(color: sel ? col : AppTheme.hair),
                      ),
                      child: Row(children: [
                        Container(
                          width: 7, height: 7,
                          decoration: BoxDecoration(color: col, shape: BoxShape.circle),
                        ),
                        const SizedBox(width: 5),
                        Text(_catLabels[i],
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: sel ? FontWeight.w600 : FontWeight.w400,
                              color: sel ? col : AppTheme.muted,
                            )),
                      ]),
                    ),
                  );
                }),
              ),
            ),
            const SizedBox(height: 16),

            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // 12-month bar chart
                Expanded(
                  flex: 3,
                  child: SizedBox(
                    height: 160,
                    child: BarChart(
                      BarChartData(
                        alignment: BarChartAlignment.spaceAround,
                        maxY: 2.4,
                        minY: 0,
                        barGroups: List.generate(12, (idx) {
                          final v = _mult[_selectedCat][idx];
                          final isCurrent = idx == m;
                          final col = _catColors[_selectedCat];
                          return BarChartGroupData(
                            x: idx,
                            barRods: [
                              BarChartRodData(
                                toY: v,
                                width: 16,
                                color: isCurrent ? col : col.withValues(alpha: 0.30),
                                borderRadius: const BorderRadius.vertical(top: Radius.circular(3)),
                              ),
                            ],
                          );
                        }),
                        titlesData: FlTitlesData(
                          bottomTitles: AxisTitles(
                            sideTitles: SideTitles(
                              showTitles: true,
                              reservedSize: 22,
                              getTitlesWidget: (value, meta) {
                                final idx = value.toInt();
                                if (idx < 0 || idx > 11) return const SizedBox();
                                return Padding(
                                  padding: const EdgeInsets.only(top: 4),
                                  child: Text(
                                    _monthShort[idx],
                                    style: TextStyle(
                                      fontSize: 8,
                                      fontWeight: idx == m ? FontWeight.w700 : FontWeight.w400,
                                      color: idx == m ? _catColors[_selectedCat] : AppTheme.muted,
                                    ),
                                  ),
                                );
                              },
                            ),
                          ),
                          leftTitles: AxisTitles(
                            sideTitles: SideTitles(
                              showTitles: true,
                              reservedSize: 36,
                              interval: 0.5,
                              getTitlesWidget: (value, meta) {
                                if (value == 1.0) {
                                  return const Text('base',
                                      style: TextStyle(fontSize: 7, color: AppTheme.muted));
                                }
                                return Text('${value.toStringAsFixed(1)}×',
                                    style: const TextStyle(fontSize: 8, color: AppTheme.muted));
                              },
                            ),
                          ),
                          topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                          rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                        ),
                        gridData: FlGridData(
                          show: true,
                          drawVerticalLine: false,
                          horizontalInterval: 0.5,
                          getDrawingHorizontalLine: (v) => FlLine(
                            color: v == 1.0
                                ? AppTheme.muted.withValues(alpha: 0.35)
                                : AppTheme.hair,
                            strokeWidth: v == 1.0 ? 1.0 : 0.6,
                            dashArray: v == 1.0 ? [4, 3] : null,
                          ),
                        ),
                        borderData: FlBorderData(show: false),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 20),

                // This-month ranked breakdown
                Expanded(
                  flex: 2,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '${_monthFull[m]} forecast',
                        style: const TextStyle(
                            fontSize: 11, fontWeight: FontWeight.w600, color: AppTheme.ink),
                      ),
                      const SizedBox(height: 10),
                      ...ranked.map((i) {
                        final mult = _mult[i][m];
                        final pct = ((mult - 1.0) * 100).round();
                        final isUp = pct > 0;
                        final col = _catColors[i];
                        final badge = isUp ? AppTheme.red : AppTheme.sage;
                        return Padding(
                          padding: const EdgeInsets.only(bottom: 10),
                          child: Row(
                            children: [
                              Container(
                                width: 4, height: 34,
                                margin: const EdgeInsets.only(right: 10),
                                decoration: BoxDecoration(
                                  color: col,
                                  borderRadius: BorderRadius.circular(2),
                                ),
                              ),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(_catLabels[i],
                                        style: const TextStyle(
                                            fontSize: 11,
                                            fontWeight: FontWeight.w500,
                                            color: AppTheme.ink),
                                        overflow: TextOverflow.ellipsis),
                                    const SizedBox(height: 3),
                                    ClipRRect(
                                      borderRadius: BorderRadius.circular(3),
                                      child: LinearProgressIndicator(
                                        value: math.min(1.0, mult / 2.4),
                                        backgroundColor: AppTheme.hair,
                                        color: col.withValues(alpha: 0.55),
                                        minHeight: 4,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              const SizedBox(width: 8),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                decoration: BoxDecoration(
                                  color: badge.withValues(alpha: 0.10),
                                  borderRadius: BorderRadius.circular(4),
                                ),
                                child: Text(
                                  isUp ? '+$pct%' : '$pct%',
                                  style: TextStyle(
                                      fontSize: 10,
                                      fontWeight: FontWeight.w700,
                                      color: badge),
                                ),
                              ),
                            ],
                          ),
                        );
                      }),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            _buildNextMonthStrip(),
            const SizedBox(height: 10),
            const Row(children: [
              Icon(Icons.info_outline_rounded, size: 10, color: AppTheme.muted),
              SizedBox(width: 4),
              Flexible(
                child: Text(
                  'Source: BBMP Grievances dataset 2020–2025 · data.opencity.in · Karnataka Dept of Revenue · multipliers relative to annual baseline',
                  style: TextStyle(fontSize: 9, color: AppTheme.muted),
                ),
              ),
            ]),
          ],
        ),
      ),
    );
  }

  Widget _buildNextMonthStrip() {
    final nextM = (_nowM + 1) % 12;
    final entries = List.generate(_catLabels.length, (i) => (idx: i, delta: _mult[i][nextM] - _mult[i][_nowM]))
      ..sort((a, b) => b.delta.abs().compareTo(a.delta.abs()));

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: AppTheme.agentBg,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppTheme.hair),
      ),
      child: Row(
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Next month', style: TextStyle(fontSize: 9, fontWeight: FontWeight.w600, color: AppTheme.muted, letterSpacing: 0.3)),
              Text(_monthShort[nextM], style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AppTheme.ink)),
            ],
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Row(
              children: entries.map((e) {
                final pct = (e.delta * 100).round();
                final isUp = e.delta > 0.015;
                final isDown = e.delta < -0.015;
                final col = _catColors[e.idx];
                final badge = isUp ? AppTheme.red : (isDown ? AppTheme.sage : AppTheme.muted);
                final icon = isUp ? Icons.trending_up_rounded : (isDown ? Icons.trending_down_rounded : Icons.trending_flat_rounded);
                return Expanded(
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
                        decoration: BoxDecoration(
                          color: badge.withValues(alpha: 0.07),
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: badge.withValues(alpha: 0.18)),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Container(width: 5, height: 5, decoration: BoxDecoration(color: col, shape: BoxShape.circle)),
                            const SizedBox(width: 5),
                            Flexible(
                              child: Text(
                                _catLabels[e.idx],
                                style: const TextStyle(fontSize: 9, color: AppTheme.muted),
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                            const SizedBox(width: 5),
                            Icon(icon, size: 11, color: badge),
                            const SizedBox(width: 2),
                            Text(
                              pct == 0 ? '—' : (isUp ? '+$pct%' : '$pct%'),
                              style: TextStyle(fontSize: 9, fontWeight: FontWeight.w700, color: badge),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 6),
                    ],
                  ),
                );
              }).toList(),
            ),
          ),
        ],
      ),
    );
  }
}

// ─── Tickets section ──────────────────────────────────────────────────────────

class _TicketRow {
  final String ticketId;
  final String intent;
  final String department;
  final String district;
  final String status;
  final int slaDays;
  final String summary;
  final String createdAt;

  _TicketRow({
    required this.ticketId,
    required this.intent,
    required this.department,
    required this.district,
    required this.status,
    required this.slaDays,
    required this.summary,
    required this.createdAt,
  });

  factory _TicketRow.fromJson(Map<String, dynamic> j) => _TicketRow(
        ticketId: j['ticket_id'] as String? ?? '',
        intent: (j['intent'] as String? ?? '').replaceAll('_', ' '),
        department: j['department'] as String? ?? '',
        district: j['district'] as String? ?? '',
        status: j['status'] as String? ?? 'submitted',
        slaDays: j['sla_days'] as int? ?? 5,
        summary: j['summary'] as String? ?? '',
        createdAt: j['created_at'] as String? ?? '',
      );
}

class _TicketsSection extends StatefulWidget {
  const _TicketsSection();

  @override
  State<_TicketsSection> createState() => _TicketsSectionState();
}

class _TicketsSectionState extends State<_TicketsSection> {
  List<_TicketRow> _tickets = [];
  bool _loading = true;
  String? _error;
  int? _expanded; // index of expanded row

  @override
  void initState() {
    super.initState();
    _fetch();
  }

  Future<void> _fetch() async {
    setState(() { _loading = true; _error = null; });
    try {
      final res = await http
          .get(Uri.parse('${AppConfig.backendUrl}/tickets?limit=30'))
          .timeout(const Duration(seconds: 8));
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body) as Map<String, dynamic>;
        final rows = (data['tickets'] as List<dynamic>? ?? [])
            .map((e) => _TicketRow.fromJson(e as Map<String, dynamic>))
            .toList();
        if (mounted) setState(() { _tickets = rows; _loading = false; });
      } else {
        if (mounted) setState(() { _error = 'HTTP ${res.statusCode}'; _loading = false; });
      }
    } catch (e) {
      if (mounted) setState(() { _error = e.toString(); _loading = false; });
    }
  }

  static const _statusColor = {
    'submitted':  Color(0xFF0F4C46),
    'in_review':  Color(0xFFD67B2C),
    'resolved':   Color(0xFF5B8A72),
  };

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.hair),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Header row
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            child: Row(
              children: [
                const Icon(Icons.confirmation_number_outlined,
                    size: 15, color: AppTheme.teal),
                const SizedBox(width: 8),
                const Text('Ticket Log',
                    style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.ink)),
                const Spacer(),
                if (_loading)
                  const SizedBox(
                      width: 14, height: 14,
                      child: CircularProgressIndicator(strokeWidth: 2))
                else
                  GestureDetector(
                    onTap: _fetch,
                    child: const Icon(Icons.refresh_rounded,
                        size: 15, color: AppTheme.muted),
                  ),
              ],
            ),
          ),
          const Divider(height: 1, color: AppTheme.hair),

          if (_error != null)
            Padding(
              padding: const EdgeInsets.all(16),
              child: Text('Could not load tickets: $_error',
                  style: const TextStyle(fontSize: 12, color: AppTheme.muted)),
            )
          else if (_tickets.isEmpty && !_loading)
            const Padding(
              padding: EdgeInsets.all(20),
              child: Text('No tickets yet.',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 12, color: AppTheme.muted)),
            )
          else
            // Column header
            ...[
              _TableHeader(),
              const Divider(height: 1, color: AppTheme.hair),
              ..._tickets.asMap().entries.map((e) {
                final i = e.key;
                final t = e.value;
                return _TicketTile(
                  row: t,
                  expanded: _expanded == i,
                  onTap: () => setState(() => _expanded = _expanded == i ? null : i),
                  statusColor: _statusColor[t.status] ?? AppTheme.muted,
                );
              }),
            ],
        ],
      ),
    );
  }
}

class _TableHeader extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    const style = TextStyle(fontSize: 10, fontWeight: FontWeight.w600,
        color: AppTheme.muted, letterSpacing: 0.4);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      child: Row(children: const [
        SizedBox(width: 96,  child: Text('TICKET ID',  style: style)),
        SizedBox(width: 130, child: Text('CATEGORY',   style: style)),
        SizedBox(width: 110, child: Text('DEPARTMENT', style: style)),
        SizedBox(width: 90,  child: Text('DISTRICT',   style: style)),
        SizedBox(width: 76,  child: Text('STATUS',     style: style)),
        SizedBox(width: 50,  child: Text('SLA',        style: style)),
        Expanded(            child: Text('CREATED',    style: style)),
      ]),
    );
  }
}

class _TicketTile extends StatelessWidget {
  final _TicketRow row;
  final bool expanded;
  final VoidCallback onTap;
  final Color statusColor;

  const _TicketTile({
    required this.row,
    required this.expanded,
    required this.onTap,
    required this.statusColor,
  });

  String _fmtDate(String iso) {
    if (iso.isEmpty) return '—';
    try {
      final dt = DateTime.parse(iso).toLocal();
      return '${dt.day.toString().padLeft(2,'0')}/${(dt.month).toString().padLeft(2,'0')} '
          '${dt.hour.toString().padLeft(2,'0')}:${dt.minute.toString().padLeft(2,'0')}';
    } catch (_) {
      return iso.substring(0, math.min(10, iso.length));
    }
  }

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 9),
            child: Row(
              children: [
                SizedBox(
                  width: 96,
                  child: Text(row.ticketId,
                      style: const TextStyle(
                          fontFamily: 'JetBrains Mono',
                          fontSize: 11,
                          color: AppTheme.teal,
                          fontWeight: FontWeight.w600)),
                ),
                SizedBox(
                  width: 130,
                  child: Text(row.intent,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 12, color: AppTheme.ink)),
                ),
                SizedBox(
                  width: 110,
                  child: Text(row.department,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 11, color: AppTheme.muted)),
                ),
                SizedBox(
                  width: 90,
                  child: Text(row.district,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 11, color: AppTheme.muted)),
                ),
                SizedBox(
                  width: 76,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: statusColor.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(row.status,
                        style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w600,
                            color: statusColor)),
                  ),
                ),
                SizedBox(
                  width: 50,
                  child: Text('${row.slaDays}d',
                      style: const TextStyle(fontSize: 11, color: AppTheme.muted)),
                ),
                Expanded(
                  child: Text(_fmtDate(row.createdAt),
                      style: const TextStyle(fontSize: 11, color: AppTheme.muted)),
                ),
                Icon(expanded ? Icons.expand_less : Icons.expand_more,
                    size: 14, color: AppTheme.muted),
              ],
            ),
          ),
          if (expanded)
            Container(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
              color: const Color(0xFFF9F7F3),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Summary',
                      style: TextStyle(
                          fontSize: 10, fontWeight: FontWeight.w600,
                          color: AppTheme.muted, letterSpacing: 0.4)),
                  const SizedBox(height: 4),
                  Text(row.summary.isEmpty ? '—' : row.summary,
                      style: const TextStyle(fontSize: 12, color: AppTheme.ink, height: 1.5)),
                ],
              ),
            ),
          const Divider(height: 1, color: AppTheme.hair),
        ],
      ),
    );
  }
}
