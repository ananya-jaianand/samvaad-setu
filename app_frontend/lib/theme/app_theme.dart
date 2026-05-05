import 'package:flutter/material.dart';

class AppTheme {
  // Backgrounds
  static const Color scaffoldBg = Color(0xFF08080F);
  static const Color cardBg = Color(0xFF11111C);
  static const Color cardBg2 = Color(0xFF191928);
  static const Color inputBg = Color(0xFF1E1E30);

  // Status
  static const Color green = Color(0xFF00D26A);
  static const Color greenBg = Color(0xFF092B1A);
  static const Color red = Color(0xFFEF4444);
  static const Color redBg = Color(0xFF2B0F0F);
  static const Color orange = Color(0xFFF59E0B);
  static const Color orangeBg = Color(0xFF2B1E0A);
  static const Color purple = Color(0xFF8B5CF6);
  static const Color purpleBg = Color(0xFF1A1040);
  static const Color teal = Color(0xFF06B6D4);
  static const Color tealBg = Color(0xFF0A2130);

  // Text
  static const Color textPrimary = Color(0xFFF1F5F9);
  static const Color textSecondary = Color(0xFF94A3B8);
  static const Color textMuted = Color(0xFF475569);

  // Bubbles
  static const Color citizenBubble = Color(0xFF14213D);
  static const Color citizenHighStress = Color(0xFF2D1520);
  static const Color aiBubble = Color(0xFF16112A);

  // Borders
  static const Color border = Color(0xFF1E2D3D);
  static const Color borderBright = Color(0xFF2D3B50);

  static ThemeData get darkTheme => ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: scaffoldBg,
        fontFamily: 'Roboto',
        colorScheme: const ColorScheme.dark(
          primary: purple,
          secondary: green,
          surface: cardBg,
          error: red,
        ),
        appBarTheme: const AppBarTheme(
          backgroundColor: cardBg,
          elevation: 0,
          centerTitle: false,
          iconTheme: IconThemeData(color: textSecondary),
          titleTextStyle: TextStyle(
            color: textPrimary,
            fontSize: 18,
            fontWeight: FontWeight.w700,
            letterSpacing: 0.5,
          ),
        ),
      );
}
