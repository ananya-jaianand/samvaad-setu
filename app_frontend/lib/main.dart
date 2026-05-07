import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'theme/app_theme.dart';
import 'screens/citizen_view.dart';
import 'screens/agent_dashboard.dart';
import 'config/app_config.dart';

void main() {
  runApp(const SamvaadSetuApp());
}

class SamvaadSetuApp extends StatelessWidget {
  const SamvaadSetuApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Samvaad-Setu',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.theme,
      home: const AppShell(),
    );
  }
}

class AppShell extends StatefulWidget {
  const AppShell({super.key});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  bool _showAgent = false;

  /// Actual backend environment — fetched from /health on startup.
  /// Values: 'mock', 'production', or '' while loading.
  String _backendMode = '';

  /// Demo data toggle — seeds pre-built Karnataka 1092 sessions into the agent queue.
  bool _demoDataEnabled = false;

  @override
  void initState() {
    super.initState();
    _fetchBackendMode();
  }

  Future<void> _fetchBackendMode() async {
    try {
      final res = await http
          .get(Uri.parse('${AppConfig.backendUrl}/health'))
          .timeout(const Duration(seconds: 4));
      if (res.statusCode == 200 && mounted) {
        final data = jsonDecode(res.body) as Map<String, dynamic>;
        setState(() => _backendMode = (data['mode'] as String?) ?? 'unknown');
      }
    } catch (_) {
      if (mounted) setState(() => _backendMode = 'unknown');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _showAgent ? AppTheme.agentBg : AppTheme.ivory,
      body: Column(
        children: [
          _TopNav(
            showAgent: _showAgent,
            onToggle: (v) => setState(() => _showAgent = v),
            backendMode: _backendMode,
          ),
          Expanded(
            child: _showAgent
                ? AgentDashboard(
                    demoDataEnabled: _demoDataEnabled,
                    onDemoToggle: (v) => setState(() => _demoDataEnabled = v),
                  )
                : const CitizenView(),
          ),
        ],
      ),
    );
  }
}

class _TopNav extends StatelessWidget {
  final bool showAgent;
  final ValueChanged<bool> onToggle;
  final String backendMode;

  const _TopNav({
    required this.showAgent,
    required this.onToggle,
    required this.backendMode,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      color: AppTheme.shellBg,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            decoration: const BoxDecoration(
              border: Border(
                bottom: BorderSide(color: AppTheme.shellBorder),
              ),
            ),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            child: Row(
              children: [
                // Brand
                Row(
                  children: [
                    Container(
                      width: 10,
                      height: 10,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: AppTheme.saffron,
                        boxShadow: [
                          BoxShadow(
                            color: AppTheme.saffron.withOpacity(0.18),
                            blurRadius: 0,
                            spreadRadius: 3,
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 10),
                    const Text(
                      'Samvaad-Setu',
                      style: TextStyle(
                        color: AppTheme.shellText,
                        fontWeight: FontWeight.w600,
                        fontSize: 13,
                        letterSpacing: 0.01,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      '· Karnataka 1092',
                      style: TextStyle(
                        color: AppTheme.shellMuted,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
                const Spacer(),
                // Segmented control
                Container(
                  padding: const EdgeInsets.all(3),
                  decoration: BoxDecoration(
                    color: const Color(0xFF171612),
                    border: Border.all(color: const Color(0xFF26241D)),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      _SegBtn(
                        label: 'Citizen',
                        active: !showAgent,
                        onTap: () => onToggle(false),
                      ),
                      _SegBtn(
                        label: 'Agent',
                        active: showAgent,
                        onTap: () => onToggle(true),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 14),
                // Dynamic backend mode badge — only show when backend has responded
                if (backendMode.isNotEmpty) _ModeBadge(mode: backendMode),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ModeBadge extends StatelessWidget {
  final String mode;
  const _ModeBadge({required this.mode});

  @override
  Widget build(BuildContext context) {
    final isMock = mode == 'mock';
    final dotColor = isMock ? AppTheme.sage : const Color(0xFF4DA6FF);
    final label = isMock ? 'Mock mode' : mode == 'production' ? 'Production' : mode;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: const Color(0xFF171612),
        border: Border.all(color: const Color(0xFF26241D)),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 6,
            height: 6,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: dotColor,
            ),
          ),
          const SizedBox(width: 6),
          Text(
            label,
            style: const TextStyle(
              color: Color(0xFFCFC8B4),
              fontSize: 11.5,
            ),
          ),
        ],
      ),
    );
  }
}

class _SegBtn extends StatelessWidget {
  final String label;
  final bool active;
  final VoidCallback onTap;

  const _SegBtn(
      {required this.label, required this.active, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: active ? const Color(0xFFE8E2D2) : Colors.transparent,
          borderRadius: BorderRadius.circular(7),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: active ? const Color(0xFF0E0E0C) : const Color(0xFF9C9786),
            fontSize: 12,
            fontWeight: active ? FontWeight.w600 : FontWeight.w400,
          ),
        ),
      ),
    );
  }
}
