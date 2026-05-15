import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:record/record.dart';
import 'package:audioplayers/audioplayers.dart';
import '../models/session_models.dart';
import '../config/app_config.dart';

enum PipelineState {
  idle,
  starting,
  ready,
  listening,
  processing,
  speaking,
  verifying,
  escalated,
  error,
}

class VoicePipelineService {
  final String backendUrl = AppConfig.backendUrl;
  final String wsUrl = AppConfig.wsUrl;

  String? sessionId;
  WebSocketChannel? _channel;
  final AudioRecorder _record = AudioRecorder();
  final AudioPlayer _audioPlayer = AudioPlayer();

  // Streams
  final _stateCtrl = StreamController<PipelineState>.broadcast();
  final _turnsCtrl = StreamController<List<SessionTurn>>.broadcast();
  final _errorCtrl = StreamController<String>.broadcast();
  final _escalationCtrl = StreamController<EscalationPacket?>.broadcast();
  final _sessionMetaCtrl = StreamController<SessionMeta?>.broadcast();
  final _nluCtrl = StreamController<NluResult?>.broadcast();
  final _verifyPromptCtrl = StreamController<VerificationPrompt?>.broadcast();
  final _confidenceCtrl = StreamController<ConfidenceScore?>.broadcast();
  final _mockModeCtrl = StreamController<bool?>.broadcast();
  final _ticketCtrl = StreamController<TicketInfo?>.broadcast();

  Stream<PipelineState> get stateStream => _stateCtrl.stream;
  Stream<List<SessionTurn>> get turnsStream => _turnsCtrl.stream;
  Stream<String> get errorStream => _errorCtrl.stream;
  Stream<EscalationPacket?> get escalationStream => _escalationCtrl.stream;
  Stream<SessionMeta?> get sessionMetaStream => _sessionMetaCtrl.stream;
  Stream<NluResult?> get nluResultStream => _nluCtrl.stream;
  Stream<VerificationPrompt?> get verificationPromptStream =>
      _verifyPromptCtrl.stream;
  Stream<ConfidenceScore?> get confidenceStream => _confidenceCtrl.stream;
  Stream<bool?> get mockModeStream => _mockModeCtrl.stream;
  Stream<TicketInfo?> get ticketStream => _ticketCtrl.stream;

  PipelineState _currentState = PipelineState.idle;
  final List<SessionTurn> _turns = [];
  String _currentLanguage = AppConfig.defaultLanguage;
  String _currentDistrict = AppConfig.defaultDistrict;
  bool? _isMockMode;
  TicketInfo? _currentTicket;

  String get currentLanguage => _currentLanguage;
  String get currentDistrict => _currentDistrict;
  bool? get isMockMode => _isMockMode;
  TicketInfo? get currentTicket => _currentTicket;

  VoicePipelineService() {
    _stateCtrl.add(_currentState);
    _turnsCtrl.add(_turns);
  }

  void _setState(PipelineState state) {
    _currentState = state;
    _stateCtrl.add(state);
  }

  // ─── Session lifecycle ────────────────────────────────────────────────────

  Future<void> startSession({String? district, String? language}) async {
    final dist = district ?? AppConfig.defaultDistrict;
    final lang = language ?? AppConfig.defaultLanguage;
    _currentLanguage = lang;
    _currentDistrict = dist;

    _setState(PipelineState.starting);
    _turns.clear();
    _turnsCtrl.add([]);
    _escalationCtrl.add(null);
    _verifyPromptCtrl.add(null);
    _currentTicket = null;
    _ticketCtrl.add(null);

    try {
      final response = await http
          .post(Uri.parse('$backendUrl/sessions?district=$dist&language=$lang'))
          .timeout(const Duration(seconds: 8));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        sessionId = data['session_id'];
        _connectWebSocket();
        _setState(PipelineState.ready);
      } else {
        throw Exception('HTTP ${response.statusCode}');
      }
    } catch (e) {
      _errorCtrl.add('Could not connect to backend: $e');
      _setState(PipelineState.error);
    }
  }

  void _connectWebSocket() {
    if (sessionId == null) return;
    _channel?.sink.close();
    _channel = WebSocketChannel.connect(Uri.parse('$wsUrl/$sessionId'));
    _channel!.stream.listen(
      (message) {
        try {
          _handleMessage(jsonDecode(message as String));
        } catch (e) {
          print('[WS] decode error: $e');
        }
      },
      onError: (e) {
        _errorCtrl.add('WebSocket error: $e');
        _setState(PipelineState.error);
      },
      onDone: () {
        if (_currentState != PipelineState.escalated) {
          _setState(PipelineState.idle);
        }
      },
    );
  }

  // ─── Incoming message router ──────────────────────────────────────────────

  Future<void> _handleMessage(Map<String, dynamic> data) async {
    final type = data['type'];

    if (data['mock_mode'] is bool) {
      _isMockMode = data['mock_mode'] as bool;
      _mockModeCtrl.add(_isMockMode);
    }

    if (data['session'] != null) {
      _sessionMetaCtrl.add(SessionMeta.fromJson(data['session']));
    }

    switch (type) {
      case 'turn_update':
        await _handleTurnUpdate(data);
        break;

      case 'verification_prompt':
        // Backend sends this after processing audio, asking citizen to confirm
        _verifyPromptCtrl.add(VerificationPrompt.fromJson(data));
        _setState(PipelineState.verifying);
        break;

      case 'verification_result':
        // Backend confirms/clarifies after citizen taps yes/partly/no
        _verifyPromptCtrl.add(null); // dismiss verify panel
        final aiText = data['ai_response'] ?? '';
        if (aiText.isNotEmpty) {
          _addTurn(SessionTurn(speaker: 'ai', rawTranscript: aiText));
        }
        final vrAudio = data['tts_audio_b64'] as String? ?? '';
        if (vrAudio.isNotEmpty) {
          await _playAudio(vrAudio);
        } else {
          _setState(PipelineState.ready);
        }
        break;

      case 'escalation':
        _verifyPromptCtrl.add(null);
        _setState(PipelineState.escalated);
        final packet = EscalationPacket.fromJson({
          ...data['packet'] as Map<String, dynamic>,
          'escalation_message': data['escalation_message'],
        });
        _escalationCtrl.add(packet);
        final escAudio = data['tts_audio_b64'] as String? ?? '';
        if (escAudio.isNotEmpty) {
          await _playAudio(escAudio);
        }
        break;

      case 'agent_audio':
        final text = (data['text'] ?? '') as String;
        if (text.isNotEmpty) {
          _addTurn(SessionTurn(speaker: 'agent', rawTranscript: text));
        }
        if (data['tts_audio_b64'] != null &&
            (data['tts_audio_b64'] as String).isNotEmpty) {
          await _playAudio(data['tts_audio_b64'] as String);
        } else {
          _setState(PipelineState.ready);
        }
        break;

      case 'ticket_created':
        final ticket = TicketInfo.fromJson(data['ticket'] as Map<String, dynamic>);
        _currentTicket = ticket;
        _ticketCtrl.add(ticket);
        break;

      case 'pong':
        break;

      case 'error':
        _errorCtrl.add(data['message'] ?? 'Unknown error from server');
        _setState(PipelineState.error);
        break;
    }
  }

  Future<void> _handleTurnUpdate(Map<String, dynamic> data) async {
    if (data['citizen_turn'] != null) {
      _addTurn(SessionTurn.fromJson(data['citizen_turn']));
    }
    if (data['ai_turn'] != null) {
      final aiTurn = SessionTurn.fromJson(data['ai_turn']);
      _addTurn(aiTurn);
      if (data['ai_turn']['tts_audio_b64'] != null &&
          (data['ai_turn']['tts_audio_b64'] as String).isNotEmpty) {
        await _playAudio(data['ai_turn']['tts_audio_b64'] as String);
      }
    }
    if (data['nlu'] != null) {
      _nluCtrl.add(NluResult.fromJson(data['nlu']));
    }
    if (data['confidence_score'] != null) {
      _confidenceCtrl.add(ConfidenceScore.fromJson(data['confidence_score']));
    }
    // State remains as-is; verification_prompt message will follow if needed
    if (_currentState == PipelineState.processing) {
      _setState(PipelineState.ready);
    }
  }

  // ─── Audio recording ──────────────────────────────────────────────────────

  Future<void> startRecording() async {
    if (_currentState != PipelineState.ready) return;
    try {
      if (await _record.hasPermission()) {
        await _record.start(
          const RecordConfig(encoder: AudioEncoder.wav),
          path: kIsWeb ? 'audio.wav' : '/tmp/samvaad_record.wav',
        );
        _setState(PipelineState.listening);
      } else {
        _errorCtrl.add('Microphone permission denied');
      }
    } catch (e) {
      _errorCtrl.add('Recording error: $e');
      _setState(PipelineState.error);
    }
  }

  Future<void> stopRecording() async {
    if (_currentState != PipelineState.listening) return;
    _setState(PipelineState.processing);

    try {
      final path = await _record.stop();
      if (_channel == null) throw Exception('WebSocket not connected');

      String base64Audio;
      if (kIsWeb) {
        if (path != null && path.startsWith('blob:')) {
          final res = await http.get(Uri.parse(path));
          if (res.statusCode != 200) throw Exception('Blob fetch failed');
          base64Audio = base64Encode(res.bodyBytes);
        } else if (path != null) {
          base64Audio = path;
        } else {
          throw Exception('No audio data');
        }
      } else {
        if (path == null) throw Exception('No audio path');
        base64Audio = base64Encode(await File(path).readAsBytes());
      }

      _channel!.sink.add(jsonEncode({
        'type': 'audio',
        'data': base64Audio,
        'language': _currentLanguage,
        'district': _currentDistrict,
      }));
    } catch (e) {
      _errorCtrl.add('Failed to send audio: $e');
      _setState(PipelineState.error);
    }
  }

  // ─── Verification response ────────────────────────────────────────────────

  /// state: "correct" | "partial" | "incorrect"
  void sendVerificationResponse(String state, {String? correctionText}) {
    if (_channel == null) return;
    _setState(PipelineState.processing);
    final payload = <String, dynamic>{
      'type': 'verification_response',
      'state': state,
    };
    if (correctionText != null) payload['correction_text'] = correctionText;
    _channel!.sink.add(jsonEncode(payload));
  }

  // ─── Agent correction ─────────────────────────────────────────────────────

  Future<void> sendAgentCorrection({
    required String field,
    required String value,
    String agentId = 'agent-001',
  }) async {
    if (sessionId == null) return;
    await http.post(
      Uri.parse('$backendUrl/sessions/$sessionId/agent-correction'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'field': field, 'value': value, 'agent_id': agentId}),
    );
  }

  // ─── Session management ───────────────────────────────────────────────────

  void endSession() {
    _channel?.sink.close();
    _channel = null;
    sessionId = null;
    _turns.clear();
    _turnsCtrl.add([]);
    _escalationCtrl.add(null);
    _verifyPromptCtrl.add(null);
    _confidenceCtrl.add(null);
    _mockModeCtrl.add(null);
    _isMockMode = null;
    _currentTicket = null;
    _ticketCtrl.add(null);
    _setState(PipelineState.idle);
  }

  /// End the call but keep turns in memory for transcript display.
  /// Fetches a ticket from the backend if one hasn't been created via WS yet.
  Future<void> endCall() async {
    final sid = sessionId;
    _channel?.sink.close();
    _channel = null;
    sessionId = null;
    _verifyPromptCtrl.add(null);
    _setState(PipelineState.idle);

    if (sid != null && _turns.isNotEmpty && _currentTicket == null) {
      try {
        final res = await http
            .get(Uri.parse('$backendUrl/sessions/$sid/ticket'))
            .timeout(const Duration(seconds: 5));
        if (res.statusCode == 200) {
          final ticket = TicketInfo.fromJson(
              jsonDecode(res.body) as Map<String, dynamic>);
          _currentTicket = ticket;
          _ticketCtrl.add(ticket);
        }
      } catch (_) {}
    }
  }

  // ─── Helpers ──────────────────────────────────────────────────────────────

  void _addTurn(SessionTurn turn) {
    _turns.add(turn);
    _turnsCtrl.add(List.from(_turns));
  }

  /// Adds a local agent turn immediately (used for live shared-session UI sync).
  void addLocalAgentTurn(String text) {
    final trimmed = text.trim();
    if (trimmed.isEmpty) return;
    _addTurn(SessionTurn(speaker: 'agent', rawTranscript: trimmed));
  }

  Future<void> _playAudio(String b64) async {
    if (b64.isEmpty) {
      if (_currentState == PipelineState.speaking) _setState(PipelineState.ready);
      return;
    }
    _setState(PipelineState.speaking);
    try {
      final bytes = base64Decode(b64);
      // Skip playback for stub audio (≤ 100 bytes = mock silent WAV)
      if (bytes.length > 100) {
        await _audioPlayer.play(BytesSource(bytes));
        await _audioPlayer.onPlayerComplete.first
            .timeout(const Duration(seconds: 30), onTimeout: () {});
      }
    } catch (_) {}
    if (_currentState == PipelineState.speaking) _setState(PipelineState.ready);
  }

  void dispose() {
    _channel?.sink.close();
    _record.dispose();
    _audioPlayer.dispose();
    _stateCtrl.close();
    _turnsCtrl.close();
    _errorCtrl.close();
    _escalationCtrl.close();
    _sessionMetaCtrl.close();
    _nluCtrl.close();
    _verifyPromptCtrl.close();
    _confidenceCtrl.close();
    _mockModeCtrl.close();
    _ticketCtrl.close();
  }
}
