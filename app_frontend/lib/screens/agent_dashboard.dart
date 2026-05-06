import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

// ─── Data models ──────────────────────────────────────────────────────────────

class _ScenarioData {
  final String id;
  final String district;
  final String dialect;
  final String intent;
  final String subIntent;
  final String department;
  final String urgency;
  final List<String> entities;
  final String action;
  final int confTotal;
  final int confAsr;
  final int confIntent;
  final int confSentiment;
  final String sentiment;
  final List<_Turn> turns;
  const _ScenarioData({
    required this.id,
    required this.district,
    required this.dialect,
    required this.intent,
    required this.subIntent,
    required this.department,
    required this.urgency,
    required this.entities,
    required this.action,
    required this.confTotal,
    required this.confAsr,
    required this.confIntent,
    required this.confSentiment,
    required this.sentiment,
    required this.turns,
  });
}

class _Turn {
  final String who; // 'cit' | 'ai'
  final String textEn;
  final String textKn;
  final String textHi;
  final String ts;
  final int conf;
  final bool verify;
  const _Turn({
    required this.who,
    required this.textEn,
    required this.textKn,
    required this.textHi,
    required this.ts,
    required this.conf,
    this.verify = false,
  });
}

class _QueueItem {
  final String id;
  final String? scIdx;
  final String ts;
  final String district;
  final String lang;
  final String sentiment;
  final String intent;
  final int conf;
  final String priority;
  final String dialect;
  const _QueueItem({
    required this.id,
    this.scIdx,
    required this.ts,
    required this.district,
    required this.lang,
    required this.sentiment,
    required this.intent,
    required this.conf,
    required this.priority,
    required this.dialect,
  });
}

class _SentPoint {
  final double v;
  final String s;
  const _SentPoint(this.v, this.s);
}

// ─── Embedded data ───────────────────────────────────────────────────────────

final _scenarios = [
  _ScenarioData(
    id: 'scheme', district: 'Mysuru', dialect: 'Mysuru Kannada',
    intent: 'Scheme information', subIntent: 'Bhagyalakshmi eligibility',
    department: 'Women & Child Development', urgency: 'low',
    entities: ['Scheme: Bhagyalakshmi', 'Beneficiary: girl child', 'District: Mysuru'],
    action: 'Send SMS with eligibility checklist + nearest Anganwadi contact',
    confTotal: 92, confAsr: 94, confIntent: 91, confSentiment: 96, sentiment: 'calm',
    turns: [
      _Turn(who: 'cit', ts: '00:00', conf: 88,
        textEn: 'Hello, I wanted to know about the Bhagyalakshmi scheme…',
        textKn: 'ನಮಸ್ಕಾರ, ಭಾಗ್ಯಲಕ್ಷ್ಮಿ ಯೋಜನೆ ಬಗ್ಗೆ ತಿಳಿಯಬೇಕಿತ್ತು…',
        textHi: 'नमस्ते, मुझे भाग्यलक्ष्मी योजना के बारे में जानना था…'),
      _Turn(who: 'ai', ts: '00:09', conf: 95,
        textEn: 'Do you want to know if you are eligible for the Bhagyalakshmi scheme?',
        textKn: 'ನೀವು ಭಾಗ್ಯಲಕ್ಷ್ಮಿ ಯೋಜನೆಗೆ ಅರ್ಹತೆ ಇದೆಯೇ ಎಂದು ತಿಳಿಯಲು ಬಯಸಿದ್ದೀರಾ?',
        textHi: 'क्या आप जानना चाहती हैं कि आप भाग्यलक्ष्मी योजना के लिए पात्र हैं?',
        verify: true),
      _Turn(who: 'ai', ts: '00:18', conf: 97,
        textEn: 'Good. Please share the daughter\'s date of birth and the mother\'s Aadhaar number.',
        textKn: 'ಒಳ್ಳೆಯದು. ಮಗಳ ಜನ್ಮ ತಾರೀಖು ಮತ್ತು ತಾಯಿಯ ಆಧಾರ್ ಸಂಖ್ಯೆ ಹೇಳುವಿರಾ?',
        textHi: 'ठीक है। बेटी की जन्म तारीख और माँ का आधार नंबर बताइए।'),
    ],
  ),
  _ScenarioData(
    id: 'ambig', district: 'Belagavi', dialect: 'North Karnataka Kannada',
    intent: 'Child protection — review', subIntent: 'Possible school harassment',
    department: 'Child Welfare Committee', urgency: 'medium',
    entities: ['Place: school', 'Subject: 14-yr-old daughter', 'Concern: discomfort'],
    action: 'Schedule CWC counsellor callback within 24h; flag for senior review',
    confTotal: 72, confAsr: 81, confIntent: 64, confSentiment: 78, sentiment: 'concerned',
    turns: [
      _Turn(who: 'cit', ts: '00:00', conf: 75,
        textEn: 'Something is happening to my daughter at school… I\'m not sure how to put it…',
        textKn: 'ನನ್ನ ಮಗಳಿಗೆ ಶಾಲೆಯಲ್ಲಿ ಏನೋ ಆಗ್ತಿದೆ… ಗೊತ್ತಾಗ್ತಿಲ್ಲ…',
        textHi: 'मेरी बेटी को स्कूल में कुछ हो रहा है… ठीक से बता नहीं पा रही…'),
      _Turn(who: 'ai', ts: '00:09', conf: 82,
        textEn: 'Is your daughter facing trouble from someone at school — am I understanding this correctly?',
        textKn: 'ನಿಮ್ಮ ಮಗಳು ಶಾಲೆಯಲ್ಲಿ ಯಾರಿಂದಾದರೂ ತೊಂದರೆ ಅನುಭವಿಸುತ್ತಿದ್ದಾರೆಯೇ — ಇದನ್ನು ನಾನು ಸರಿಯಾಗಿ ಅರ್ಥ ಮಾಡಿಕೊಂಡಿದ್ದೇನೆಯೇ?',
        textHi: 'क्या आपकी बेटी को स्कूल में किसी से परेशानी हो रही है — क्या मैंने सही समझा?',
        verify: true),
      _Turn(who: 'ai', ts: '00:18', conf: 91,
        textEn: 'Thank you. I\'m connecting you to a CWC counsellor — please hold on.',
        textKn: 'ಧನ್ಯವಾದ. ನಾನು ನಿಮ್ಮನ್ನು CWC ಕೌನ್ಸೆಲರ್‌ಗೆ ಸಂಪರ್ಕಿಸುತ್ತಿದ್ದೇನೆ. ಸ್ವಲ್ಪ ಕಾಯಿರಿ.',
        textHi: 'धन्यवाद। मैं आपको CWC काउंसलर से जोड़ रही हूँ। एक पल रुकिए।'),
    ],
  ),
  _ScenarioData(
    id: 'distress', district: 'Kalaburagi', dialect: 'Hyderabad-Karnataka Kannada',
    intent: 'Domestic violence — immediate support', subIntent: 'Caller fears for safety',
    department: 'Police + One Stop Centre', urgency: 'high',
    entities: ['Subject: caller herself', 'Threat: present in home', 'Children: 2 with caller'],
    action: 'Dispatch local OSC team; warm-handoff to senior agent; keep line open',
    confTotal: 93, confAsr: 88, confIntent: 95, confSentiment: 97, sentiment: 'distress',
    turns: [
      _Turn(who: 'cit', ts: '00:00', conf: 82,
        textEn: 'Please help me… I\'m frightened, I don\'t feel safe at home…',
        textKn: 'ದಯವಿಟ್ಟು ಸಹಾಯ ಮಾಡಿ… ನನಗೆ ಭಯವಾಗ್ತಿದೆ, ಮನೆಯಲ್ಲಿ ಸುರಕ್ಷಿತವಾಗಿಲ್ಲ…',
        textHi: 'कृपया मदद कीजिए… मुझे डर लग रहा है, घर में सुरक्षित नहीं हूँ…'),
      _Turn(who: 'ai', ts: '00:09', conf: 98,
        textEn: 'You are not alone. I\'m connecting you to a human agent now. Please stay on the line.',
        textKn: 'ನೀವು ಒಬ್ಬರೇ ಅಲ್ಲ. ನಾನು ನಿಮ್ಮನ್ನು ಮಾನವ ಸಹಾಯಕರಿಗೆ ಸಂಪರ್ಕಿಸುತ್ತಿದ್ದೇನೆ. ಫೋನ್ ಕಟ್ ಮಾಡಬೇಡಿ.',
        textHi: 'आप अकेली नहीं हैं। मैं आपको एक मानव सहायक से जोड़ रही हूँ। फोन मत काटिए।'),
    ],
  ),
];

final _queueExtra = [
  const _QueueItem(id: 'q-1', ts: '14:02', district: 'Bengaluru U', lang: 'kn',
    sentiment: 'concerned', intent: 'Workplace harassment — disclosure', conf: 74, priority: 'med', dialect: 'Bengaluru Kannada'),
  const _QueueItem(id: 'q-2', ts: '14:08', district: 'Hassan', lang: 'kn',
    sentiment: 'calm', intent: 'Maternity benefits — eligibility query', conf: 88, priority: 'low', dialect: 'Old Mysuru Kannada'),
  const _QueueItem(id: 'q-3', ts: '14:11', district: 'Vijayapura', lang: 'hi',
    sentiment: 'concerned', intent: 'Missing minor — daughter age 12', conf: 69, priority: 'med', dialect: 'Dakhini Hindi'),
  const _QueueItem(id: 'q-4', ts: '14:14', district: 'Mangaluru', lang: 'kn',
    sentiment: 'calm', intent: 'Anganwadi services — relocation', conf: 91, priority: 'low', dialect: 'Mangaluru Kannada'),
];

final _sentPointsByScenario = {
  'distress': [
    _SentPoint(.4, 'calm'), _SentPoint(0, 'calm'), _SentPoint(-.5, 'concerned'),
    _SentPoint(-.85, 'distress'), _SentPoint(-.95, 'distress'), _SentPoint(-.7, 'distress'), _SentPoint(-.4, 'concerned'),
  ],
  'ambig': [
    _SentPoint(.6, 'calm'), _SentPoint(.2, 'calm'), _SentPoint(-.2, 'concerned'),
    _SentPoint(-.45, 'concerned'), _SentPoint(-.3, 'concerned'), _SentPoint(-.1, 'concerned'), _SentPoint(.1, 'calm'),
  ],
  'scheme': [
    _SentPoint(.7, 'calm'), _SentPoint(.6, 'calm'), _SentPoint(.55, 'calm'),
    _SentPoint(.6, 'calm'), _SentPoint(.7, 'calm'), _SentPoint(.75, 'calm'), _SentPoint(.8, 'calm'),
  ],
};

// ─── AgentDashboard ───────────────────────────────────────────────────────────

class AgentDashboard extends StatefulWidget {
  const AgentDashboard({super.key});

  @override
  State<AgentDashboard> createState() => _AgentDashboardState();
}

class _AgentDashboardState extends State<AgentDashboard> {
  int _activeIdx = 2; // distress first
  String _revealLang = 'en';
  bool _reviewed = false;
  bool _showToast = false;
  String _toastTitle = '';
  String _toastBody = '';
  bool _toastHigh = false;

  late List<Map<String, dynamic>> _interp;

  @override
  void initState() {
    super.initState();
    _interp = _scenarios
        .map((s) => {
              'intent': s.intent,
              'subIntent': s.subIntent,
              'department': s.department,
              'urgency': s.urgency,
              'entities': List<String>.from(s.entities),
              'dialect': s.dialect,
              'action': s.action,
            })
        .toList();

    Future.delayed(const Duration(milliseconds: 4500), () {
      if (!mounted) return;
      setState(() {
        _showToast = true;
        _toastTitle = 'New high-priority escalation';
        _toastBody = 'Vijayapura · Hindi · Missing minor — daughter age 12';
        _toastHigh = true;
      });
      Future.delayed(const Duration(milliseconds: 6500), () {
        if (mounted) setState(() => _showToast = false);
      });
    });
  }

  _ScenarioData get _scenario => _scenarios[_activeIdx];
  Map<String, dynamic> get _fields => _interp[_activeIdx];

  List<_QueueItem> get _queue {
    final cards = _scenarios.asMap().entries.map((e) {
      final i = e.key;
      final s = e.value;
      final pri = s.urgency == 'high' ? 'high' : s.urgency == 'medium' ? 'med' : 'low';
      return _QueueItem(
        id: 's-$i', scIdx: '$i',
        ts: ['14:21', '14:23', '14:26'][i],
        district: s.district, lang: 'kn',
        sentiment: s.sentiment, intent: s.subIntent,
        conf: s.confTotal, priority: pri, dialect: s.dialect,
      );
    }).toList();
    const order = {'high': 0, 'med': 1, 'low': 2};
    cards.sort((a, b) => (order[a.priority] ?? 2).compareTo(order[b.priority] ?? 2));
    return [...cards, ..._queueExtra];
  }

  void _updateField(String key, dynamic value) {
    setState(() {
      _interp[_activeIdx] = {..._interp[_activeIdx], key: value};
    });
  }

  void _approveAll() => setState(() => _reviewed = true);

  void _resolve() {
    if (!_reviewed) return;
    setState(() {
      _showToast = true;
      _toastTitle = 'Session resolved · ${_scenario.district}';
      _toastBody = 'Closure note logged. Removed from queue.';
      _toastHigh = false;
    });
    Future.delayed(const Duration(milliseconds: 3500), () {
      if (mounted) setState(() => _showToast = false);
    });
  }

  @override
  Widget build(BuildContext context) {
    final sentPoints = _sentPointsByScenario[_scenario.id] ?? [];
    final queue = _queue;

    return Stack(
      children: [
        Column(
          children: [
            // Top bar
            _AgBar(
              queueCount: queue.length,
              reviewed: _reviewed,
              onResolve: _resolve,
            ),
            // Sub-bar
            _AgSubBar(
              revealLang: _revealLang,
              onLangChange: (l) => setState(() => _revealLang = l),
            ),
            // 3-pane grid
            Expanded(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Left: queue (25%)
                  SizedBox(
                    width: MediaQuery.of(context).size.width * 0.25,
                    child: _QueuePane(
                      queue: queue,
                      activeIdx: _activeIdx,
                      onSelect: (idx) => setState(() {
                        _activeIdx = idx;
                        _reviewed = false;
                      }),
                    ),
                  ),
                  // Center: conversation (45%)
                  Expanded(
                    flex: 45,
                    child: _ConvPane(
                      scenario: _scenario,
                      sessionNum: 2061 + _activeIdx,
                      turns: _scenario.turns,
                      sentPoints: sentPoints,
                      revealLang: _revealLang,
                    ),
                  ),
                  // Right: interpretation (30%)
                  SizedBox(
                    width: MediaQuery.of(context).size.width * 0.30,
                    child: _InterpPane(
                      fields: _fields,
                      scenario: _scenario,
                      reviewed: _reviewed,
                      onApprove: _approveAll,
                      onUpdate: _updateField,
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
            ),
          ),
      ],
    );
  }
}

// ─── Top bar ──────────────────────────────────────────────────────────────────

class _AgBar extends StatelessWidget {
  final int queueCount;
  final bool reviewed;
  final VoidCallback onResolve;
  const _AgBar({required this.queueCount, required this.reviewed, required this.onResolve});

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
          Row(
            children: [
              Container(
                width: 28, height: 28,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(8),
                  gradient: const LinearGradient(
                    begin: Alignment.topLeft, end: Alignment.bottomRight,
                    colors: [AppTheme.teal, AppTheme.teal2],
                  ),
                ),
                child: const Center(
                  child: Text('S', style: TextStyle(color: Color(0xFFF6E2BF), fontWeight: FontWeight.w700, fontSize: 13)),
                ),
              ),
              const SizedBox(width: 10),
              const Text('Samvaad-Setu', style: TextStyle(fontWeight: FontWeight.w600, color: AppTheme.teal2, fontSize: 13)),
              const Text(' · Agent', style: TextStyle(color: AppTheme.muted, fontSize: 13)),
            ],
          ),
          const SizedBox(width: 18),
          // Search
          Expanded(
            child: Container(
              constraints: const BoxConstraints(maxWidth: 480),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
              decoration: BoxDecoration(
                color: const Color(0xFFF4F2EC),
                border: Border.all(color: AppTheme.hair),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Row(
                children: [
                  const Icon(Icons.search, size: 14, color: AppTheme.muted),
                  const SizedBox(width: 8),
                  const Expanded(
                    child: Text('Search by district, intent, session id…',
                        style: TextStyle(fontSize: 13, color: AppTheme.muted)),
                  ),
                  const Text('⌘K', style: TextStyle(fontSize: 11, color: AppTheme.muted, fontFamily: 'JetBrains Mono')),
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
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 1),
                  decoration: BoxDecoration(
                    color: AppTheme.saffron,
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Text('$queueCount',
                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600, fontSize: 11.5)),
                ),
                const SizedBox(width: 8),
                const Text('in queue', style: TextStyle(fontSize: 12.5)),
              ],
            ),
          ),
          const SizedBox(width: 14),
          // Agent
          Row(
            children: [
              Container(
                width: 30, height: 30,
                decoration: const BoxDecoration(shape: BoxShape.circle, color: AppTheme.teal),
                child: const Center(
                  child: Text('PR', style: TextStyle(color: Color(0xFFF6E2BF), fontWeight: FontWeight.w600, fontSize: 12)),
                ),
              ),
              const SizedBox(width: 8),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: const [
                  Text('Priya Rao', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 12.5, color: AppTheme.ink)),
                  Text('AGT-1092-021', style: TextStyle(fontSize: 11, color: AppTheme.muted, fontFamily: 'JetBrains Mono')),
                ],
              ),
            ],
          ),
          const SizedBox(width: 14),
          // Resolve
          GestureDetector(
            onTap: reviewed ? onResolve : null,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
              decoration: BoxDecoration(
                color: reviewed ? AppTheme.teal : const Color(0xFFE6E2D7),
                border: Border.all(color: reviewed ? AppTheme.teal2 : const Color(0xFFDCD6C4)),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.check, size: 14, color: reviewed ? const Color(0xFFFFF7E5) : const Color(0xFF9C9786)),
                  const SizedBox(width: 8),
                  Text('Resolve session',
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: reviewed ? FontWeight.w600 : FontWeight.w500,
                        color: reviewed ? const Color(0xFFFFF7E5) : const Color(0xFF9C9786),
                      )),
                  const SizedBox(width: 6),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                    decoration: BoxDecoration(
                      color: reviewed ? Colors.white.withValues(alpha: 0.18) : Colors.transparent,
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text('R',
                        style: TextStyle(fontSize: 10.5, fontFamily: 'JetBrains Mono',
                            color: reviewed ? const Color(0xFFFFF7E5).withValues(alpha: 0.7) : const Color(0xFF9C9786))),
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

// ─── Sub-bar ──────────────────────────────────────────────────────────────────

class _AgSubBar extends StatelessWidget {
  final String revealLang;
  final ValueChanged<String> onLangChange;
  const _AgSubBar({required this.revealLang, required this.onLangChange});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 6),
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(bottom: BorderSide(color: AppTheme.hair)),
      ),
      child: Row(
        children: [
          _kbdHint('Shortcuts'),
          _kbdKey('A', 'approve'),
          _kbdKey('E', 'edit'),
          _kbdKey('R', 'resolve'),
          _kbdKey('↑↓', 'queue'),
          _kbdKey('?', 'all'),
          const Spacer(),
          const Text('Transcript language',
              style: TextStyle(fontSize: 11.5, color: AppTheme.muted, letterSpacing: 0.04)),
          const SizedBox(width: 8),
          Row(
            children: ['en', 'kn', 'hi'].map((l) {
              final active = revealLang == l;
              return GestureDetector(
                onTap: () => onLangChange(l),
                child: Container(
                  margin: const EdgeInsets.only(left: 4),
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: active ? AppTheme.ink : Colors.white,
                    border: Border.all(color: AppTheme.hair),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(l.toUpperCase(),
                      style: TextStyle(
                        fontSize: 11,
                        color: active ? const Color(0xFFFFF7E5) : AppTheme.ink2,
                        letterSpacing: 0.06,
                        fontFamily: 'JetBrains Mono',
                      )),
                ),
              );
            }).toList(),
          ),
          const SizedBox(width: 14),
          const Text('14:32:08 IST',
              style: TextStyle(fontSize: 11.5, color: AppTheme.muted, fontFamily: 'JetBrains Mono', letterSpacing: 0.06)),
        ],
      ),
    );
  }

  Widget _kbdHint(String label) => Padding(
        padding: const EdgeInsets.only(right: 14),
        child: Text(label, style: const TextStyle(fontSize: 11.5, color: AppTheme.muted, letterSpacing: 0.04)),
      );

  Widget _kbdKey(String key, String label) => Padding(
        padding: const EdgeInsets.only(right: 14),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
              decoration: BoxDecoration(
                color: const Color(0xFFF4F2EC),
                border: Border.all(color: AppTheme.hair),
                borderRadius: BorderRadius.circular(5),
              ),
              child: Text(key,
                  style: const TextStyle(fontFamily: 'JetBrains Mono', fontSize: 10.5, color: AppTheme.ink2, fontWeight: FontWeight.w500)),
            ),
            const SizedBox(width: 4),
            Text(label, style: const TextStyle(fontSize: 11.5, color: AppTheme.muted, letterSpacing: 0.04)),
          ],
        ),
      );
}

// ─── Queue pane ───────────────────────────────────────────────────────────────

class _QueuePane extends StatelessWidget {
  final List<_QueueItem> queue;
  final int activeIdx;
  final ValueChanged<int> onSelect;
  const _QueuePane({required this.queue, required this.activeIdx, required this.onSelect});

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
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(8),
              children: queue.map((q) {
                final scIdx = q.scIdx != null ? int.tryParse(q.scIdx!) : null;
                return Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: _QueueCard(
                    item: q,
                    active: scIdx == activeIdx,
                    onTap: scIdx != null ? () => onSelect(scIdx) : null,
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

class _QueueCard extends StatelessWidget {
  final _QueueItem item;
  final bool active;
  final VoidCallback? onTap;
  const _QueueCard({required this.item, required this.active, this.onTap});

  Color get _priColor {
    if (item.priority == 'high') return AppTheme.red;
    if (item.priority == 'med') return AppTheme.amber;
    return AppTheme.sage;
  }

  Color get _sentColor {
    if (item.sentiment == 'distress') return AppTheme.red;
    if (item.sentiment == 'concerned') return AppTheme.amber;
    return AppTheme.sage;
  }

  Color get _sentBg {
    if (item.sentiment == 'distress') return const Color(0xFFF8DEDA);
    if (item.sentiment == 'concerned') return const Color(0xFFFBEFD0);
    return const Color(0xFFE8F0EA);
  }

  Color get _confColor {
    if (item.conf < 50) return AppTheme.red;
    if (item.conf < 75) return AppTheme.amber;
    return AppTheme.sage;
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          color: Colors.white,
          border: Border(
            top: BorderSide(color: active ? AppTheme.teal : AppTheme.hair),
            right: BorderSide(color: active ? AppTheme.teal : AppTheme.hair),
            bottom: BorderSide(color: active ? AppTheme.teal : AppTheme.hair),
            left: BorderSide(color: _priColor, width: 3),
          ),
          borderRadius: BorderRadius.circular(12),
          boxShadow: active
              ? [BoxShadow(color: AppTheme.teal.withValues(alpha: 0.08), blurRadius: 14, offset: const Offset(0, 4))]
              : null,
        ),
        padding: const EdgeInsets.fromLTRB(12, 11, 12, 11),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(item.ts,
                          style: const TextStyle(fontFamily: 'JetBrains Mono', fontSize: 11, color: AppTheme.muted)),
                      const SizedBox(width: 8),
                      Text(item.district,
                          style: const TextStyle(fontSize: 11.5, color: AppTheme.ink2, fontWeight: FontWeight.w500)),
                      const Spacer(),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 1),
                        decoration: BoxDecoration(
                          color: const Color(0xFFF4F2EC),
                          borderRadius: BorderRadius.circular(999),
                        ),
                        child: Text(item.lang.toUpperCase(),
                            style: const TextStyle(fontFamily: 'JetBrains Mono', fontSize: 10.5, color: AppTheme.ink2)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(item.intent,
                      style: const TextStyle(fontSize: 13.5, color: AppTheme.ink, height: 1.45),
                      maxLines: 2, overflow: TextOverflow.ellipsis),
                  const SizedBox(height: 6),
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                        decoration: BoxDecoration(color: _sentBg, borderRadius: BorderRadius.circular(999)),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Container(width: 6, height: 6, decoration: BoxDecoration(shape: BoxShape.circle, color: _sentColor)),
                            const SizedBox(width: 6),
                            Text(item.sentiment,
                                style: TextStyle(fontSize: 11.5, color: _sentColor, fontWeight: FontWeight.w500)),
                          ],
                        ),
                      ),
                      const SizedBox(width: 8),
                      Text('· ${item.dialect}', style: const TextStyle(fontSize: 11.5, color: AppTheme.muted)),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(width: 10),
            _MiniRing(value: item.conf, color: _confColor),
          ],
        ),
      ),
    );
  }
}

class _MiniRing extends StatelessWidget {
  final int value;
  final Color color;
  const _MiniRing({required this.value, required this.color});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 32, height: 32,
      child: CustomPaint(
        painter: _RingPainter(value / 100.0, color, const Color(0xFFEFEAD9), 4),
        child: Center(
          child: Text('$value',
              style: const TextStyle(fontSize: 9, fontWeight: FontWeight.w600, fontFamily: 'JetBrains Mono', color: AppTheme.ink)),
        ),
      ),
    );
  }
}

// ─── Center pane: conversation ────────────────────────────────────────────────

class _ConvPane extends StatelessWidget {
  final _ScenarioData scenario;
  final int sessionNum;
  final List<_Turn> turns;
  final List<_SentPoint> sentPoints;
  final String revealLang;
  const _ConvPane({
    required this.scenario,
    required this.sessionNum,
    required this.turns,
    required this.sentPoints,
    required this.revealLang,
  });

  Color get _sentBg {
    if (scenario.sentiment == 'distress') return const Color(0xFFFFF4F2);
    if (scenario.sentiment == 'concerned') return const Color(0xFFFFF7E8);
    return const Color(0xFFF1F8F4);
  }

  Color get _sentBorderColor {
    if (scenario.sentiment == 'distress') return const Color(0xFFF2D5CE);
    if (scenario.sentiment == 'concerned') return const Color(0xFFF1DDA7);
    return const Color(0xFFCFE1D6);
  }

  Color get _sentTextColor {
    if (scenario.sentiment == 'distress') return const Color(0xFF7A1F1F);
    if (scenario.sentiment == 'concerned') return const Color(0xFF7A5A14);
    return const Color(0xFF2E5640);
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: AppTheme.agentBg,
        border: Border(right: BorderSide(color: AppTheme.hair)),
      ),
      child: Column(
        children: [
          _PaneHeader(title: 'Live conversation', meta: 'SESSION #$sessionNum'),
          // Meta bar
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
            color: Colors.white,
            child: Wrap(
              spacing: 18,
              runSpacing: 8,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                _MetaItem('District', scenario.district),
                _MetaItem('Dialect', scenario.dialect),
                _MetaItem('Language', 'Kannada (auto-detected)'),
                _MetaItem('Started', '14:${21 + 0}:42', mono: true),
                _MetaItem('Duration', '02:14', mono: true),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
                  decoration: BoxDecoration(
                    color: _sentBg,
                    border: Border.all(color: _sentBorderColor),
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Container(width: 6, height: 6, decoration: BoxDecoration(shape: BoxShape.circle, color: _sentTextColor)),
                      const SizedBox(width: 6),
                      Text('Sentiment: ${scenario.sentiment}',
                          style: TextStyle(fontSize: 11.5, color: _sentTextColor)),
                    ],
                  ),
                ),
              ],
            ),
          ),
          // Turns
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(18),
              child: Column(
                children: turns.map((t) => Padding(
                  padding: const EdgeInsets.only(bottom: 14),
                  child: _TurnRow(turn: t, revealLang: revealLang),
                )).toList(),
              ),
            ),
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
                      Text('Sentiment over last ${sentPoints.length} turns',
                          style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                      const Spacer(),
                      Row(
                        children: [
                          _LegendDot(color: AppTheme.sage, label: 'calm'),
                          const SizedBox(width: 10),
                          _LegendDot(color: AppTheme.amber, label: 'concerned'),
                          const SizedBox(width: 10),
                          _LegendDot(color: AppTheme.red, label: 'distress'),
                        ],
                      ),
                    ],
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
                  child: SizedBox(
                    height: 100,
                    child: CustomPaint(
                      painter: _SentimentLinePainter(sentPoints),
                      size: const Size(double.infinity, 100),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _MetaItem extends StatelessWidget {
  final String label;
  final String value;
  final bool mono;
  const _MetaItem(this.label, this.value, {this.mono = false});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label.toUpperCase(),
            style: const TextStyle(fontSize: 10.5, letterSpacing: 0.08, color: AppTheme.muted)),
        const SizedBox(height: 1),
        Text(value,
            style: TextStyle(fontSize: 13, fontWeight: FontWeight.w500, color: AppTheme.ink,
                fontFamily: mono ? 'JetBrains Mono' : 'Inter')),
      ],
    );
  }
}

class _TurnRow extends StatelessWidget {
  final _Turn turn;
  final String revealLang;
  const _TurnRow({required this.turn, required this.revealLang});

  String get _text {
    if (revealLang == 'kn') return turn.textKn;
    if (revealLang == 'hi') return turn.textHi;
    return turn.textEn;
  }

  Color get _confColor {
    if (turn.conf < 70) return const Color(0xFF7A1F1F);
    if (turn.conf < 85) return const Color(0xFF7A5A14);
    return const Color(0xFF2E5640);
  }

  Color get _confBg {
    if (turn.conf < 70) return const Color(0xFFFFF4F2);
    if (turn.conf < 85) return const Color(0xFFFFF7E8);
    return const Color(0xFFF1F8F4);
  }

  Color get _confBorder {
    if (turn.conf < 70) return const Color(0xFFF2D5CE);
    if (turn.conf < 85) return const Color(0xFFF1DDA7);
    return const Color(0xFFCFE1D6);
  }

  String get _fontFamily {
    if (revealLang == 'kn') return 'Noto Sans Kannada';
    if (revealLang == 'hi') return 'Noto Sans Devanagari';
    return 'Inter';
  }

  @override
  Widget build(BuildContext context) {
    final isCit = turn.who == 'cit';
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 30, height: 30,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: isCit ? const Color(0xFFFFF1DD) : AppTheme.tealSoft,
            border: Border.all(color: isCit ? const Color(0xFFF1DDA7) : const Color(0xFFC9DCD5)),
          ),
          child: Center(
            child: Text(isCit ? 'C' : 'AI',
                style: TextStyle(
                  fontSize: 10.5, fontWeight: FontWeight.w700, letterSpacing: 0.04,
                  color: isCit ? AppTheme.saffron2 : AppTheme.teal2,
                )),
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Text(isCit ? 'Citizen' : 'AI Assistant',
                      style: const TextStyle(fontSize: 11, letterSpacing: 0.08, color: AppTheme.muted)),
                  if (turn.verify) ...[
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                      decoration: BoxDecoration(
                        color: AppTheme.tealSoft,
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: const Text('VERIFY TURN',
                          style: TextStyle(fontSize: 10, color: AppTheme.teal)),
                    ),
                  ],
                  const SizedBox(width: 8),
                  Text(turn.ts,
                      style: const TextStyle(fontSize: 11, color: AppTheme.muted, fontFamily: 'JetBrains Mono')),
                ],
              ),
              const SizedBox(height: 4),
              Text(_text,
                  style: TextStyle(fontSize: 14, height: 1.55, color: AppTheme.ink, fontFamily: _fontFamily)),
            ],
          ),
        ),
        const SizedBox(width: 10),
        Column(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            if (isCit)
              Container(
                width: 24, height: 24,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: Colors.white,
                  border: Border.all(color: AppTheme.hair),
                ),
                child: const Icon(Icons.play_arrow, size: 10, color: AppTheme.teal),
              ),
            const SizedBox(height: 4),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 1),
              decoration: BoxDecoration(
                color: _confBg,
                border: Border.all(color: _confBorder),
                borderRadius: BorderRadius.circular(999),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(width: 5, height: 5, decoration: BoxDecoration(shape: BoxShape.circle, color: _confColor)),
                  const SizedBox(width: 4),
                  Text('${turn.conf}%',
                      style: TextStyle(fontSize: 10.5, color: _confColor, fontFamily: 'JetBrains Mono')),
                ],
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _LegendDot extends StatelessWidget {
  final Color color;
  final String label;
  const _LegendDot({required this.color, required this.label});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(width: 8, height: 8, decoration: BoxDecoration(shape: BoxShape.circle, color: color)),
        const SizedBox(width: 5),
        Text(label, style: const TextStyle(fontSize: 11, color: AppTheme.muted)),
      ],
    );
  }
}

// ─── Right pane: AI interpretation ───────────────────────────────────────────

class _InterpPane extends StatelessWidget {
  final Map<String, dynamic> fields;
  final _ScenarioData scenario;
  final bool reviewed;
  final VoidCallback onApprove;
  final void Function(String, dynamic) onUpdate;
  const _InterpPane({
    required this.fields,
    required this.scenario,
    required this.reviewed,
    required this.onApprove,
    required this.onUpdate,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      color: AppTheme.agentBg,
      child: Column(
        children: [
          _PaneHeader(title: 'AI interpretation', meta: reviewed ? 'Reviewed' : 'Inline-editable'),
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Approve button
                  GestureDetector(
                    onTap: onApprove,
                    child: Container(
                      padding: const EdgeInsets.symmetric(vertical: 9),
                      decoration: BoxDecoration(
                        color: AppTheme.teal,
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(Icons.check, size: 14, color: Color(0xFFFFF7E5)),
                          const SizedBox(width: 8),
                          Text(reviewed ? 'Approved' : 'Approve all',
                              style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: Color(0xFFFFF7E5))),
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                            decoration: BoxDecoration(
                              color: Colors.white.withValues(alpha: 0.18),
                              borderRadius: BorderRadius.circular(5),
                            ),
                            child: const Text('A',
                                style: TextStyle(fontFamily: 'JetBrains Mono', fontSize: 10.5, color: Color(0xFFFFF7E5))),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 10),
                  _EditableField(label: 'Intent', value: fields['intent'] ?? '', onSave: (v) => onUpdate('intent', v)),
                  _EditableField(label: 'Sub-intent', value: fields['subIntent'] ?? '', onSave: (v) => onUpdate('subIntent', v)),
                  _EditableField(label: 'Department', value: fields['department'] ?? '', onSave: (v) => onUpdate('department', v)),
                  _UrgencyField(value: fields['urgency'] ?? 'low', onSave: (v) => onUpdate('urgency', v)),
                  _EntitiesField(entities: List<String>.from(fields['entities'] ?? []), onSave: (v) => onUpdate('entities', v)),
                  _EditableField(label: 'Dialect tag', value: fields['dialect'] ?? '', onSave: (v) => onUpdate('dialect', v)),
                  _EditableField(label: 'Recommended action', value: fields['action'] ?? '', onSave: (v) => onUpdate('action', v), multiline: true),
                  const SizedBox(height: 6),
                  // Confidence gauge
                  _ConfGaugeCard(scenario: scenario),
                  const SizedBox(height: 8),
                  // Mark for review
                  Container(
                    padding: const EdgeInsets.symmetric(vertical: 9, horizontal: 12),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      border: Border.all(color: AppTheme.hair),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: const [
                        Icon(Icons.info_outline_rounded, size: 13, color: AppTheme.muted),
                        SizedBox(width: 6),
                        Text('Mark for senior review',
                            style: TextStyle(fontSize: 12.5, color: AppTheme.ink)),
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
  const _EditableField({required this.label, required this.value, required this.onSave, this.multiline = false});

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
  void didUpdateWidget(covariant _EditableField oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.value != widget.value && !_editing) {
      _ctrl.text = widget.value;
    }
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
      decoration: const BoxDecoration(border: Border(bottom: BorderSide(color: AppTheme.hair, width: 0.5))),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 110,
            child: Padding(
              padding: const EdgeInsets.only(top: 5),
              child: Text(widget.label.toUpperCase(),
                  style: const TextStyle(fontSize: 11, letterSpacing: 0.08, color: AppTheme.muted)),
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
                    style: const TextStyle(fontSize: 13.5, color: AppTheme.ink, fontWeight: FontWeight.w500),
                    decoration: InputDecoration(
                      isDense: true,
                      contentPadding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(6),
                        borderSide: const BorderSide(color: AppTheme.teal),
                      ),
                      focusedBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(6),
                        borderSide: const BorderSide(color: AppTheme.teal),
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
                              style: const TextStyle(fontSize: 13.5, color: AppTheme.ink, fontWeight: FontWeight.w500, height: 1.35)),
                        ),
                        const SizedBox(width: 4),
                        const Icon(Icons.edit_outlined, size: 12, color: AppTheme.muted),
                      ],
                    ),
                  ),
          ),
        ],
      ),
    );
  }
}

class _UrgencyField extends StatelessWidget {
  final String value;
  final ValueChanged<String> onSave;
  const _UrgencyField({required this.value, required this.onSave});

  Color get _bg => value == 'high' ? const Color(0xFFF8DEDA) : value == 'medium' ? const Color(0xFFFBEFD0) : const Color(0xFFE8F0EA);
  Color get _fg => value == 'high' ? const Color(0xFF7A1F1F) : value == 'medium' ? const Color(0xFF7A5A14) : const Color(0xFF2E5640);

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 4),
      decoration: const BoxDecoration(border: Border(bottom: BorderSide(color: AppTheme.hair, width: 0.5))),
      child: Row(
        children: [
          const SizedBox(
            width: 110,
            child: Text('URGENCY', style: TextStyle(fontSize: 11, letterSpacing: 0.08, color: AppTheme.muted)),
          ),
          const SizedBox(width: 10),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
            decoration: BoxDecoration(color: _bg, borderRadius: BorderRadius.circular(999)),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(width: 6, height: 6, decoration: BoxDecoration(shape: BoxShape.circle, color: _fg)),
                const SizedBox(width: 6),
                Text(value, style: TextStyle(fontSize: 11.5, color: _fg, fontWeight: FontWeight.w500)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _EntitiesField extends StatelessWidget {
  final List<String> entities;
  final ValueChanged<List<String>> onSave;
  const _EntitiesField({required this.entities, required this.onSave});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 4),
      decoration: const BoxDecoration(border: Border(bottom: BorderSide(color: AppTheme.hair, width: 0.5))),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(
            width: 110,
            child: Padding(
              padding: EdgeInsets.only(top: 5),
              child: Text('KEY ENTITIES', style: TextStyle(fontSize: 11, letterSpacing: 0.08, color: AppTheme.muted)),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: entities.map((e) => Padding(
                padding: const EdgeInsets.only(bottom: 2),
                child: Text('• $e',
                    style: const TextStyle(fontSize: 13.5, color: AppTheme.ink, fontWeight: FontWeight.w500, height: 1.35)),
              )).toList(),
            ),
          ),
        ],
      ),
    );
  }
}

class _ConfGaugeCard extends StatelessWidget {
  final _ScenarioData scenario;
  const _ConfGaugeCard({required this.scenario});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border.all(color: AppTheme.hair),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          SizedBox(
            width: 128, height: 128,
            child: CustomPaint(
              painter: _RingPainter(
                scenario.confTotal / 100.0,
                scenario.confTotal < 50 ? AppTheme.red : scenario.confTotal < 75 ? AppTheme.amber : AppTheme.sage,
                const Color(0xFFEFEAD9),
                10,
              ),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text('${scenario.confTotal}',
                      style: const TextStyle(fontSize: 30, fontWeight: FontWeight.w600, fontFamily: 'JetBrains Mono', color: AppTheme.ink)),
                  const Text('CONFIDENCE',
                      style: TextStyle(fontSize: 9, letterSpacing: 2, color: AppTheme.muted)),
                ],
              ),
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              children: [
                _SubMeter(label: 'ASR', value: scenario.confAsr),
                const SizedBox(height: 8),
                _SubMeter(label: 'Intent', value: scenario.confIntent),
                const SizedBox(height: 8),
                _SubMeter(label: 'Sentiment', value: scenario.confSentiment),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _SubMeter extends StatelessWidget {
  final String label;
  final int value;
  const _SubMeter({required this.label, required this.value});

  Color get _color => value < 50 ? AppTheme.red : value < 75 ? AppTheme.amber : AppTheme.sage;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        SizedBox(
          width: 60,
          child: Text(label.toUpperCase(),
              style: const TextStyle(fontSize: 10.5, letterSpacing: 0.04, color: AppTheme.muted)),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Container(
            height: 6,
            decoration: BoxDecoration(
              color: const Color(0xFFF4F2EC),
              borderRadius: BorderRadius.circular(3),
            ),
            child: FractionallySizedBox(
              widthFactor: value / 100.0,
              alignment: Alignment.centerLeft,
              child: Container(
                decoration: BoxDecoration(color: _color, borderRadius: BorderRadius.circular(3)),
              ),
            ),
          ),
        ),
        const SizedBox(width: 8),
        SizedBox(
          width: 36,
          child: Text('$value%',
              textAlign: TextAlign.right,
              style: const TextStyle(fontFamily: 'JetBrains Mono', fontSize: 11.5, color: AppTheme.ink2)),
        ),
      ],
    );
  }
}

// ─── Toast ────────────────────────────────────────────────────────────────────

class _Toast extends StatelessWidget {
  final String title;
  final String body;
  final bool high;
  final VoidCallback onDismiss;
  const _Toast({required this.title, required this.body, required this.high, required this.onDismiss});

  @override
  Widget build(BuildContext context) {
    final accentColor = high ? AppTheme.red : AppTheme.sage;
    return Container(
      width: 320,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border(
          top: BorderSide(color: AppTheme.hair),
          right: BorderSide(color: AppTheme.hair),
          bottom: BorderSide(color: AppTheme.hair),
          left: BorderSide(color: accentColor, width: 4),
        ),
        borderRadius: BorderRadius.circular(12),
        boxShadow: const [
          BoxShadow(color: Color(0x2E000000), blurRadius: 40, offset: Offset(0, 14)),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              Container(width: 8, height: 8, decoration: BoxDecoration(shape: BoxShape.circle, color: accentColor)),
              const SizedBox(width: 8),
              Expanded(
                child: Text(title, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13, color: AppTheme.ink)),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(body, style: const TextStyle(fontSize: 12.5, color: AppTheme.ink2, height: 1.45)),
          if (high) ...[
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.symmetric(vertical: 6),
                    decoration: BoxDecoration(color: AppTheme.teal, borderRadius: BorderRadius.circular(8)),
                    child: const Center(
                      child: Text('Switch to this session',
                          style: TextStyle(fontSize: 12, color: Color(0xFFFFF7E5))),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                GestureDetector(
                  onTap: onDismiss,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      border: Border.all(color: AppTheme.hair),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Text('Dismiss', style: TextStyle(fontSize: 12, color: AppTheme.ink)),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

// ─── Shared: pane header ──────────────────────────────────────────────────────

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
          Text(title, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
          const Spacer(),
          Text(meta,
              style: const TextStyle(
                  fontSize: 11.5, color: AppTheme.muted, letterSpacing: 0.04, fontFamily: 'JetBrains Mono')),
        ],
      ),
    );
  }
}

// ─── Painters ─────────────────────────────────────────────────────────────────

class _RingPainter extends CustomPainter {
  final double progress;
  final Color color;
  final Color trackColor;
  final double strokeWidth;
  const _RingPainter(this.progress, this.color, this.trackColor, this.strokeWidth);

  @override
  void paint(Canvas canvas, Size size) {
    final cx = size.width / 2;
    final cy = size.height / 2;
    final r = (math.min(size.width, size.height) - strokeWidth) / 2;
    final rect = Rect.fromCircle(center: Offset(cx, cy), radius: r);
    final trackPaint = Paint()
      ..color = trackColor
      ..strokeWidth = strokeWidth
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;
    canvas.drawCircle(Offset(cx, cy), r, trackPaint);
    final arcPaint = Paint()
      ..color = color
      ..strokeWidth = strokeWidth
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;
    canvas.drawArc(rect, -math.pi / 2, 2 * math.pi * progress.clamp(0, 1), false, arcPaint);
  }

  @override
  bool shouldRepaint(covariant _RingPainter old) =>
      old.progress != progress || old.color != color;
}

class _SentimentLinePainter extends CustomPainter {
  final List<_SentPoint> points;
  const _SentimentLinePainter(this.points);

  Color _colorFor(String s) {
    if (s == 'calm') return AppTheme.sage;
    if (s == 'concerned') return AppTheme.amber;
    return AppTheme.red;
  }

  @override
  void paint(Canvas canvas, Size size) {
    if (points.length < 2) return;
    const padX = 24.0;
    const padY = 18.0;
    double xs(int i) => padX + (i / (points.length - 1)) * (size.width - 2 * padX);
    double ys(double v) => padY + (1 - (v + 1) / 2) * (size.height - 2 * padY);

    // Grid lines
    final gridPaint = Paint()..color = const Color(0xFFEFEAD9)..strokeWidth = 1;
    for (final v in [1.0, 0.5, 0.0, -0.5, -1.0]) {
      final y = ys(v);
      if (v == 0.0) {
        canvas.drawLine(Offset(padX, y), Offset(size.width - padX, y), gridPaint);
      } else {
        const dashLen = 2.0;
        const gapLen = 4.0;
        var x = padX;
        while (x < size.width - padX) {
          canvas.drawLine(Offset(x, y), Offset(x + dashLen, y), gridPaint);
          x += dashLen + gapLen;
        }
      }
    }

    // Build path
    final path = Path();
    path.moveTo(xs(0), ys(points[0].v));
    for (var i = 1; i < points.length; i++) {
      final x0 = xs(i - 1); final y0 = ys(points[i - 1].v);
      final x1 = xs(i); final y1 = ys(points[i].v);
      final cx = (x0 + x1) / 2;
      path.cubicTo(cx, y0, cx, y1, x1, y1);
    }

    // Fill area
    final fillPath = Path.from(path);
    fillPath.lineTo(size.width - padX, size.height - padY);
    fillPath.lineTo(padX, size.height - padY);
    fillPath.close();
    canvas.drawPath(
      fillPath,
      Paint()
        ..color = AppTheme.teal.withValues(alpha: 0.08)
        ..style = PaintingStyle.fill,
    );

    // Line
    canvas.drawPath(
      path,
      Paint()
        ..color = AppTheme.teal
        ..strokeWidth = 1.6
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.round
        ..strokeJoin = StrokeJoin.round,
    );

    // Dots
    for (var i = 0; i < points.length; i++) {
      final x = xs(i); final y = ys(points[i].v);
      canvas.drawCircle(Offset(x, y), 4.5, Paint()..color = _colorFor(points[i].s));
      canvas.drawCircle(Offset(x, y), 4.5, Paint()
        ..color = Colors.white
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.5);
    }
  }

  @override
  bool shouldRepaint(covariant _SentimentLinePainter old) => old.points != points;
}
