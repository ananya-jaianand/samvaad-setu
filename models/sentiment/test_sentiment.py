import argparse
import sys
import json
from .text_sentiment import TextSentimentClassifier

def main():
    parser = argparse.ArgumentParser(description="Test the Zero-shot Multilingual Sentiment Classifier")
    parser.add_argument("--text", type=str, required=True, help="Text transcript to analyze")
    args = parser.parse_args()

    print("Initializing classifier...")
    try:
        classifier = TextSentimentClassifier()
    except Exception as e:
        print(f"Failed to initialize classifier: {e}")
        sys.exit(1)

    print(f"\nAnalyzing text: '{args.text}'")
    result = classifier.analyze(args.text)

    print("\n--- RESULTS ---")
    print(f"Dominant Emotion: {result['dominant_label'].upper()} (Confidence: {result['dominant_score']})")
    print(f"Latency: {result['latency_ms']} ms")
    
    print("\nAll Scores:")
    for label, score in result['all_scores'].items():
        print(f"  - {label}: {score}")

    print("\nJSON Output:")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
