import 'package:flutter/material.dart';

class AppTheme {
  static const Color ivory = Color(0xFFFBF6EC);
  static const Color ivory2 = Color(0xFFF4ECD8);
  static const Color teal = Color(0xFF0F4C46);
  static const Color teal2 = Color(0xFF0B3A35);
  static const Color tealSoft = Color(0xFFE8EFEC);
  static const Color saffron = Color(0xFFD67B2C);
  static const Color saffron2 = Color(0xFFB8651E);
  static const Color ink = Color(0xFF1B1A17);
  static const Color ink2 = Color(0xFF3A3833);
  static const Color muted = Color(0xFF6E6A60);
  static const Color hair = Color(0xFFE6E0CF);
  static const Color sage = Color(0xFF5B8A72);
  static const Color amber = Color(0xFFD4A547);
  static const Color red = Color(0xFFC04545);
  static const Color agentBg = Color(0xFFF6F5F1);
  static const Color shellBg = Color(0xFF0E0E0C);
  static const Color shellBorder = Color(0xFF1F1D18);
  static const Color shellText = Color(0xFFE8E2D2);
  static const Color shellMuted = Color(0xFF8A8676);

  static ThemeData get theme => ThemeData(
        brightness: Brightness.light,
        scaffoldBackgroundColor: ivory,
        fontFamily: 'Inter',
        colorScheme: const ColorScheme.light(
          primary: teal,
          secondary: saffron,
          surface: Colors.white,
          error: red,
        ),
        appBarTheme: const AppBarTheme(
          backgroundColor: shellBg,
          foregroundColor: shellText,
          elevation: 0,
          scrolledUnderElevation: 0,
          centerTitle: false,
        ),
      );
}
