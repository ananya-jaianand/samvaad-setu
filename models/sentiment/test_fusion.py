import argparse
import sys
import json
import os
import wave
import math
import struct

from .fusion import SentimentFusionModel

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
    parser = argparse.ArgumentParser(description="Test the Sentiment Fusion Model")
    parser.add_argument("--text", type=str, required=True, help="Text transcript to analyze")
    parser.add_argument("--audio", type=str, help="Path to WAV file to analyze (optional)")
    args = parser.parse_args()

    # Use provided file or create a dummy one if we want to test fusion
    audio_path = args.audio
    if not audio_path:
        audio_path = "fusion_test_audio.wav"
        create_dummy_wav(audio_path)
    
    if not os.path.exists(audio_path):
        print(f"Error: File {audio_path} not found.")
        sys.exit(1)

    print("Initializing Fusion Model...")
    try:
        fusion_model = SentimentFusionModel(text_weight=0.65, prosodic_weight=0.35)
    except Exception as e:
        print(f"Failed to initialize fusion model: {e}")
        sys.exit(1)

    print(f"\nAnalyzing text: '{args.text}'")
    print(f"Analyzing audio: '{audio_path}'")
    
    result = fusion_model.analyze(args.text, audio_path)

    print("\n--- RESULTS ---")
    print(f"Dominant Fused Emotion: {result['dominant_label'].upper()} (Confidence: {result['dominant_score']})")
    print(f"High Distress Flag: {'YES' if result['is_high_distress'] else 'NO'} (Aggregate: {result['distress_aggregate']})")
    print(f"Latency: {result['latency_ms']} ms")
    
    print("\nFused Scores:")
    for label, score in result['all_scores'].items():
        print(f"  - {label}: {score}")

    print("\nJSON Output:")
    print(json.dumps(result, indent=2))
    
    # Cleanup dummy file if we created it
    if not args.audio and os.path.exists(audio_path):
        os.remove(audio_path)

if __name__ == "__main__":
    main()
