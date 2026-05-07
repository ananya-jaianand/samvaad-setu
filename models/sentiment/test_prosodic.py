import argparse
import sys
import json
import os
import wave
import math
import struct

from .prosodic_features import ProsodicSentimentExtractor

def create_dummy_wav(filename):
    """Creates a 1-second 440Hz sine wave for testing if no audio is provided."""
    print(f"Generating dummy test audio: {filename}")
    sample_rate = 16000
    duration = 1.0
    frequency = 440.0
    
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        
        for i in range(int(sample_rate * duration)):
            value = int(32767.0 * math.sin(2.0 * math.pi * frequency * i / sample_rate))
            data = struct.pack('<h', value)
            wav_file.writeframesraw(data)

def main():
    parser = argparse.ArgumentParser(description="Test the Prosodic Feature Extractor")
    parser.add_argument("--audio", type=str, help="Path to WAV file to analyze")
    args = parser.parse_args()

    # Use provided file or create a dummy one
    audio_path = args.audio
    if not audio_path:
        audio_path = "test_audio.wav"
        create_dummy_wav(audio_path)
    
    if not os.path.exists(audio_path):
        print(f"Error: File {audio_path} not found.")
        sys.exit(1)

    print("Initializing prosodic extractor...")
    try:
        extractor = ProsodicSentimentExtractor()
    except Exception as e:
        print(f"Failed to initialize extractor: {e}")
        sys.exit(1)

    print(f"\nAnalyzing audio: '{audio_path}'")
    result = extractor.analyze(audio_path)

    print("\n--- RESULTS ---")
    print(f"Dominant Emotion: {result['dominant_label'].upper()} (Confidence: {result['dominant_score']})")
    print(f"Latency: {result['latency_ms']} ms")
    
    print("\nAll Scores:")
    for label, score in result['all_scores'].items():
        print(f"  - {label}: {score}")

    print("\nJSON Output:")
    print(json.dumps(result, indent=2))
    
    # Cleanup dummy file if we created it
    if not args.audio and os.path.exists(audio_path):
        os.remove(audio_path)

if __name__ == "__main__":
    main()
