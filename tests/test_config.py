"""
Test script for Samvaad-Setu Agent Configuration
Verifies that all components can be imported and initialized
"""

import sys
from dotenv import load_dotenv
import os

def test_imports():
    """Test that all required modules can be imported"""
    print("Testing imports...")
    try:
        from livekit import agents
        print("✓ livekit.agents imported successfully")

        from livekit.plugins import sarvam
        print("✓ livekit.plugins.sarvam imported successfully")

        from livekit.plugins import anthropic
        print("✓ livekit.plugins.anthropic imported successfully")

        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False


def test_environment():
    """Test that environment variables are configured"""
    print("\nTesting environment configuration...")
    load_dotenv()

    required_vars = [
        "SARVAM_API_KEY",
        "ANTHROPIC_API_KEY",
        "LIVEKIT_URL",
        "LIVEKIT_API_KEY",
        "LIVEKIT_API_SECRET"
    ]

    all_set = True
    for var in required_vars:
        value = os.getenv(var)
        if not value or value in ["your_key_here", "..."]:
            print(f"✗ {var} is not properly configured")
            all_set = False
        else:
            # Show partial value for security
            masked_value = value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
            print(f"✓ {var} is set ({masked_value})")

    return all_set


def test_agent_config():
    """Test that agent configuration can be loaded"""
    print("\nTesting agent configuration...")
    try:
        from agent import GRIEVANCE_TAXONOMY, get_system_prompt

        print(f"✓ Grievance taxonomy loaded with {len(GRIEVANCE_TAXONOMY)} categories:")
        for i, category in enumerate(GRIEVANCE_TAXONOMY, 1):
            print(f"  {i}. {category}")

        prompt = get_system_prompt()
        print(f"✓ System prompt generated ({len(prompt)} characters)")

        return True
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False


def main():
    print("="*60)
    print("Samvaad-Setu Agent Configuration Test")
    print("="*60)

    results = []

    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("Environment", test_environment()))
    results.append(("Agent Config", test_agent_config()))

    # Summary
    print("\n" + "="*60)
    print("Test Summary:")
    print("="*60)

    all_passed = True
    for test_name, passed in results:
        status = "PASS" if passed else "FAIL"
        symbol = "✓" if passed else "✗"
        print(f"{symbol} {test_name}: {status}")
        if not passed:
            all_passed = False

    print("="*60)

    if all_passed:
        print("\n✓ All tests passed! Your agent is ready to run.")
        print("\nTo start the agent, run:")
        print("  python agent.py dev")
        return 0
    else:
        print("\n✗ Some tests failed. Please fix the issues above.")
        print("\nMake sure to:")
        print("  1. Update .env file with your API keys")
        print("  2. Install all dependencies")
        return 1


if __name__ == "__main__":
    sys.exit(main())
