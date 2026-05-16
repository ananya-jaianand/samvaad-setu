import 'package:flutter/foundation.dart' show kIsWeb;

/// Backend connection configuration.
///
/// Priority order:
///   1. Build-time --dart-define flags (BACKEND_URL, WS_URL)
///   2. Auto-detected from page origin on Flutter Web
///   3. Localhost defaults for native/desktop dev
class AppConfig {
  static const _envBackendUrl =
      String.fromEnvironment('BACKEND_URL', defaultValue: '');
  static const _envWsUrl =
      String.fromEnvironment('WS_URL', defaultValue: '');

  static String get backendUrl {
    if (_envBackendUrl.isNotEmpty) return _envBackendUrl;
    if (kIsWeb) return _autoBackendUrl();
    return 'http://localhost:8000';
  }

  static String get wsUrl {
    if (_envWsUrl.isNotEmpty) return _envWsUrl;
    if (kIsWeb) {
      final base = _autoBackendUrl();
      final wsBase = base
          .replaceFirst('https://', 'wss://')
          .replaceFirst('http://', 'ws://');
      return '$wsBase/ws';
    }
    return 'ws://localhost:8000/ws';
  }

  /// Derives the backend URL from the current page origin.
  /// On localhost, assumes the backend is on port 8000.
  /// On any other host, assumes the backend is co-hosted at the same origin.
  static String _autoBackendUrl() {
    final origin = Uri.base.origin; // e.g. "https://samvaad-setu.onrender.com"
    if (origin.contains('localhost') || origin.contains('127.0.0.1')) {
      return 'http://localhost:8000';
    }
    return origin;
  }

  static const String defaultDistrict = String.fromEnvironment(
    'DEFAULT_DISTRICT',
    defaultValue: 'mangaluru',
  );

  static const String defaultLanguage = String.fromEnvironment(
    'DEFAULT_LANGUAGE',
    defaultValue: 'kn',
  );
}