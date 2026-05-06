import 'package:flutter/material.dart';
import 'theme/app_theme.dart';
import 'screens/citizen_view.dart';
import 'screens/agent_dashboard.dart';

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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _showAgent ? AppTheme.agentBg : AppTheme.ivory,
      body: Column(
        children: [
          _TopNav(
            showAgent: _showAgent,
            onToggle: (v) => setState(() => _showAgent = v),
          ),
          Expanded(
            child: _showAgent ? const AgentDashboard() : const CitizenView(),
          ),
        ],
      ),
    );
  }
}

class _TopNav extends StatelessWidget {
  final bool showAgent;
  final ValueChanged<bool> onToggle;

  const _TopNav({required this.showAgent, required this.onToggle});

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
                // Mock badge
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
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
                        decoration: const BoxDecoration(
                          shape: BoxShape.circle,
                          color: AppTheme.sage,
                        ),
                      ),
                      const SizedBox(width: 6),
                      const Text(
                        'Mock mode',
                        style: TextStyle(
                          color: Color(0xFFCFC8B4),
                          fontSize: 11.5,
                        ),
                      ),
                    ],
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
