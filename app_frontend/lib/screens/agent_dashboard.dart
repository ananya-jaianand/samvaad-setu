import 'dart:async';
import 'dart:convert';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:web_socket_channel/web_socket_channel.dart';
import '../theme/app_theme.dart';
import '../models/session_models.dart';
import '../config/app_config.dart';
import '../services/voice_pipeline_service.dart';

// ─── AgentDashboard ───────────────────────────────────────────────────────────

class AgentDashboard extends StatefulWidget {
  final VoicePipelineService citizenSvc;
  const AgentDashboard({super.key, required this.citizenSvc});

  @override
  State<AgentDashboard> createState() => _AgentDashboardState();
}

class _AgentDashboardState extends State<AgentDashboard> {
  static const _agentId = 'agent-001';

  List<AgentQueueItem> _queue = [];
  int _queueTotal = 0;
  bool _queueLoading = true;

  AgentQueueItem? _activeItem;
  Map<String, dynamic>? _fullContext;
  bool _contextLoading = false;

  String _revealLang = 'en';
  bool _reviewed = false;
  bool _showToast = false;
  String _toastTitle = '';
  String _toastBody = '';
  bool _toastHigh = false;
  String? _toastSessionId;

  Map<String, String> _editedFields = {};

  List<Map<String, dynamic>> _liveTurns = [];
  final TextEditingController _replyCtrl = TextEditingController();

  WebSocketChannel? _agentWs;
  Timer? _pollTimer;

  // ── Live citizen session (shared VoicePipelineService) ────────────────────
  List<SessionTurn> _citizenLiveTurns = [];
  ConfidenceScore? _liveConfidence;
  SessionMeta? _citizenSessionMeta;
  StreamSubscription<List<SessionTurn>>? _citizenTurnsSub;
  StreamSubscription<ConfidenceScore?>? _citizenConfSub;
  StreamSubscription<SessionMeta?>? _citizenMetaSub;

  @override
  void initState() {
    super.initState();
    _seedThenFetch();
    _connectAgentWs();
    _pollTimer = Timer.periodic(const Duration(seconds: 15), (_) => _fetchQueue());

    _citizenTurnsSub = widget.citizenSvc.turnsStream.listen((turns) {
      if (mounted) setState(() => _citizenLiveTurns = turns);
    });
    _citizenConfSub = widget.citizenSvc.confidenceStream.listen((conf) {
      if (mounted && conf != null) setState(() => _liveConfidence = conf);
    });
    _citizenMetaSub = widget.citizenSvc.sessionMetaStream.listen((meta) {
      if (mounted && meta != null) setState(() => _citizenSessionMeta = meta);
    });
  }

  @override
  void dispose() {
    _agentWs?.sink.close();
    _pollTimer?.cancel();
    _replyCtrl.dispose();
    _citizenTurnsSub?.cancel();
    _citizenConfSub?.cancel();
    _citizenMetaSub?.cancel();
    super.dispose();
  }

  // ─── Backend calls ────────────────────────────────────────────────────────

  Future<void> _seedThenFetch() async {
    try {
      await http
          .post(Uri.parse('${AppConfig.backendUrl}/demo/seed-agent-queue'))
          .timeout(const Duration(seconds: 10));
    } catch (_) {}
    await _fetchQueue();
  }

  Future<void> _fetchQueue() async {
    try {
      final res = await http
          .get(Uri.parse('${AppConfig.backendUrl}/agent/queue?limit=20'))
          .timeout(const Duration(seconds: 5));
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        final items = (data['items'] as List<dynamic>? ?? [])
            .map((e) => AgentQueueItem.fromJson(e))
            .toList();
        if (mounted) {
          setState(() {
            _queue = items;
            _queueTotal = data['total'] ?? items.length;
            _queueLoading = false;
          });
          // Auto-select first if nothing selected
          if (_activeItem == null && items.isNotEmpty) {
            _selectItem(items.first);
          }
        }
      }
    } catch (_) {
      if (mounted) setState(() => _queueLoading = false);
    }
  }

  Future<void> _selectItem(AgentQueueItem item) async {
    setState(() {
      _activeItem = item;
      _fullContext = null;
      _liveTurns = [];
      _contextLoading = true;
      _reviewed = false;
      _editedFields = {};
    });
    try {
      final res = await http
          .get(Uri.parse(
              '${AppConfig.backendUrl}/sessions/${item.sessionId}/full-context'))
          .timeout(const Duration(seconds: 6));
      if (res.statusCode == 200 && mounted) {
        setState(() {
          _fullContext = jsonDecode(res.body);
          _contextLoading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _contextLoading = false);
    }
  }

  Future<void> _sendCorrection(String field, String value) async {
    if (_activeItem == null) return;
    setState(() => _editedFields[field] = value);
    try {
      await http.post(
        Uri.parse(
            '${AppConfig.backendUrl}/sessions/${_activeItem!.sessionId}/agent-correction'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(
            {'field': field, 'value': value, 'agent_id': _agentId}),
      );
    } catch (_) {}
  }

  void _sendAgentReply() {
    final text = _replyCtrl.text.trim();
    print('[AGENT_REPLY_DEBUG] text: "$text", activeItem: ${_activeItem?.sessionId}, agentWs: ${_agentWs != null}');

    if (text.isEmpty) {
      print('[AGENT_REPLY_DEBUG] Aborting: text is empty');
      return;
    }
    if (_activeItem == null) {
      print('[AGENT_REPLY_DEBUG] Aborting: no active item selected');
      return;
    }
    if (_agentWs == null) {
      print('[AGENT_REPLY_DEBUG] Aborting: agent WebSocket not connected');
      return;
    }

    try {
      final payload = {
        'type': 'agent_reply',
        'session_id': _activeItem!.sessionId,
        'text': text,
      };
      print('[AGENT_REPLY_DEBUG] Sending payload: ${jsonEncode(payload)}');
      _agentWs!.sink.add(jsonEncode(payload));
      print('[AGENT_REPLY_DEBUG] Message sent successfully');
    } catch (e) {
      print('[AGENT_REPLY_DEBUG] Error sending message: $e');
      return;
    }

    // Optimistic update: add to the visible turn list immediately.
    // For live sessions the ConvPane renders _citizenLiveTurns (from the shared
    // VoicePipelineService), so add there directly. For demo/escalated sessions
    // _liveTurns is the right place.
    final optimisticTurn = SessionTurn(
      speaker: 'agent',
      rawTranscript: text,
    );
    setState(() {
      if (_isViewingLiveSession) {
        _citizenLiveTurns = [..._citizenLiveTurns, optimisticTurn];
      } else {
        _liveTurns.add({
          'speaker': 'agent',
          'raw_transcript': text,
          'timestamp': DateTime.now().toIso8601String(),
        });
      }
    });
    _replyCtrl.clear();
  }

  Future<void> _resolveSession() async {
    if (_activeItem == null || !_reviewed) return;
    try {
      await http.post(
        Uri.parse(
            '${AppConfig.backendUrl}/sessions/${_activeItem!.sessionId}/resolve'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'agent_id': _agentId}),
      );
      _showToastMsg(
        title: 'Session resolved · ${_activeItem!.district}',
        body: 'Closure note logged. Removed from queue.',
        high: false,
      );
      await _fetchQueue();
      setState(() {
        _activeItem = null;
        _fullContext = null;
      });
    } catch (_) {}
  }

  void _connectAgentWs() {
    final wsUri = Uri.parse(
        '${AppConfig.wsUrl.replaceFirst('/ws', '/ws/agent')}/$_agentId');
    print('[AGENT_WS_DEBUG] Connecting to: $wsUri');
    try {
      _agentWs = WebSocketChannel.connect(wsUri);
      print('[AGENT_WS_DEBUG] WebSocket instance created');
      _agentWs!.stream.listen(
        (msg) {
          print('[AGENT_WS_DEBUG] Received message: ${msg.toString().substring(0, math.min(100, msg.toString().length))}');
          try {
            final data = jsonDecode(msg as String);
            final type = data['type'] as String? ?? '';

            if (type == 'queue_snapshot') {
              // Populate queue on WebSocket connect (reliable alternative to HTTP fetch)
              final items = (data['items'] as List<dynamic>? ?? [])
                  .map((e) => AgentQueueItem.fromJson(e as Map<String, dynamic>))
                  .toList();
              if (mounted) {
                setState(() {
                  _queue = items;
                  _queueTotal = data['total'] ?? items.length;
                  _queueLoading = false;
                });
                if (_activeItem == null && items.isNotEmpty) {
                  _selectItem(items.first);
                }
              }
            } else if (type == 'new_escalation') {
              final packet = data['packet'] as Map<String, dynamic>? ?? {};
              _showToastMsg(
                title: 'New high-priority escalation',
                body:
                    '${packet['district'] ?? ''} · ${packet['detected_language']?.toString().toUpperCase() ?? ''} · ${packet['summary'] ?? ''}',
                high: true,
                sessionId: packet['session_id'] as String?,
              );
              _fetchQueue();
            } else if (type == 'session_update') {
              final s = data['session'] as Map<String, dynamic>? ?? {};
              final item = AgentQueueItem.fromJson(s);
              if (mounted) {
                setState(() {
                  final idx = _queue.indexWhere((q) => q.sessionId == item.sessionId);
                  if (idx >= 0) {
                    _queue[idx] = item;
                  } else {
                    _queue.add(item);
                  }
                  _queueTotal = _queue.length;
                  _queueLoading = false;
                });
                if (_activeItem == null && _queue.isNotEmpty) {
                  _selectItem(_queue.first);
                }
              }
              // Notify agent when a new citizen call connects from another tab
              if (!(s['is_escalated'] as bool? ?? false)) {
                final district = s['district'] as String? ?? '';
                final lang = (s['language'] as String? ?? '').toUpperCase();
                _showToastMsg(
                  title: 'New active call · $district',
                  body: '$lang · ${s['summary'] ?? 'Citizen connected'}',
                  high: false,
                );
              }
            } else if (type == 'session_live_update') {
              final sessionId = data['session_id'] as String? ?? '';
              // Update queue card with latest state
              final sessionMeta = data['session'] as Map<String, dynamic>? ?? {};
              if (sessionMeta.isNotEmpty && mounted) {
                final updated = AgentQueueItem.fromJson(sessionMeta);
                setState(() {
                  final idx = _queue.indexWhere((q) => q.sessionId == sessionId);
                  if (idx >= 0) _queue[idx] = updated;
                });
              }
              // Append new turns and update live metrics for the active session
              if (sessionId == _activeItem?.sessionId && mounted) {
                setState(() {
                  if (data['citizen_turn'] != null) {
                    _liveTurns.add(data['citizen_turn'] as Map<String, dynamic>);
                  }
                  if (data['ai_turn'] != null) {
                    _liveTurns.add(data['ai_turn'] as Map<String, dynamic>);
                  }
                  // Update live confidence when not viewing the citizen's own service
                  if (data['confidence_score'] != null && !_isViewingLiveSession) {
                    _liveConfidence = ConfidenceScore.fromJson(
                        data['confidence_score'] as Map<String, dynamic>);
                  }
                });
              } else if (sessionId != _activeItem?.sessionId && mounted) {
                // Citizen talking in another session — show notification
                final citizenTurn = data['citizen_turn'] as Map<String, dynamic>?;
                final snippet = citizenTurn?['raw_transcript'] as String? ?? '';
                final district = sessionMeta['district'] as String? ?? sessionId.substring(0, 8);
                final lang = (sessionMeta['language'] as String? ?? '').toUpperCase();
                _showToastMsg(
                  title: 'Citizen speaking · $district · $lang',
                  body: snippet.length > 100 ? '${snippet.substring(0, 100)}…' : snippet,
                  high: false,
                );
              }
            } else if (type == 'session_ended') {
              final sessionId = data['session_id'] as String? ?? '';
              if (mounted) {
                setState(() {
                  _queue.removeWhere((q) => q.sessionId == sessionId);
                  _queueTotal = _queue.length;
                  if (_activeItem?.sessionId == sessionId) {
                    _activeItem = null;
                    _fullContext = null;
                    _liveTurns = [];
                  }
                });
              }
            }
          } catch (_) {}
        },
        onError: (_) {},
        onDone: () {},
      );
      _agentWs!.sink.add(jsonEncode({'type': 'ping'}));
    } catch (_) {}
  }

  void _showToastMsg(
      {required String title,
      required String body,
      required bool high,
      String? sessionId}) {
    setState(() {
      _showToast = true;
      _toastTitle = title;
      _toastBody = body;
      _toastHigh = high;
      _toastSessionId = sessionId;
    });
    Future.delayed(Duration(milliseconds: high ? 6500 : 3500), () {
      if (mounted) setState(() => _showToast = false);
    });
  }

  void _switchToToastSession() {
    final sid = _toastSessionId;
    if (sid == null) return;
    setState(() => _showToast = false);
    final idx = _queue.indexWhere((q) => q.sessionId == sid);
    if (idx >= 0) {
      _selectItem(_queue[idx]);
    } else {
      // Session not in queue yet — re-fetch then select
      _fetchQueue().then((_) {
        final i = _queue.indexWhere((q) => q.sessionId == sid);
        if (i >= 0 && mounted) _selectItem(_queue[i]);
      });
    }
  }

  // ─── Live session helpers ─────────────────────────────────────────────────

  bool get _isViewingLiveSession =>
      _activeItem?.sessionId == widget.citizenSvc.sessionId &&
      widget.citizenSvc.sessionId != null;

  Future<void> _selectLiveSession() async {
    final sid = widget.citizenSvc.sessionId;
    if (sid == null) return;

    final existingIdx = _queue.indexWhere((q) => q.sessionId == sid);
    if (existingIdx >= 0) {
      _selectItem(_queue[existingIdx]);
      return;
    }

    final item = AgentQueueItem(
      sessionId: sid,
      district: widget.citizenSvc.currentDistrict,
      language: widget.citizenSvc.currentLanguage,
      sentiment: _citizenSessionMeta?.currentSentiment ?? 'calm',
      sentimentIntensity: _liveConfidence?.sentimentIntensity ?? 0.3,
      reason: 'active',
      summary: _citizenLiveTurns.isNotEmpty
          ? _citizenLiveTurns.last.displayText
          : 'Live call in progress',
      createdAt: DateTime.now().toIso8601String(),
    );

    setState(() {
      _activeItem = item;
      _fullContext = null;
      _liveTurns = [];
      _contextLoading = true;
      _reviewed = false;
      _editedFields = {};
    });

    try {
      final res = await http
          .get(Uri.parse('${AppConfig.backendUrl}/sessions/$sid/full-context'))
          .timeout(const Duration(seconds: 6));
      if (res.statusCode == 200 && mounted) {
        setState(() {
          _fullContext = jsonDecode(res.body);
          _contextLoading = false;
        });
      } else {
        if (mounted) setState(() => _contextLoading = false);
      }
    } catch (_) {
      if (mounted) setState(() => _contextLoading = false);
    }
  }

  // ─── Derived data ─────────────────────────────────────────────────────────

  List<Map<String, dynamic>> get _transcript {
    if (_fullContext == null) return [];
    return (_fullContext!['transcript'] as List<dynamic>? ?? [])
        .cast<Map<String, dynamic>>();
  }

  List<Map<String, dynamic>> get _sentTimeline {
    if (_fullContext == null) return [];
    return (_fullContext!['sentiment_timeline'] as List<dynamic>? ?? [])
        .cast<Map<String, dynamic>>();
  }

  Map<String, dynamic> get _interpFields {
    if (_fullContext == null) return {};
    final si = _fullContext!['structured_intent'] as Map<String, dynamic>? ?? {};
    return {
      'intent': _editedFields['intent'] ??
          si['intent_id'] ??
          _activeItem?.finalIntent ??
          '',
      'label': si['label_en'] ?? '',
      'department': _editedFields['department'] ??
          si['responsible_department'] ?? '',
      'urgency': _activeItem?.priorityLabel ?? 'low',
      'dialect': _fullContext!['dialect_tag'] ?? '',
      'summary': _editedFields['summary'] ??
          _activeItem?.summary ?? '',
    };
  }

  // ─── Build ────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final sw = MediaQuery.of(context).size.width;

    return Stack(
      children: [
        Column(
          children: [
            _AgBar(
              queueTotal: _queueTotal,
              reviewed: _reviewed,
              onResolve: _resolveSession,
            ),
            _AgSubBar(
              revealLang: _revealLang,
              onLangChange: (l) => setState(() => _revealLang = l),
            ),
            Expanded(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Left: queue (25%)
                  SizedBox(
                    width: sw * 0.25,
                    child: _QueuePane(
                      queue: _queue,
                      loading: _queueLoading,
                      activeSessionId: _activeItem?.sessionId,
                      onSelect: _selectItem,
                      liveSessionId: widget.citizenSvc.sessionId,
                      liveDistrict: widget.citizenSvc.currentDistrict,
                      liveTurnCount: _citizenLiveTurns.length,
                      onSelectLive: _selectLiveSession,
                    ),
                  ),
                  // Center: conversation (45%)
                  Expanded(
                    flex: 45,
                    child: Column(
                      children: [
                        Expanded(
                          child: _ConvPane(
                            item: _activeItem,
                            context: _fullContext,
                            loading: _contextLoading,
                            // When viewing the live session, use citizenSvc turns directly
                            transcript: _isViewingLiveSession
                                ? _citizenLiveTurns.map((t) => t.toAgentMap()).toList()
                                : _transcript,
                            liveTurns: _isViewingLiveSession ? const [] : _liveTurns,
                            sentTimeline: _isViewingLiveSession &&
                                    _citizenSessionMeta != null
                                ? _citizenSessionMeta!.sentimentTimeline
                                    .map((e) => {
                                          'label': e.label,
                                          'intensity': e.intensity,
                                          'timestamp': e.timestamp,
                                        })
                                    .toList()
                                : _sentTimeline,
                            revealLang: _revealLang,
                            isLive: _isViewingLiveSession,
                          ),
                        ),
                        if (_activeItem != null)
                          _AgentReplyBar(
                            controller: _replyCtrl,
                            onSend: _sendAgentReply,
                          ),
                      ],
                    ),
                  ),
                  // Right: interpretation (30%)
                  SizedBox(
                    width: sw * 0.30,
                    child: _InterpPane(
                      item: _activeItem,
                      fields: _interpFields,
                      reviewed: _reviewed,
                      onApprove: () => setState(() => _reviewed = true),
                      onUpdate: _sendCorrection,
                      liveConfidence: _isViewingLiveSession ? _liveConfidence : null,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
        if (_showToast)
          Positioned(
            top: 90,
            right: 18,
            child: _Toast(
              title: _toastTitle,
              body: _toastBody,
              high: _toastHigh,
              onDismiss: () => setState(() => _showToast = false),
              onSwitchToSession:
                  _toastSessionId != null ? _switchToToastSession : null,
            ),
          ),
      ],
    );
  }
}

// ─── Top bar ──────────────────────────────────────────────────────────────────

class _AgBar extends StatelessWidget {
  final int queueTotal;
  final bool reviewed;
  final VoidCallback onResolve;

  const _AgBar({
    required this.queueTotal,
    required this.reviewed,
    required this.onResolve,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 10),
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(bottom: BorderSide(color: AppTheme.hair)),
      ),
      child: Row(
        children: [
          Row(children: [
            Container(
              width: 28,
              height: 28,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(8),
                gradient: const LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [AppTheme.teal, AppTheme.teal2]),
              ),
              child: const Center(
                child: Text('S',
                    style: TextStyle(
                        color: Color(0xFFF6E2BF),
                        fontWeight: FontWeight.w700,
                        fontSize: 13)),
              ),
            ),
            const SizedBox(width: 10),
            const Text('Samvaad-Setu',
                style: TextStyle(
                    fontWeight: FontWeight.w600,
                    color: AppTheme.teal2,
                    fontSize: 13)),
            const Text(' · Agent',
                style: TextStyle(color: AppTheme.muted, fontSize: 13)),
          ]),
          const SizedBox(width: 18),
          Expanded(
            child: Container(
              constraints: const BoxConstraints(maxWidth: 480),
              padding:
                  const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
              decoration: BoxDecoration(
                color: const Color(0xFFF4F2EC),
                border: Border.all(color: AppTheme.hair),
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Row(
                children: [
                  Icon(Icons.search, size: 14, color: AppTheme.muted),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                        'Search by district, intent, session id…',
                        style:
                            TextStyle(fontSize: 13, color: AppTheme.muted)),
                  ),
                  Text('⌘K',
                      style: TextStyle(
                          fontSize: 11,
                          color: AppTheme.muted,
                          fontFamily: 'JetBrains Mono')),
                ],
              ),
            ),
          ),
          const Spacer(),
          // Queue badge
          Container(
            padding: const EdgeInsets.fromLTRB(8, 5, 10, 5),
            decoration: BoxDecoration(
              color: Colors.white,
              border: Border.all(color: AppTheme.hair),
              borderRadius: BorderRadius.circular(999),
            ),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 8, vertical: 1),
                decoration: BoxDecoration(
                  color: AppTheme.saffron,
                  borderRadius: BorderRadius.circular(999),
                ),
                child: Text('$queueTotal',
                    style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w600,
                        fontSize: 11.5)),
              ),
              const SizedBox(width: 8),
              const Text('in queue',
                  style: TextStyle(fontSize: 12.5)),
            ]),
          ),
          const SizedBox(width: 14),
          // Agent identity
          const Row(children: [
            CircleAvatar(
                radius: 15,
                backgroundColor: AppTheme.teal,
                child: Text('PR',
                    style: TextStyle(
                        color: Color(0xFFF6E2BF),
                        fontSize: 12,
                        fontWeight: FontWeight.w600))),
            SizedBox(width: 8),
            Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Priya Rao',
                  style: TextStyle(
                      fontWeight: FontWeight.w600,
                      fontSize: 12.5,
                      color: AppTheme.ink)),
              Text('AGT-1092-021',
                  style: TextStyle(
                      fontSize: 11,
                      color: AppTheme.muted,
                      fontFamily: 'JetBrains Mono')),
            ]),
          ]),
          const SizedBox(width: 14),
          // Resolve button
          GestureDetector(
            onTap: reviewed ? onResolve : null,
            child: Container(
              padding:
                  const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
              decoration: BoxDecoration(
                color: reviewed ? AppTheme.teal : const Color(0xFFE6E2D7),
                border: Border.all(
                    color: reviewed
                        ? AppTheme.teal2
                        : const Color(0xFFDCD6C4)),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                Icon(Icons.check,
                    size: 14,
                    color: reviewed
                        ? const Color(0xFFFFF7E5)
                        : const Color(0xFF9C9786)),
                const SizedBox(width: 8),
                Text('Resolve session',
                    style: TextStyle(
                        fontSize: 13,
                        fontWeight: reviewed
                            ? FontWeight.w600
                            : FontWeight.w500,
                        color: reviewed
                            ? const Color(0xFFFFF7E5)
                            : const Color(0xFF9C9786))),
                const SizedBox(width: 6),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                  decoration: BoxDecoration(
                    color: reviewed
                        ? Colors.white.withValues(alpha: 0.18)
                        : Colors.transparent,
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text('R',
                      style: TextStyle(
                          fontSize: 10.5,
                          fontFamily: 'JetBrains Mono',
                          color: reviewed
                              ? const Color(0xFFFFF7E5)
                                  .withValues(alpha: 0.7)
                              : const Color(0xFF9C9786))),
                ),
              ]),
            ),
          ),
        ],
      ),
    );
  }
}

// ─── Sub-bar ──────────────────────────────────────────────────────────────────

class _AgSubBar extends StatelessWidget {
  final String revealLang;
  final ValueChanged<String> onLangChange;
  const _AgSubBar(
      {required this.revealLang, required this.onLangChange});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 6),
      decoration: const BoxDecoration(
          color: Colors.white,
          border: Border(bottom: BorderSide(color: AppTheme.hair))),
      child: Row(
        children: [
          _kbd('A', 'approve'),
          _kbd('E', 'edit'),
          _kbd('R', 'resolve'),
          _kbd('↑↓', 'queue'),
          const Spacer(),
          const Text('Transcript language',
              style: TextStyle(
                  fontSize: 11.5,
                  color: AppTheme.muted,
                  letterSpacing: 0.04)),
          const SizedBox(width: 8),
          ...['en', 'kn', 'hi'].map((l) {
            final active = revealLang == l;
            return GestureDetector(
              onTap: () => onLangChange(l),
              child: Container(
                margin: const EdgeInsets.only(left: 4),
                padding:
                    const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: active ? AppTheme.ink : Colors.white,
                  border: Border.all(color: AppTheme.hair),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(l.toUpperCase(),
                    style: TextStyle(
                        fontSize: 11,
                        color: active
                            ? const Color(0xFFFFF7E5)
                            : AppTheme.ink2,
                        letterSpacing: 0.06,
                        fontFamily: 'JetBrains Mono')),
              ),
            );
          }),
          const SizedBox(width: 14),
          Text(
            _nowIST(),
            style: const TextStyle(
                fontSize: 11.5,
                color: AppTheme.muted,
                fontFamily: 'JetBrains Mono',
                letterSpacing: 0.06),
          ),
        ],
      ),
    );
  }

  Widget _kbd(String key, String label) => Padding(
        padding: const EdgeInsets.only(right: 14),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Container(
            padding:
                const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
            decoration: BoxDecoration(
              color: const Color(0xFFF4F2EC),
              border: Border.all(color: AppTheme.hair),
              borderRadius: BorderRadius.circular(5),
            ),
            child: Text(key,
                style: const TextStyle(
                    fontFamily: 'JetBrains Mono',
                    fontSize: 10.5,
                    color: AppTheme.ink2,
                    fontWeight: FontWeight.w500)),
          ),
          const SizedBox(width: 4),
          Text(label,
              style: const TextStyle(
                  fontSize: 11.5,
                  color: AppTheme.muted,
                  letterSpacing: 0.04)),
        ]),
      );

  String _nowIST() {
    final now = DateTime.now().toUtc().add(const Duration(hours: 5, minutes: 30));
    final h = now.hour.toString().padLeft(2, '0');
    final m = now.minute.toString().padLeft(2, '0');
    final s = now.second.toString().padLeft(2, '0');
    return '$h:$m:$s IST';
  }
}

// ─── Queue pane ───────────────────────────────────────────────────────────────

class _QueuePane extends StatelessWidget {
  final List<AgentQueueItem> queue;
  final bool loading;
  final String? activeSessionId;
  final ValueChanged<AgentQueueItem> onSelect;
  final String? liveSessionId;
  final String liveDistrict;
  final int liveTurnCount;
  final VoidCallback onSelectLive;
  const _QueuePane({
    required this.queue,
    required this.loading,
    this.activeSessionId,
    required this.onSelect,
    this.liveSessionId,
    this.liveDistrict = '',
    this.liveTurnCount = 0,
    required this.onSelectLive,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: AppTheme.agentBg,
        border: Border(right: BorderSide(color: AppTheme.hair)),
      ),
      child: Column(
        children: [
          _PaneHeader(title: 'Active queue', meta: 'Sorted · priority'),
          // Live call banner — shown whenever citizen has an active session
          if (liveSessionId != null)
            Padding(
              padding: const EdgeInsets.fromLTRB(8, 8, 8, 0),
              child: _LiveSessionCard(
                sessionId: liveSessionId!,
                district: liveDistrict,
                turnCount: liveTurnCount,
                isActive: liveSessionId == activeSessionId,
                onTap: onSelectLive,
              ),
            ),
          Expanded(
            child: loading
                ? const Center(
                    child: CircularProgressIndicator(
                        color: AppTheme.teal, strokeWidth: 2))
                : queue.isEmpty && liveSessionId == null
                    ? const Center(
                        child: Text('No active sessions',
                            style: TextStyle(
                                color: AppTheme.muted, fontSize: 13)))
                    : ListView.builder(
                        padding: const EdgeInsets.all(8),
                        itemCount: queue.length,
                        itemBuilder: (_, i) => Padding(
                          padding: const EdgeInsets.only(bottom: 6),
                          child: _QueueCard(
                            item: queue[i],
                            active: queue[i].sessionId == activeSessionId,
                            onTap: () => onSelect(queue[i]),
                          ),
                        ),
                      ),
          ),
        ],
      ),
    );
  }
}

class _QueueCard extends StatelessWidget {
  final AgentQueueItem item;
  final bool active;
  final VoidCallback onTap;
  const _QueueCard(
      {required this.item, required this.active, required this.onTap});

  Color get _priColor {
    final p = item.priorityLabel;
    if (p == 'high') return AppTheme.red;
    if (p == 'med') return AppTheme.amber;
    return AppTheme.sage;
  }

  Color get _sentBg => item.sentiment == 'distress'
      ? const Color(0xFFF8DEDA)
      : item.sentiment == 'concerned'
          ? const Color(0xFFFBEFD0)
          : const Color(0xFFE8F0EA);

  Color get _sentFg => item.sentiment == 'distress'
      ? const Color(0xFF7A1F1F)
      : item.sentiment == 'concerned'
          ? const Color(0xFF7A5A14)
          : const Color(0xFF2E5640);

  @override
  Widget build(BuildContext context) {
    final confPct = (item.sentimentIntensity * 100).round();
    final confColor = confPct < 50
        ? AppTheme.red
        : confPct < 75
            ? AppTheme.amber
            : AppTheme.sage;

    return GestureDetector(
      onTap: onTap,
      child: Container(
        clipBehavior: Clip.antiAlias,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: active ? AppTheme.teal : AppTheme.hair),
          boxShadow: active
              ? [
                  BoxShadow(
                      color: AppTheme.teal.withValues(alpha: 0.08),
                      blurRadius: 14,
                      offset: const Offset(0, 4))
                ]
              : null,
        ),
        child: IntrinsicHeight(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Left accent bar — separated from border to avoid non-uniform
              // border + borderRadius which causes Flutter Web rendering failures
              Container(width: 3, color: _priColor),
              Expanded(
                child: Container(
                  color: Colors.white,
                  padding: const EdgeInsets.fromLTRB(9, 11, 12, 11),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(children: [
                              Text(_fmtTime(item.createdAt),
                                  style: const TextStyle(
                                      fontFamily: 'JetBrains Mono',
                                      fontSize: 11,
                                      color: AppTheme.muted)),
                              const SizedBox(width: 8),
                              Flexible(
                                child: Text(
                                    item.district.isEmpty ? '—' : item.district,
                                    style: const TextStyle(
                                        fontSize: 11.5,
                                        color: AppTheme.ink2,
                                        fontWeight: FontWeight.w500),
                                    overflow: TextOverflow.ellipsis),
                              ),
                              const Spacer(),
                              Container(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 7, vertical: 1),
                                decoration: BoxDecoration(
                                    color: const Color(0xFFF4F2EC),
                                    borderRadius: BorderRadius.circular(999)),
                                child: Text(
                                    item.language.isEmpty
                                        ? 'KN'
                                        : item.language.toUpperCase(),
                                    style: const TextStyle(
                                        fontFamily: 'JetBrains Mono',
                                        fontSize: 10.5,
                                        color: AppTheme.ink2)),
                              ),
                            ]),
                            const SizedBox(height: 6),
                            Text(
                                item.summary.isNotEmpty
                                    ? item.summary
                                    : item.reason.isNotEmpty
                                        ? item.reason
                                        : 'New call connected',
                                style: const TextStyle(
                                    fontSize: 13.5,
                                    color: AppTheme.ink,
                                    height: 1.45),
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis),
                            const SizedBox(height: 6),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 8, vertical: 2),
                              decoration: BoxDecoration(
                                  color: _sentBg,
                                  borderRadius: BorderRadius.circular(999)),
                              child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Container(
                                        width: 6,
                                        height: 6,
                                        decoration: BoxDecoration(
                                            shape: BoxShape.circle,
                                            color: _sentFg)),
                                    const SizedBox(width: 6),
                                    Text(
                                        item.sentiment.isEmpty
                                            ? 'calm'
                                            : item.sentiment,
                                        style: TextStyle(
                                            fontSize: 11.5,
                                            color: _sentFg,
                                            fontWeight: FontWeight.w500)),
                                  ]),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 10),
                      // Intensity ring
                      SizedBox(
                        width: 32,
                        height: 32,
                        child: CustomPaint(
                          painter: _RingPainter(
                              item.sentimentIntensity,
                              confColor,
                              const Color(0xFFEFEAD9),
                              4),
                          child: Center(
                            child: Text('$confPct',
                                style: const TextStyle(
                                    fontSize: 8,
                                    fontWeight: FontWeight.w600,
                                    fontFamily: 'JetBrains Mono',
                                    color: AppTheme.ink)),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _fmtTime(String iso) {
    try {
      final dt = DateTime.parse(iso).toLocal();
      final h = dt.hour.toString().padLeft(2, '0');
      final m = dt.minute.toString().padLeft(2, '0');
      return '$h:$m';
    } catch (_) {
      return iso.length > 5 ? iso.substring(11, 16) : iso;
    }
  }
}

// ─── Conversation pane ────────────────────────────────────────────────────────

class _ConvPane extends StatelessWidget {
  final AgentQueueItem? item;
  final Map<String, dynamic>? context;
  final bool loading;
  final List<Map<String, dynamic>> transcript;
  final List<Map<String, dynamic>> liveTurns;
  final List<Map<String, dynamic>> sentTimeline;
  final String revealLang;
  final bool isLive;
  const _ConvPane({
    required this.item,
    required this.context,
    required this.loading,
    required this.transcript,
    required this.liveTurns,
    required this.sentTimeline,
    required this.revealLang,
    this.isLive = false,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: AppTheme.agentBg,
        border: Border(right: BorderSide(color: AppTheme.hair)),
      ),
      child: Column(
        children: [
          _PaneHeader(
            title: 'Live conversation',
            meta: item != null
                ? '${isLive ? '● LIVE  ' : ''}SESSION ${item!.sessionId.substring(0, 8).toUpperCase()}'
                : '—',
          ),
          if (item == null)
            const Expanded(
              child: Center(
                child: Text('Select a session from the queue',
                    style: TextStyle(color: AppTheme.muted, fontSize: 13)),
              ),
            )
          else if (loading)
            const Expanded(
              child: Center(
                child: CircularProgressIndicator(
                    color: AppTheme.teal, strokeWidth: 2),
              ),
            )
          else ...[
            // Meta bar
            Container(
              padding: const EdgeInsets.symmetric(
                  horizontal: 18, vertical: 14),
              color: Colors.white,
              child: Wrap(
                spacing: 18,
                runSpacing: 8,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  _MetaItem('District', item!.district),
                  _MetaItem('Language', item!.language.toUpperCase()),
                  _MetaItem('Reason', item!.reason),
                  _SentChip(sentiment: item!.sentiment),
                ],
              ),
            ),
            // Turns — combine fetched history with live updates
            Expanded(
              child: Builder(builder: (ctx) {
                final allTurns = [...transcript, ...liveTurns];
                return allTurns.isEmpty
                    ? const Center(
                        child: Text('No transcript yet',
                            style: TextStyle(
                                color: AppTheme.muted, fontSize: 13)))
                    : ListView.builder(
                        padding: const EdgeInsets.all(18),
                        itemCount: allTurns.length,
                        itemBuilder: (_, i) => Padding(
                          padding: const EdgeInsets.only(bottom: 14),
                          child: _TurnRow(
                              turn: allTurns[i],
                              revealLang: revealLang),
                        ),
                      );
              }),
            ),
            // Sentiment timeline
            Container(
              decoration: const BoxDecoration(
                color: Colors.white,
                border: Border(top: BorderSide(color: AppTheme.hair)),
              ),
              child: Column(
                children: [
                  Padding(
                    padding: const EdgeInsets.fromLTRB(18, 10, 18, 4),
                    child: Row(
                      children: [
                        Text(
                          'Sentiment · ${sentTimeline.length} turns',
                          style: const TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w600),
                        ),
                        const Spacer(),
                        _LegendDot(color: AppTheme.sage, label: 'calm'),
                        const SizedBox(width: 10),
                        _LegendDot(
                            color: AppTheme.amber, label: 'concerned'),
                        const SizedBox(width: 10),
                        _LegendDot(color: AppTheme.red, label: 'distress'),
                      ],
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
                    child: SizedBox(
                      height: 90,
                      width: double.infinity,
                      child: sentTimeline.isEmpty
                          ? const Center(
                              child: Text('No sentiment data',
                                  style: TextStyle(
                                      fontSize: 11,
                                      color: AppTheme.muted)))
                          : CustomPaint(
                              painter: _SentLinePainter(sentTimeline),
                              size: const Size(double.infinity, 90),
                            ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _TurnRow extends StatelessWidget {
  final Map<String, dynamic> turn;
  final String revealLang;
  const _TurnRow({required this.turn, required this.revealLang});

  String get _text {
    // Pick the language-specific translation when available
    if (revealLang == 'en') {
      final t = turn['en_text'] as String?;
      if (t != null && t.isNotEmpty) return t;
    } else if (revealLang == 'hi') {
      final t = turn['hi_text'] as String?;
      if (t != null && t.isNotEmpty) return t;
    } else if (revealLang == 'kn') {
      final t = turn['kn_text'] as String?;
      if (t != null && t.isNotEmpty) return t;
    }
    return (turn['raw_transcript'] ?? turn['ai_rephrasing'] ?? '') as String;
  }

  String get _fontFamily {
    if (revealLang == 'kn') return 'Noto Sans Kannada';
    if (revealLang == 'hi') return 'Noto Sans Devanagari';
    return 'Inter';
  }

  @override
  Widget build(BuildContext context) {
    final isCit = (turn['speaker'] ?? '') == 'citizen';
    final conf = ((turn['asr_confidence'] as num?)?.toDouble() ?? 1.0);
    final confPct = (conf * 100).round();
    final isVerify = (turn['verification_state'] ?? '') != 'pending';

    Color confBg, confBorder, confFg;
    if (confPct < 70) {
      confBg = const Color(0xFFFFF4F2);
      confBorder = const Color(0xFFF2D5CE);
      confFg = const Color(0xFF7A1F1F);
    } else if (confPct < 85) {
      confBg = const Color(0xFFFFF7E8);
      confBorder = const Color(0xFFF1DDA7);
      confFg = const Color(0xFF7A5A14);
    } else {
      confBg = const Color(0xFFF1F8F4);
      confBorder = const Color(0xFFCFE1D6);
      confFg = const Color(0xFF2E5640);
    }

    final isAgent = (turn['speaker'] ?? '') == 'agent';

    final avatarColor = isCit
        ? const Color(0xFFFFF1DD)
        : isAgent
            ? const Color(0xFFF0EAF8)
            : AppTheme.tealSoft;
    final avatarBorder = isCit
        ? const Color(0xFFF1DDA7)
        : isAgent
            ? const Color(0xFFCDB8E8)
            : const Color(0xFFC9DCD5);
    final avatarTextColor = isCit
        ? AppTheme.saffron2
        : isAgent
            ? const Color(0xFF5C3D8F)
            : AppTheme.teal2;
    final avatarLabel = isCit ? 'C' : (isAgent ? 'AG' : 'AI');
    final speakerLabel = isCit ? 'Citizen' : (isAgent ? 'Agent' : 'AI Assistant');

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 30,
          height: 30,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: avatarColor,
            border: Border.all(color: avatarBorder),
          ),
          child: Center(
            child: Text(avatarLabel,
                style: TextStyle(
                    fontSize: 10.5,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.04,
                    color: avatarTextColor)),
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(children: [
                Text(speakerLabel,
                    style: const TextStyle(
                        fontSize: 11,
                        letterSpacing: 0.08,
                        color: AppTheme.muted)),
                if (isVerify) ...[
                  const SizedBox(width: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 6, vertical: 1),
                    decoration: BoxDecoration(
                        color: AppTheme.tealSoft,
                        borderRadius: BorderRadius.circular(4)),
                    child: const Text('VERIFY TURN',
                        style:
                            TextStyle(fontSize: 10, color: AppTheme.teal)),
                  ),
                ],
                const SizedBox(width: 8),
                Text(_fmtTs(turn['timestamp'] ?? ''),
                    style: const TextStyle(
                        fontSize: 11,
                        color: AppTheme.muted,
                        fontFamily: 'JetBrains Mono')),
              ]),
              const SizedBox(height: 4),
              Text(_text,
                  style: TextStyle(
                      fontSize: 14,
                      height: 1.55,
                      color: AppTheme.ink,
                      fontFamily: _fontFamily)),
            ],
          ),
        ),
        const SizedBox(width: 10),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 1),
          decoration: BoxDecoration(
            color: confBg,
            border: Border.all(color: confBorder),
            borderRadius: BorderRadius.circular(999),
          ),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            Container(
                width: 5,
                height: 5,
                decoration: BoxDecoration(
                    shape: BoxShape.circle, color: confFg)),
            const SizedBox(width: 4),
            Text('$confPct%',
                style: TextStyle(
                    fontSize: 10.5,
                    color: confFg,
                    fontFamily: 'JetBrains Mono')),
          ]),
        ),
      ],
    );
  }

  String _fmtTs(String iso) {
    try {
      final dt = DateTime.parse(iso).toLocal();
      return '${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}:${dt.second.toString().padLeft(2, '0')}';
    } catch (_) {
      return '';
    }
  }
}

// ─── Interpretation pane ──────────────────────────────────────────────────────

class _InterpPane extends StatelessWidget {
  final AgentQueueItem? item;
  final Map<String, dynamic> fields;
  final bool reviewed;
  final VoidCallback onApprove;
  final void Function(String, String) onUpdate;
  final ConfidenceScore? liveConfidence;
  const _InterpPane({
    required this.item,
    required this.fields,
    required this.reviewed,
    required this.onApprove,
    required this.onUpdate,
    this.liveConfidence,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      color: AppTheme.agentBg,
      child: Column(
        children: [
          _PaneHeader(
              title: 'AI interpretation',
              meta: reviewed ? 'Reviewed' : 'Inline-editable'),
          if (item == null)
            const Expanded(
                child: Center(
                    child: Text('No session selected',
                        style: TextStyle(
                            color: AppTheme.muted, fontSize: 13))))
          else
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // Approve
                    GestureDetector(
                      onTap: onApprove,
                      child: Container(
                        padding: const EdgeInsets.symmetric(vertical: 9),
                        decoration: BoxDecoration(
                            color: AppTheme.teal,
                            borderRadius: BorderRadius.circular(10)),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Icon(Icons.check,
                                size: 14,
                                color: Color(0xFFFFF7E5)),
                            const SizedBox(width: 8),
                            Text(
                              reviewed ? 'Approved' : 'Approve all',
                              style: const TextStyle(
                                  fontSize: 13,
                                  fontWeight: FontWeight.w600,
                                  color: Color(0xFFFFF7E5)),
                            ),
                            const SizedBox(width: 8),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 6, vertical: 1),
                              decoration: BoxDecoration(
                                color: Colors.white.withValues(alpha: 0.18),
                                borderRadius: BorderRadius.circular(5),
                              ),
                              child: const Text('A',
                                  style: TextStyle(
                                      fontFamily: 'JetBrains Mono',
                                      fontSize: 10.5,
                                      color: Color(0xFFFFF7E5))),
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 10),

                    _EditableField(
                      label: 'Intent',
                      value: fields['intent']?.toString() ?? '',
                      onSave: (v) => onUpdate('intent', v),
                    ),
                    _EditableField(
                      label: 'Department',
                      value: fields['department']?.toString() ?? '',
                      onSave: (v) => onUpdate('department', v),
                    ),
                    _EditableField(
                      label: 'Dialect tag',
                      value: fields['dialect']?.toString() ?? '',
                      onSave: (v) => onUpdate('dialect', v),
                    ),
                    _EditableField(
                      label: 'Summary',
                      value: fields['summary']?.toString() ?? '',
                      onSave: (v) => onUpdate('summary', v),
                      multiline: true,
                    ),
                    _UrgencyChip(label: fields['urgency']?.toString() ?? 'low'),

                    const SizedBox(height: 6),

                    // Live confidence breakdown (real-time when viewing live session)
                    if (liveConfidence != null) ...[
                      _LiveConfCard(score: liveConfidence!),
                      const SizedBox(height: 8),
                    ] else if (item != null) ...[
                      _ConfCard(
                          sentimentIntensity: item!.sentimentIntensity,
                          label: item!.sentiment),
                    ],

                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          vertical: 9, horizontal: 12),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        border: Border.all(color: AppTheme.hair),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: const Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.info_outline_rounded,
                              size: 13, color: AppTheme.muted),
                          SizedBox(width: 6),
                          Text('Mark for senior review',
                              style: TextStyle(
                                  fontSize: 12.5, color: AppTheme.ink)),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _EditableField extends StatefulWidget {
  final String label;
  final String value;
  final bool multiline;
  final ValueChanged<String> onSave;
  const _EditableField(
      {required this.label,
      required this.value,
      required this.onSave,
      this.multiline = false});

  @override
  State<_EditableField> createState() => _EditableFieldState();
}

class _EditableFieldState extends State<_EditableField> {
  bool _editing = false;
  late TextEditingController _ctrl;

  @override
  void initState() {
    super.initState();
    _ctrl = TextEditingController(text: widget.value);
  }

  @override
  void didUpdateWidget(covariant _EditableField old) {
    super.didUpdateWidget(old);
    if (old.value != widget.value && !_editing) _ctrl.text = widget.value;
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  void _commit() {
    widget.onSave(_ctrl.text);
    setState(() => _editing = false);
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 4),
      decoration: const BoxDecoration(
          border: Border(
              bottom:
                  BorderSide(color: AppTheme.hair, width: 0.5))),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 100,
            child: Padding(
              padding: const EdgeInsets.only(top: 5),
              child: Text(widget.label.toUpperCase(),
                  style: const TextStyle(
                      fontSize: 11,
                      letterSpacing: 0.08,
                      color: AppTheme.muted)),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: _editing
                ? TextField(
                    controller: _ctrl,
                    autofocus: true,
                    maxLines: widget.multiline ? null : 1,
                    minLines: widget.multiline ? 2 : null,
                    style: const TextStyle(
                        fontSize: 13.5,
                        color: AppTheme.ink,
                        fontWeight: FontWeight.w500),
                    decoration: InputDecoration(
                      isDense: true,
                      contentPadding: const EdgeInsets.symmetric(
                          horizontal: 6, vertical: 4),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(6),
                        borderSide:
                            const BorderSide(color: AppTheme.teal),
                      ),
                      focusedBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(6),
                        borderSide:
                            const BorderSide(color: AppTheme.teal),
                      ),
                    ),
                    onSubmitted: (_) => _commit(),
                  )
                : GestureDetector(
                    onTap: () => setState(() => _editing = true),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(
                          child: Text(widget.value,
                              style: const TextStyle(
                                  fontSize: 13.5,
                                  color: AppTheme.ink,
                                  fontWeight: FontWeight.w500,
                                  height: 1.35)),
                        ),
                        const SizedBox(width: 4),
                        const Icon(Icons.edit_outlined,
                            size: 12, color: AppTheme.muted),
                      ],
                    ),
                  ),
          ),
        ],
      ),
    );
  }
}

// ─── Agent reply bar ──────────────────────────────────────────────────────────

class _AgentReplyBar extends StatelessWidget {
  final TextEditingController controller;
  final VoidCallback onSend;
  const _AgentReplyBar({required this.controller, required this.onSend});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 10),
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(top: BorderSide(color: AppTheme.hair)),
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: controller,
              style: const TextStyle(fontSize: 13.5, color: AppTheme.ink),
              decoration: InputDecoration(
                hintText: 'Reply to citizen…',
                hintStyle:
                    const TextStyle(fontSize: 13.5, color: AppTheme.muted),
                isDense: true,
                contentPadding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: const BorderSide(color: AppTheme.hair),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: const BorderSide(color: AppTheme.hair),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: const BorderSide(color: AppTheme.teal),
                ),
              ),
              onSubmitted: (_) => onSend(),
            ),
          ),
          const SizedBox(width: 8),
          GestureDetector(
            onTap: onSend,
            child: Container(
              padding:
                  const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
              decoration: BoxDecoration(
                color: AppTheme.teal,
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.headset_mic_rounded,
                      size: 14, color: Color(0xFFFFF7E5)),
                  SizedBox(width: 6),
                  Text('Send',
                      style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: Color(0xFFFFF7E5))),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _UrgencyChip extends StatelessWidget {
  final String label;
  const _UrgencyChip({required this.label});

  Color get _bg => label == 'high'
      ? const Color(0xFFF8DEDA)
      : label == 'med' || label == 'medium'
          ? const Color(0xFFFBEFD0)
          : const Color(0xFFE8F0EA);
  Color get _fg => label == 'high'
      ? const Color(0xFF7A1F1F)
      : label == 'med' || label == 'medium'
          ? const Color(0xFF7A5A14)
          : const Color(0xFF2E5640);

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 4),
      decoration: const BoxDecoration(
          border: Border(
              bottom:
                  BorderSide(color: AppTheme.hair, width: 0.5))),
      child: Row(
        children: [
          const SizedBox(
            width: 100,
            child: Text('URGENCY',
                style: TextStyle(
                    fontSize: 11,
                    letterSpacing: 0.08,
                    color: AppTheme.muted)),
          ),
          const SizedBox(width: 10),
          Container(
            padding:
                const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
            decoration: BoxDecoration(
                color: _bg, borderRadius: BorderRadius.circular(999)),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              Container(
                  width: 6,
                  height: 6,
                  decoration: BoxDecoration(
                      shape: BoxShape.circle, color: _fg)),
              const SizedBox(width: 6),
              Text(label,
                  style: TextStyle(
                      fontSize: 11.5,
                      color: _fg,
                      fontWeight: FontWeight.w500)),
            ]),
          ),
        ],
      ),
    );
  }
}

class _ConfCard extends StatelessWidget {
  final double sentimentIntensity;
  final String label;
  const _ConfCard({required this.sentimentIntensity, required this.label});

  @override
  Widget build(BuildContext context) {
    final pct = (sentimentIntensity * 100).round().clamp(0, 100);
    final color = pct < 50
        ? AppTheme.sage
        : pct < 75
            ? AppTheme.amber
            : AppTheme.red;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border.all(color: AppTheme.hair),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        children: [
          SizedBox(
            width: 96,
            height: 96,
            child: CustomPaint(
              painter: _RingPainter(
                  sentimentIntensity.clamp(0, 1),
                  color,
                  const Color(0xFFEFEAD9),
                  8),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text('$pct',
                      style: const TextStyle(
                          fontSize: 24,
                          fontWeight: FontWeight.w600,
                          fontFamily: 'JetBrains Mono',
                          color: AppTheme.ink)),
                  const Text('DISTRESS',
                      style: TextStyle(
                          fontSize: 8,
                          letterSpacing: 1.5,
                          color: AppTheme.muted)),
                ],
              ),
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('SENTIMENT LABEL',
                    style: TextStyle(
                        fontSize: 10.5,
                        letterSpacing: 0.08,
                        color: AppTheme.muted)),
                const SizedBox(height: 4),
                Text(label,
                    style: const TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                        color: AppTheme.ink)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ─── Shared widgets ───────────────────────────────────────────────────────────

class _PaneHeader extends StatelessWidget {
  final String title;
  final String meta;
  const _PaneHeader({required this.title, required this.meta});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(bottom: BorderSide(color: AppTheme.hair)),
      ),
      child: Row(
        children: [
          Text(title,
              style: const TextStyle(
                  fontSize: 13, fontWeight: FontWeight.w600)),
          const Spacer(),
          Text(meta,
              style: const TextStyle(
                  fontSize: 11.5,
                  color: AppTheme.muted,
                  letterSpacing: 0.04,
                  fontFamily: 'JetBrains Mono')),
        ],
      ),
    );
  }
}

class _MetaItem extends StatelessWidget {
  final String k;
  final String v;
  const _MetaItem(this.k, this.v);

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(k.toUpperCase(),
            style: const TextStyle(
                fontSize: 10.5,
                letterSpacing: 0.08,
                color: AppTheme.muted)),
        const SizedBox(height: 1),
        Text(v,
            style: const TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w500,
                color: AppTheme.ink)),
      ],
    );
  }
}

class _SentChip extends StatelessWidget {
  final String sentiment;
  const _SentChip({required this.sentiment});

  Color get _bg => sentiment == 'distress'
      ? const Color(0xFFFFF4F2)
      : sentiment == 'concerned'
          ? const Color(0xFFFFF7E8)
          : const Color(0xFFF1F8F4);
  Color get _border => sentiment == 'distress'
      ? const Color(0xFFF2D5CE)
      : sentiment == 'concerned'
          ? const Color(0xFFF1DDA7)
          : const Color(0xFFCFE1D6);
  Color get _fg => sentiment == 'distress'
      ? const Color(0xFF7A1F1F)
      : sentiment == 'concerned'
          ? const Color(0xFF7A5A14)
          : const Color(0xFF2E5640);

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
      decoration: BoxDecoration(
        color: _bg,
        border: Border.all(color: _border),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Container(
            width: 6,
            height: 6,
            decoration:
                BoxDecoration(shape: BoxShape.circle, color: _fg)),
        const SizedBox(width: 6),
        Text('Sentiment: $sentiment',
            style: TextStyle(fontSize: 11.5, color: _fg)),
      ]),
    );
  }
}

class _LegendDot extends StatelessWidget {
  final Color color;
  final String label;
  const _LegendDot({required this.color, required this.label});

  @override
  Widget build(BuildContext context) {
    return Row(mainAxisSize: MainAxisSize.min, children: [
      Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(shape: BoxShape.circle, color: color)),
      const SizedBox(width: 5),
      Text(label,
          style: const TextStyle(fontSize: 11, color: AppTheme.muted)),
    ]);
  }
}

class _Toast extends StatelessWidget {
  final String title;
  final String body;
  final bool high;
  final VoidCallback onDismiss;
  final VoidCallback? onSwitchToSession;
  const _Toast(
      {required this.title,
      required this.body,
      required this.high,
      required this.onDismiss,
      this.onSwitchToSession});

  @override
  Widget build(BuildContext context) {
    final accent = high ? AppTheme.red : AppTheme.sage;
    return Container(
      width: 320,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border(
          top: BorderSide(color: AppTheme.hair),
          right: BorderSide(color: AppTheme.hair),
          bottom: BorderSide(color: AppTheme.hair),
          left: BorderSide(color: accent, width: 4),
        ),
        borderRadius: BorderRadius.circular(12),
        boxShadow: const [
          BoxShadow(
              color: Color(0x2E000000),
              blurRadius: 40,
              offset: Offset(0, 14)),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(children: [
            Container(
                width: 8,
                height: 8,
                decoration: BoxDecoration(
                    shape: BoxShape.circle, color: accent)),
            const SizedBox(width: 8),
            Expanded(
              child: Text(title,
                  style: const TextStyle(
                      fontWeight: FontWeight.w600,
                      fontSize: 13,
                      color: AppTheme.ink)),
            ),
          ]),
          const SizedBox(height: 8),
          Text(body,
              style: const TextStyle(
                  fontSize: 12.5, color: AppTheme.ink2, height: 1.45)),
          if (high) ...[
            const SizedBox(height: 8),
            Row(children: [
              Expanded(
                child: GestureDetector(
                  onTap: onSwitchToSession ?? onDismiss,
                  child: Container(
                    padding: const EdgeInsets.symmetric(vertical: 6),
                    decoration: BoxDecoration(
                        color: AppTheme.teal,
                        borderRadius: BorderRadius.circular(8)),
                    child: const Center(
                        child: Text('Switch to this session',
                            style: TextStyle(
                                fontSize: 12,
                                color: Color(0xFFFFF7E5)))),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              GestureDetector(
                onTap: onDismiss,
                child: Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    border: Border.all(color: AppTheme.hair),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Text('Dismiss',
                      style: TextStyle(
                          fontSize: 12, color: AppTheme.ink)),
                ),
              ),
            ]),
          ],
        ],
      ),
    );
  }
}

// ─── Live session card (queue pane) ──────────────────────────────────────────

class _LiveSessionCard extends StatefulWidget {
  final String sessionId;
  final String district;
  final int turnCount;
  final bool isActive;
  final VoidCallback onTap;
  const _LiveSessionCard({
    required this.sessionId,
    required this.district,
    required this.turnCount,
    required this.isActive,
    required this.onTap,
  });

  @override
  State<_LiveSessionCard> createState() => _LiveSessionCardState();
}

class _LiveSessionCardState extends State<_LiveSessionCard>
    with SingleTickerProviderStateMixin {
  late final AnimationController _pulse;

  @override
  void initState() {
    super.initState();
    _pulse = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _pulse.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: widget.onTap,
      child: Container(
        clipBehavior: Clip.antiAlias,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: widget.isActive ? AppTheme.teal : AppTheme.hair),
          boxShadow: widget.isActive
              ? [BoxShadow(color: AppTheme.teal.withValues(alpha: 0.10), blurRadius: 12, offset: const Offset(0, 3))]
              : null,
        ),
        child: IntrinsicHeight(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Container(width: 3, color: AppTheme.red),
              Expanded(
                child: Container(
                  color: Colors.white,
                  padding: const EdgeInsets.fromLTRB(9, 10, 12, 10),
                  child: Row(
                    children: [
                      AnimatedBuilder(
                        animation: _pulse,
                        builder: (_, __) => Container(
                          width: 7,
                          height: 7,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: AppTheme.red.withValues(alpha: 0.5 + 0.5 * _pulse.value),
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(children: [
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                                decoration: BoxDecoration(
                                  color: const Color(0xFFFFF4F2),
                                  border: Border.all(color: const Color(0xFFF2D5CE)),
                                  borderRadius: BorderRadius.circular(4),
                                ),
                                child: const Text('LIVE',
                                    style: TextStyle(
                                        fontSize: 10,
                                        fontWeight: FontWeight.w700,
                                        color: AppTheme.red,
                                        letterSpacing: 0.5,
                                        fontFamily: 'JetBrains Mono')),
                              ),
                              const SizedBox(width: 8),
                              Text(
                                widget.district.isEmpty ? 'Active call' : widget.district,
                                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500, color: AppTheme.ink),
                              ),
                            ]),
                            const SizedBox(height: 3),
                            Text(
                              '${widget.turnCount} turn${widget.turnCount == 1 ? '' : 's'} · tap to open',
                              style: const TextStyle(fontSize: 11, color: AppTheme.muted),
                            ),
                          ],
                        ),
                      ),
                      const Icon(Icons.chevron_right_rounded, size: 16, color: AppTheme.muted),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ─── Live confidence card (interpretation pane) ────────────────────────────

class _LiveConfCard extends StatelessWidget {
  final ConfidenceScore score;
  const _LiveConfCard({required this.score});

  @override
  Widget build(BuildContext context) {
    final pct = (score.compositeScore * 100).round().clamp(0, 100);
    final ringColor = pct >= 70 ? AppTheme.sage : pct >= 50 ? AppTheme.amber : AppTheme.red;

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border.all(color: AppTheme.hair),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Container(
              width: 6, height: 6,
              decoration: const BoxDecoration(shape: BoxShape.circle, color: AppTheme.red),
            ),
            const SizedBox(width: 6),
            const Text('LIVE CONFIDENCE',
                style: TextStyle(fontSize: 10, letterSpacing: 0.5, color: AppTheme.muted)),
          ]),
          const SizedBox(height: 10),
          Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              SizedBox(
                width: 64, height: 64,
                child: CustomPaint(
                  painter: _RingPainter(score.compositeScore.clamp(0, 1), ringColor, const Color(0xFFEFEAD9), 6),
                  child: Center(
                    child: Text('$pct',
                        style: const TextStyle(
                            fontSize: 18, fontWeight: FontWeight.w700,
                            fontFamily: 'JetBrains Mono', color: AppTheme.ink)),
                  ),
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  children: [
                    _confBar('ASR', score.asrConfidence),
                    const SizedBox(height: 5),
                    _confBar('Intent', 1.0 - score.intentEntropy),
                    const SizedBox(height: 5),
                    _confBar('Tone', 1.0 - score.sentimentIntensity,
                        color: score.sentimentIntensity > 0.7 ? AppTheme.red : AppTheme.sage),
                  ],
                ),
              ),
            ],
          ),
          if (score.clarificationCount > 0) ...[
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: const Color(0xFFFFF7E8),
                border: Border.all(color: const Color(0xFFF1DDA7)),
                borderRadius: BorderRadius.circular(999),
              ),
              child: Text(
                '${score.clarificationCount} clarification${score.clarificationCount == 1 ? '' : 's'}',
                style: const TextStyle(fontSize: 11, color: Color(0xFF7A5A14)),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _confBar(String label, double value, {Color? color}) {
    final c = color ?? (value >= 0.7 ? AppTheme.sage : value >= 0.5 ? AppTheme.amber : AppTheme.red);
    return Row(children: [
      SizedBox(
        width: 38,
        child: Text(label,
            style: const TextStyle(fontSize: 10, color: AppTheme.muted)),
      ),
      Expanded(
        child: ClipRRect(
          borderRadius: BorderRadius.circular(2),
          child: Stack(children: [
            Container(height: 4, color: const Color(0xFFEFEAD9)),
            FractionallySizedBox(
              widthFactor: value.clamp(0.0, 1.0),
              child: Container(height: 4, color: c),
            ),
          ]),
        ),
      ),
      const SizedBox(width: 6),
      Text('${(value * 100).round()}%',
          style: const TextStyle(
              fontSize: 10, fontFamily: 'JetBrains Mono', color: AppTheme.ink2)),
    ]);
  }
}

// ─── Painters ─────────────────────────────────────────────────────────────────

class _RingPainter extends CustomPainter {
  final double progress;
  final Color color;
  final Color trackColor;
  final double strokeWidth;
  const _RingPainter(
      this.progress, this.color, this.trackColor, this.strokeWidth);

  @override
  void paint(Canvas canvas, Size size) {
    final cx = size.width / 2;
    final cy = size.height / 2;
    final r = (math.min(size.width, size.height) - strokeWidth) / 2;
    final track = Paint()
      ..color = trackColor
      ..strokeWidth = strokeWidth
      ..style = PaintingStyle.stroke;
    canvas.drawCircle(Offset(cx, cy), r, track);
    final arc = Paint()
      ..color = color
      ..strokeWidth = strokeWidth
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;
    canvas.drawArc(Rect.fromCircle(center: Offset(cx, cy), radius: r),
        -math.pi / 2, 2 * math.pi * progress.clamp(0.0, 1.0), false, arc);
  }

  @override
  bool shouldRepaint(covariant _RingPainter old) =>
      old.progress != progress || old.color != color;
}

class _SentLinePainter extends CustomPainter {
  final List<Map<String, dynamic>> points;
  const _SentLinePainter(this.points);

  Color _col(String s) {
    if (s == 'calm') return AppTheme.sage;
    if (s == 'concerned') return AppTheme.amber;
    if (s == 'distress' || s == 'anger' || s == 'fear') return AppTheme.red;
    return AppTheme.muted;
  }

  @override
  void paint(Canvas canvas, Size size) {
    if (points.length < 2) return;
    const padX = 24.0, padY = 14.0;

    double xs(int i) =>
        padX + (i / (points.length - 1)) * (size.width - 2 * padX);
    double ys(double v) =>
        padY + (1 - (v + 1) / 2) * (size.height - 2 * padY);
    double val(Map<String, dynamic> p) =>
        1.0 - ((p['intensity'] as num?)?.toDouble() ?? 0.5) * 2;

    // Grid
    final gp = Paint()..color = const Color(0xFFEFEAD9)..strokeWidth = 1;
    canvas.drawLine(
        Offset(padX, ys(0)), Offset(size.width - padX, ys(0)), gp);

    // Smooth path
    final path = Path()..moveTo(xs(0), ys(val(points[0])));
    for (var i = 1; i < points.length; i++) {
      final x0 = xs(i - 1), y0 = ys(val(points[i - 1]));
      final x1 = xs(i), y1 = ys(val(points[i]));
      final cx = (x0 + x1) / 2;
      path.cubicTo(cx, y0, cx, y1, x1, y1);
    }

    // Fill
    final fill = Path.from(path)
      ..lineTo(size.width - padX, size.height - padY)
      ..lineTo(padX, size.height - padY)
      ..close();
    canvas.drawPath(
        fill,
        Paint()
          ..color = AppTheme.teal.withValues(alpha: 0.08)
          ..style = PaintingStyle.fill);

    // Line
    canvas.drawPath(
        path,
        Paint()
          ..color = AppTheme.teal
          ..strokeWidth = 1.6
          ..style = PaintingStyle.stroke
          ..strokeCap = StrokeCap.round);

    // Dots
    for (var i = 0; i < points.length; i++) {
      final p = points[i];
      canvas.drawCircle(Offset(xs(i), ys(val(p))), 4.5,
          Paint()..color = _col(p['label'] as String? ?? ''));
      canvas.drawCircle(
          Offset(xs(i), ys(val(p))),
          4.5,
          Paint()
            ..color = Colors.white
            ..style = PaintingStyle.stroke
            ..strokeWidth = 1.5);
    }
  }

  @override
  bool shouldRepaint(covariant _SentLinePainter old) =>
      old.points != points;
}
