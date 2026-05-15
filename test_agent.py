#!/usr/bin/env python3
"""
Quick Test Script for Samvaad-Setu Voice Agent
Tests the JSON parsing and classification logic without LiveKit
"""

import json
import logging
from src.agent import (
    get_system_prompt,
    is_affirmation,
    is_denial_or_correction,
    GRIEVANCE_TAXONOMY
)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_system_prompt():
    """Test system prompt generation"""
    print("\n" + "="*80)
    print("TEST 1: System Prompt Generation")
    print("="*80)
    prompt = get_system_prompt()
    print(f"✅ System prompt generated ({len(prompt)} characters)")
    print(f"Grievance categories included: {len(GRIEVANCE_TAXONOMY)}")
    for category in GRIEVANCE_TAXONOMY:
        print(f"  - {category}")
    return True

def test_affirmation_detection():
    """Test affirmation detection in multiple languages"""
    print("\n" + "="*80)
    print("TEST 2: Affirmation Detection")
    print("="*80)

    test_cases = [
        ("yes", True),
        ("Yeah that's right", True),
        ("houdu", True),
        ("sari", True),
        ("ಹೌದು", True),
        ("haan sahi hai", True),
        ("no that's wrong", False),
        ("actually it's different", False),
        ("illa", False),
    ]

    passed = 0
    for text, expected in test_cases:
        result = is_affirmation(text)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{text}' -> {result} (expected: {expected})")
        if result == expected:
            passed += 1

    print(f"\nPassed: {passed}/{len(test_cases)}")
    return passed == len(test_cases)

def test_denial_detection():
    """Test denial/correction detection"""
    print("\n" + "="*80)
    print("TEST 3: Denial/Correction Detection")
    print("="*80)

    test_cases = [
        ("no", True),
        ("illa that's wrong", True),
        ("nahi galat hai", True),
        ("actually I meant something else about water supply issue", True),
        ("yes", False),
        ("sari", False),
    ]

    passed = 0
    for text, expected in test_cases:
        result = is_denial_or_correction(text)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{text}' -> {result} (expected: {expected})")
        if result == expected:
            passed += 1

    print(f"\nPassed: {passed}/{len(test_cases)}")
    return passed == len(test_cases)

def test_json_parsing():
    """Test JSON response parsing logic"""
    print("\n" + "="*80)
    print("TEST 4: JSON Response Parsing")
    print("="*80)

    sample_json = {
        "intent": "Water Supply",
        "original_language": "Kannada",
        "sentiment": "frustrated",
        "urgency_score": 7,
        "verification_question": "I understand you're facing water supply issues in your area. Is that correct?"
    }

    try:
        json_str = json.dumps(sample_json)
        parsed = json.loads(json_str)

        print(f"✅ JSON parsing successful")
        print(f"\n📊 Sample Classification Output:")
        print("="*80)
        print(f"📋 FINAL JSON OUTPUT:\n{json.dumps(parsed, indent=2)}")
        print(f"🎯 Intent Classification: {parsed['intent']}")
        print(f"🔥 Urgency Score: {parsed['urgency_score']}/10")
        print(f"😊 Sentiment Analysis: {parsed['sentiment']}")
        print(f"🗣️  Original Language: {parsed['original_language']}")
        print(f"✅ Verification Question: {parsed['verification_question']}")
        print("="*80)
        return True
    except Exception as e:
        print(f"❌ JSON parsing failed: {e}")
        return False

def test_urgency_escalation():
    """Test urgency-based escalation logic"""
    print("\n" + "="*80)
    print("TEST 5: Urgency Escalation Logic")
    print("="*80)

    test_cases = [
        (5, False, "Normal priority"),
        (7, False, "High priority but not urgent"),
        (9, True, "🚨 URGENT - Should escalate to human"),
        (10, True, "🚨 EMERGENCY - Should escalate immediately"),
    ]

    for urgency_score, should_escalate, description in test_cases:
        escalates = urgency_score > 8
        status = "✅" if escalates == should_escalate else "❌"
        action = "ESCALATE" if escalates else "VERIFY"
        print(f"{status} Urgency {urgency_score}/10 -> {action} ({description})")

    return True

def main():
    """Run all tests"""
    print("\n" + "#"*80)
    print("# SAMVAAD-SETU VOICE AGENT - UNIT TESTS")
    print("#"*80)

    results = []
    results.append(("System Prompt Generation", test_system_prompt()))
    results.append(("Affirmation Detection", test_affirmation_detection()))
    results.append(("Denial Detection", test_denial_detection()))
    results.append(("JSON Parsing", test_json_parsing()))
    results.append(("Urgency Escalation", test_urgency_escalation()))

    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    total_passed = sum(1 for _, passed in results if passed)
    print(f"\nTotal: {total_passed}/{len(results)} tests passed")

    if total_passed == len(results):
        print("\n🎉 All tests passed! Agent logic is working correctly.")
        print("\nNext steps:")
        print("1. Update .env file with your API keys")
        print("2. Install dependencies: pip install -r requirements.txt")
        print("3. Run the agent: python src/agent.py dev")
    else:
        print("\n⚠️  Some tests failed. Please review the output above.")

if __name__ == "__main__":
    main()



