/// Backend connection configuration.
/// Pass values at build time with --dart-define flags:
///   flutter run -d chrome --dart-define=BACKEND_URL=http://192.168.1.10:8000
/// Or edit the defaultValue strings below for local development.
class AppConfig {
  static const String backendUrl = String.fromEnvironment(
    'BACKEND_URL',
    defaultValue: 'http://localhost:8000',
  );

  static const String wsUrl = String.fromEnvironment(
    'WS_URL',
    defaultValue: 'ws://localhost:8000/ws',
  );

  static const String defaultDistrict = String.fromEnvironment(
    'DEFAULT_DISTRICT',
    defaultValue: 'mangaluru',
  );

  static const String defaultLanguage = String.fromEnvironment(
    'DEFAULT_LANGUAGE',
    defaultValue: 'kn',
  );
}
