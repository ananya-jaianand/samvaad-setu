
"""
Test script for Verification Machine logic
Demonstrates the session-state-based verification flow
"""

import sys
sys.path.append('.')

from agent import is_affirmation, is_denial_or_correction

def test_affirmations():
    """Test affirmation detection across multiple languages"""
    print("="*70)
    print("TESTING AFFIRMATION DETECTION")
    print("="*70)

    test_cases = [
        # English
        ("yes", True),
        ("Yeah, that's right", True),
        ("Correct", True),
        ("Okay", True),

        # Kannada
        ("ಹೌದು", True),
        ("sari", True),
        ("Sari ide", True),
        ("aaythu", True),

        # Hindi
        ("haan", True),
        ("सही", True),
        ("theek hai", True),

        # Tamil
        ("aam", True),

        # Negatives (should be False)
        ("no", False),
        ("not really", False),
        ("nahi", False),
        ("illa", False),
    ]

    passed = 0
    failed = 0

    for text, expected in test_cases:
        result = is_affirmation(text)
        status = "✅" if result == expected else "❌"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"{status} '{text}' → {result} (expected {expected})")

    print(f"\n📊 Results: {passed} passed, {failed} failed out of {len(test_cases)}")
    return failed == 0


def test_denials():
    """Test denial and correction detection"""
    print("\n" + "="*70)
    print("TESTING DENIAL/CORRECTION DETECTION")
    print("="*70)

    test_cases = [
        # English denials
        ("no", True),
        ("nope, that's wrong", True),
        ("Not correct", True),
        ("Actually, it's different", True),

        # Kannada denials
        ("ಇಲ್ಲ", True),
        ("illa", True),
        ("beda", True),
        ("aagolla", True),

        # Hindi denials
        ("nahi", True),
        ("नहीं", True),
        ("galat", True),

        # Long corrections (>10 words)
        ("No, actually the problem is not in Indiranagar but in Jayanagar area near the park", True),

        # Affirmations (should be False)
        ("yes", False),
        ("correct", False),
        ("sari", False),

        # Short neutral responses (should be False)
        ("okay", False),
        ("hmm", False),
    ]

    passed = 0
    failed = 0

    for text, expected in test_cases:
        result = is_denial_or_correction(text)
        status = "✅" if result == expected else "❌"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"{status} '{text[:50]}...' → {result} (expected {expected})")

    print(f"\n📊 Results: {passed} passed, {failed} failed out of {len(test_cases)}")
    return failed == 0


def simulate_verification_flow():
    """Simulate the complete verification flow"""
    print("\n" + "="*70)
    print("SIMULATING VERIFICATION FLOW")
    print("="*70)

    # Scenario 1: Happy Path
    print("\n📋 Scenario 1: User Affirms")
    print("-" * 70)

    session_state = {
        'verified': False,
        'waiting_for_verification': True,
        'current_intent': 'Water Supply',
        'current_urgency': 7
    }

    print(f"Initial state: {session_state}")
    print("Agent: 'I understand you have no water supply in your area, is that correct?'")

    user_response = "Yes"
    print(f"User: '{user_response}'")

    if is_affirmation(user_response):
        session_state['verified'] = True
        session_state['waiting_for_verification'] = False
        print("✅ TICKET REGISTERED")

    print(f"Final state: {session_state}")

    # Scenario 2: User Corrects
    print("\n📋 Scenario 2: User Provides Correction")
    print("-" * 70)

    session_state = {
        'verified': False,
        'waiting_for_verification': True,
        'current_intent': 'Water Supply',
        'current_urgency': 6
    }

    print(f"Initial state: {session_state}")
    print("Agent: 'I understand you have a water supply issue, is that correct?'")

    user_response = "No, actually it's not water supply, it's drainage blockage"
    print(f"User: '{user_response}'")

    if is_denial_or_correction(user_response):
        session_state['waiting_for_verification'] = False
        print("🔄 SENDING CORRECTION BACK TO LLM")
        print(f"Correction text: '{user_response}'")

    print(f"Final state: {session_state}")

    # Scenario 3: Urgent Escalation
    print("\n📋 Scenario 3: Urgent Escalation (urgency > 8)")
    print("-" * 70)

    session_state = {
        'verified': False,
        'waiting_for_verification': False,
        'current_intent': 'Sanitation/Waste',
        'current_urgency': 9
    }

    print(f"Initial state: {session_state}")
    print("LLM detected urgency_score: 9")

    if session_state['current_urgency'] > 8:
        print("🚨 URGENT - BYPASSING VERIFICATION")
        print("Agent: 'This sounds urgent. Connecting you to a human supervisor...'")
        session_state['verified'] = True

    print(f"Final state: {session_state}")

    # Scenario 4: Multilingual Affirmation
    print("\n📋 Scenario 4: Multilingual Affirmation")
    print("-" * 70)

    session_state = {
        'verified': False,
        'waiting_for_verification': True,
        'current_intent': 'Aadhaar Services',
        'current_urgency': 5
    }

    print(f"Initial state: {session_state}")
    print("Agent: 'Nimge Aadhaar update beku, sari na?'")

    user_response = "ಹೌದು"  # Kannada "yes"
    print(f"User: '{user_response}' (Kannada: 'yes')")

    if is_affirmation(user_response):
        session_state['verified'] = True
        session_state['waiting_for_verification'] = False
        print("✅ TICKET REGISTERED (Kannada affirmation detected)")

    print(f"Final state: {session_state}")


def main():
    print("\n" + "="*70)
    print("VERIFICATION MACHINE TEST SUITE")
    print("="*70)

    results = []

    # Run tests
    results.append(("Affirmation Detection", test_affirmations()))
    results.append(("Denial/Correction Detection", test_denials()))

    # Run simulation
    simulate_verification_flow()

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
        if not passed:
            all_passed = False

    print("="*70)

    if all_passed:
        print("\n🎉 All tests passed! Verification Machine is working correctly.")
        return 0
    else:
        print("\n⚠️ Some tests failed. Please review the implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
