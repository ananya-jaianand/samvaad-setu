import argparse
import sys
import json
from .ambiguity_detector import SemanticAmbiguityDetector

def main():
    parser = argparse.ArgumentParser(description="Test the Semantic Ambiguity Detector")
    parser.add_argument("--text", type=str, help="Text transcript to analyze")
    args = parser.parse_args()

    # If no text provided, we test both an unambiguous and an ambiguous statement
    test_cases = []
    if args.text:
        test_cases.append(args.text)
    else:
        test_cases.extend([
            "My property tax is showing pending but I paid it.", # Unambiguous
            "Neeru bartilla", # Ambiguous (Water supply vs Sanitation)
            "The street light is broken", # Unambiguous
            "Current illa rasta alli", # Ambiguous (Current + Road)
        ])

    print("Initializing Ambiguity Detector...")
    try:
        detector = SemanticAmbiguityDetector()
    except Exception as e:
        print(f"Failed to initialize detector: {e}")
        sys.exit(1)

    for text in test_cases:
        print(f"\n{'='*50}")
        print(f"Analyzing transcript: '{text}'")
        print(f"{'='*50}")
        
        result = detector.analyze(text)
        
        print(f"Top Intent: {result['top_intent'].upper()} (Confidence: {result['top_intent_confidence']})")
        print(f"Secondary Intent: {result['secondary_intent'].upper()}")
        
        print(f"\n>> AMBIGUITY SCORE: {result['ambiguity_score']}")
        print(f">> REQUIRES CLARIFICATION: {'YES' if result['requires_clarification'] else 'NO'}")
        
        print("\nReasons:")
        print(f"  - Base Entropy: {result['reasons']['base_entropy']}")
        print(f"  - Margin Penalty: {result['reasons']['margin_penalty']}")
        if result['reasons']['keywords_flagged']:
            print(f"  - Flagged Keywords: {result['reasons']['keywords_flagged']}")
            print(f"  - Conflicting Intents: {result['reasons']['conflicting_intents']}")
            
        print(f"\nLatency: {result['latency_ms']} ms")

if __name__ == "__main__":
    main()
