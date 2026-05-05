import 'package:flutter/material.dart';
import 'screens/home_screen.dart';

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
      theme: ThemeData(
        brightness: Brightness.light,
        scaffoldBackgroundColor: const Color(0xFFF5F5F7), // PocketSage background
        colorScheme: const ColorScheme.light(
          primary: Color(0xFF826695), // PocketSage Purple
          secondary: Color(0xFF2D223A), // Dark text color
          error: Color(0xFFEF4444),
          surface: Colors.white,
        ),
        fontFamily: 'Montserrat', // PocketSage font preference
        appBarTheme: const AppBarTheme(
          backgroundColor: Colors.white,
          foregroundColor: Color(0xFF2D223A),
          elevation: 0,
          scrolledUnderElevation: 0,
          centerTitle: true,
          iconTheme: IconThemeData(color: Color(0xFF826695)),
        ),
      ),
      home: const HomeScreen(),
    );
  }
}
