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

enum PipelineState { idle, starting, ready, listening, processing, speaking, escalated, error }

class VoicePipelineService {
  final String backendUrl = AppConfig.backendUrl;
  final String wsUrl = AppConfig.wsUrl;

  String? sessionId;
  WebSocketChannel? _channel;
  final AudioRecorder _record = AudioRecorder();
  final AudioPlayer _audioPlayer = AudioPlayer();
  Timer? _callTimer;
  int _callSeconds = 0;

  // Streams
  final _stateController = StreamController<PipelineState>.broadcast();
  final _turnsController = StreamController<List<SessionTurn>>.broadcast();
  final _errorController = StreamController<String>.broadcast();
  final _escalationController = StreamController<EscalationPacket?>.broadcast();
  final _sessionMetaController = StreamController<SessionMeta?>.broadcast();
  final _nluResultController = StreamController<NluResult?>.broadcast();

  Stream<PipelineState> get stateStream => _stateController.stream;
  Stream<List<SessionTurn>> get turnsStream => _turnsController.stream;
  Stream<String> get errorStream => _errorController.stream;
  Stream<EscalationPacket?> get escalationStream => _escalationController.stream;
  Stream<SessionMeta?> get sessionMetaStream => _sessionMetaController.stream;
  Stream<NluResult?> get nluResultStream => _nluResultController.stream;

  PipelineState _currentState = PipelineState.idle;
  final List<SessionTurn> _turns = [];
  SessionMeta? _currentMeta;

  VoicePipelineService() {
    _stateController.add(_currentState);
    _turnsController.add(_turns);
  }

  void _setState(PipelineState state) {
    _currentState = state;
    _stateController.add(state);
  }

  void _startCallTimer() {
    _callSeconds = 0;
    _callTimer?.cancel();
    _callTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      _callSeconds++;
      final mins = (_callSeconds ~/ 60).toString().padLeft(2, '0');
      final secs = (_callSeconds % 60).toString().padLeft(2, '0');
      _currentMeta = SessionMeta(
        compositeConfidence: _currentMeta?.compositeConfidence ?? 0.88,
        clarificationCount: _currentMeta?.clarificationCount ?? 0,
        sentimentTimeline: _currentMeta?.sentimentTimeline ?? [],
        currentLanguage: _currentMeta?.currentLanguage,
        currentDialect: _currentMeta?.currentDialect,
        currentSentiment: _currentMeta?.currentSentiment,
        callId: _currentMeta?.callId ?? 'IN-8472',
        callDuration: '$mins:$secs',
      );
      _sessionMetaController.add(_currentMeta);
    });
  }

  Future<void> startSession({
    String? district,
    String? language,
  }) async {
    final dist = district ?? AppConfig.defaultDistrict;
    final lang = language ?? AppConfig.defaultLanguage;

    try {
      _setState(PipelineState.starting);

      // Create session with backend
      final response = await http
          .post(Uri.parse('$backendUrl/sessions?district=$dist&language=$lang'))
          .timeout(const Duration(seconds: 5));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        sessionId = data['session_id'];
        print('Session created: $sessionId');
        _connectWebSocket();
        _startCallTimer();
        _setState(PipelineState.ready);
      } else {
        throw Exception('Failed to create session: ${response.statusCode}');
      }
    } catch (e) {
      _errorController.add('Could not start session: $e');
      _setState(PipelineState.error);
      print('Session creation error: $e');
    }
  }

  void _connectWebSocket() {
    if (sessionId == null) return;
    print('[WS] Connecting to: $wsUrl/$sessionId');
    _channel = WebSocketChannel.connect(Uri.parse('$wsUrl/$sessionId'));
    _channel!.stream.listen(
      (message) {
        print('[WS] Received message: ${message.toString().substring(0, message.toString().length > 200 ? 200 : message.toString().length)}...');
        try {
          _handleWsMessage(jsonDecode(message));
        } catch (e) {
          print('[WS] Error decoding message: $e');
          print('[WS] Raw message: $message');
        }
      },
      onError: (e) {
        print('[WS] WebSocket error: $e');
        _errorController.add('WebSocket Error: $e');
        _setState(PipelineState.error);
      },
      onDone: () {
        print('[WS] WebSocket connection closed');
        if (_currentState != PipelineState.escalated) _setState(PipelineState.idle);
      },
    );
    print('[WS] WebSocket connected');
  }

  Future<void> _handleWsMessage(Map<String, dynamic> data) async {
    final type = data['type'];
    print('[WS] Handling message type: $type');
    if (data['session'] != null) {
      _currentMeta = SessionMeta.fromJson(data['session']);
      _sessionMetaController.add(_currentMeta);
    }
    if (data['nlu'] != null) {
      _nluResultController.add(NluResult.fromJson(data['nlu']));
    }
    if (type == 'turn_update') {
      print('[WS] Processing turn_update');
      if (data['citizen_turn'] != null) {
        print('[WS] Adding citizen turn');
        _addTurn(SessionTurn.fromJson(data['citizen_turn']));
      }
      if (data['ai_turn'] != null) {
        print('[WS] Adding AI turn');
        final aiTurn = SessionTurn.fromJson(data['ai_turn']);
        _addTurn(aiTurn);
        if (data['ai_turn']['tts_audio_b64'] != null) {
          print('[WS] Playing TTS audio');
          await _playAudioB64(data['ai_turn']['tts_audio_b64']);
        }
      }
      print('[WS] Turn update complete, setting state to ready');
      _setState(PipelineState.ready);
    } else if (type == 'verification_result') {
      // Handle verification response from backend
      final aiResponse = data['ai_response'] ?? '';
      final state = data['state'] ?? '';
      
      // Add AI response as a turn
      if (aiResponse.isNotEmpty) {
        final aiTurn = SessionTurn(
          speaker: 'ai',
          rawTranscript: aiResponse,
          detectedLanguage: _currentMeta?.currentLanguage,
        );
        _addTurn(aiTurn);
      }
      
      // Play TTS audio if available
      if (data['tts_audio_b64'] != null) {
        await _playAudioB64(data['tts_audio_b64']);
      }
      
      // Update clarification count if provided
      if (data['clarification_count'] != null && _currentMeta != null) {
        _currentMeta = SessionMeta(
          compositeConfidence: _currentMeta!.compositeConfidence,
          clarificationCount: data['clarification_count'],
          sentimentTimeline: _currentMeta!.sentimentTimeline,
          currentLanguage: _currentMeta!.currentLanguage,
          currentDialect: _currentMeta!.currentDialect,
          currentSentiment: _currentMeta!.currentSentiment,
          callId: _currentMeta!.callId,
          callDuration: _currentMeta!.callDuration,
        );
        _sessionMetaController.add(_currentMeta);
      }
      
      _setState(PipelineState.ready);
      print('Verification result: $state - $aiResponse');
    } else if (type == 'escalation') {
      print('[WS] Processing escalation');
      _setState(PipelineState.escalated);
      final packet = EscalationPacket.fromJson(data['packet']);
      _escalationController.add(packet);
      print('[WS] Escalation packet added');
      _nluResultController.add(NluResult(
        intentConfidence: 0.93,
        aiSummary: packet.summary,
        intent: packet.reason,
      ));
      if (data['tts_audio_b64'] != null) await _playAudioB64(data['tts_audio_b64']);
    } else if (type == 'error') {
      _errorController.add(data['message'] ?? 'Unknown error');
      _setState(PipelineState.error);
    }
  }

  void _addTurn(SessionTurn turn) {
    _turns.add(turn);
    _turnsController.add(List.from(_turns));
  }

  /// Send verification response (correct/partial/incorrect) to backend
  void sendVerification(String response) {
    if (_channel == null) {
      print('WebSocket not connected, cannot send verification');
      return;
    }

    try {
      _setState(PipelineState.processing);
      _channel!.sink.add(jsonEncode({
        'type': 'verification',
        'data': response,
      }));
      print('Sent verification: $response');
    } catch (e) {
      _errorController.add('Failed to send verification: $e');
    }
  }

  Future<void> _playAudioB64(String b64) async {
    _setState(PipelineState.speaking);
    final bytes = base64Decode(b64);
    await _audioPlayer.play(BytesSource(bytes));
    await _audioPlayer.onPlayerComplete.first;
    if (_currentState == PipelineState.speaking) _setState(PipelineState.ready);
  }

  Future<void> startRecording() async {
    if (_currentState != PipelineState.ready) return;
    try {
      // Check and request permission
      if (await _record.hasPermission()) {
        // Start recording (path is ignored on web)
        await _record.start(
          const RecordConfig(encoder: AudioEncoder.wav),
          path: kIsWeb ? 'audio.wav' : '/tmp/samvaad_record.wav',
        );
        _setState(PipelineState.listening);
        print('Recording started');
      } else {
        throw Exception('Microphone permission denied');
      }
    } catch (e) {
      _errorController.add('Recording error: $e');
      _setState(PipelineState.error);
      print('Recording error: $e');
    }
  }

  Future<void> stopRecording() async {
    if (_currentState != PipelineState.listening) return;
    _setState(PipelineState.processing);
    
    try {
      // Stop recording and get audio data
      final path = await _record.stop();
      print('Recording stopped, path: $path');

      // Send audio to backend via WebSocket
      if (_channel == null) {
        throw Exception('WebSocket not connected');
      }

      String base64Audio;
      
      if (kIsWeb) {
        // On web, path is a blob URL - need to fetch and convert to base64
        if (path != null && path.startsWith('blob:')) {
          print('Fetching blob from: $path');
          final response = await http.get(Uri.parse(path));
          if (response.statusCode == 200) {
            base64Audio = base64Encode(response.bodyBytes);
            print('Converted blob to base64, length: ${base64Audio.length}');
          } else {
            throw Exception('Failed to fetch blob: ${response.statusCode}');
          }
        } else if (path != null && !path.startsWith('blob:')) {
          // Already base64
          base64Audio = path;
        } else {
          throw Exception('No audio data received from recorder');
        }
      } else {
        // On mobile/desktop, read from file
        if (path != null) {
          final file = File(path);
          final bytes = await file.readAsBytes();
          base64Audio = base64Encode(bytes);
        } else {
          throw Exception('No audio file path received');
        }
      }
      
      _channel!.sink.add(jsonEncode({
        'type': 'audio',
        'data': base64Audio,
        'language': _currentMeta?.currentLanguage?.toLowerCase() ?? 'kn',
        'district': AppConfig.defaultDistrict,
      }));
      
      print('Sent audio to backend via WebSocket');
      // Backend will respond via WebSocket, handled in _handleWsMessage
    } catch (e) {
      _errorController.add('Failed to send audio: $e');
      _setState(PipelineState.error);
      print('Stop recording error: $e');
    }
  }


  void endSession() {
    _callTimer?.cancel();
    _channel?.sink.close();
    _channel = null;
    sessionId = null;
    _turns.clear();
    _turnsController.add([]);
    _escalationController.add(null);
    _sessionMetaController.add(null);
    _nluResultController.add(null);
    _setState(PipelineState.idle);
  }

  void dispose() {
    _callTimer?.cancel();
    _channel?.sink.close();
    _record.dispose();
    _audioPlayer.dispose();
    _stateController.close();
    _turnsController.close();
    _errorController.close();
    _escalationController.close();
    _sessionMetaController.close();
    _nluResultController.close();
  }
}
