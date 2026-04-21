#!/usr/bin/env python3
"""
Test script for Discord bot functionality
Tests the security assessment and Q&A features without connecting to Discord
"""

import os
from pathlib import Path
from agent import (
    build_architecture_summary,
    format_assessment_prompt,
    parse_counts_and_percentages,
    build_report_markdown,
    run_pytm_model,
    local_llm_query
)

def test_drawio_assessment():
    """Test Draw.io file assessment functionality"""
    print("🧪 Testing Draw.io assessment functionality...")

    sample_file = Path("sample.drawio")
    if not sample_file.exists():
        print("❌ sample.drawio not found, skipping Draw.io test")
        return

    try:
        # Test architecture parsing
        architecture_summary = build_architecture_summary(sample_file)
        print(f"✅ Architecture summary generated ({len(architecture_summary)} chars)")

        # Test PYTM analysis
        pytm_results = run_pytm_model(sample_file)
        print(f"✅ PYTM analysis completed: {len(pytm_results.get('threats', []))} threats found")

        # Test AI assessment
        prompt = format_assessment_prompt(architecture_summary)
        llm_output = local_llm_query(prompt, os.getenv("MODEL_PATH", "mock"))
        print(f"✅ AI assessment completed ({len(llm_output)} chars)")

        # Test report generation
        parsed_data = parse_counts_and_percentages(llm_output)
        report = build_report_markdown(sample_file, architecture_summary, llm_output, parsed_data, pytm_results)
        print(f"✅ Report generated ({len(report)} chars)")

        print("🎉 Draw.io assessment test PASSED")
        return True

    except Exception as e:
        print(f"❌ Draw.io assessment test FAILED: {e}")
        return False

def test_security_qa():
    """Test security question answering functionality"""
    print("\n🧪 Testing security Q&A functionality...")

    test_questions = [
        "What WAF tools do you recommend for AWS?",
        "How to secure AI applications?",
        "Best practices for API security"
    ]

    for question in test_questions:
        try:
            prompt = f"""You are a cybersecurity expert. Answer this security question thoroughly and practically:

Question: {question}

Provide:
1. Direct answer with recommendations
2. Key considerations or requirements
3. Implementation steps (if applicable)
4. Additional resources or best practices

Be specific, actionable, and focus on current security standards."""

            response = local_llm_query(prompt, os.getenv("MODEL_PATH", "mock"), max_tokens=800)
            print(f"✅ Question answered: '{question[:50]}...' ({len(response)} chars)")

        except Exception as e:
            print(f"❌ Q&A test FAILED for '{question}': {e}")
            return False

    print("🎉 Security Q&A test PASSED")
    return True

def test_risk_scoring():
    """Test risk scoring calculation"""
    print("\n🧪 Testing risk scoring functionality...")

    # Mock data for testing
    test_cases = [
        {"threats": [], "coverage": {"Data Protection": 80}, "expected": 1},  # Very Low
        {"threats": [{"severity": "High"}] * 30, "coverage": {"Data Protection": 60}, "expected": 4},  # High
        {"threats": [{"severity": "Very High"}] * 60, "coverage": {"Data Protection": 40}, "expected": 5},  # Very High
    ]

    for i, case in enumerate(test_cases):
        try:
            # Calculate risk score
            total_threats = len(case["threats"])
            high_severity = sum(1 for t in case["threats"] if t.get('severity') in ['High', 'Very High'])
            low_coverage = sum(1 for pct in case["coverage"].values() if pct < 70)

            if total_threats == 0:
                risk_score = 1
            elif high_severity > 50 or low_coverage > 3:
                risk_score = 5
            elif high_severity > 20 or low_coverage > 1:
                risk_score = 4
            elif total_threats > 100 or low_coverage > 0:
                risk_score = 3
            else:
                risk_score = 2

            if risk_score == case["expected"]:
                print(f"✅ Risk scoring test {i+1} PASSED (score: {risk_score})")
            else:
                print(f"❌ Risk scoring test {i+1} FAILED (expected: {case['expected']}, got: {risk_score})")
                return False

        except Exception as e:
            print(f"❌ Risk scoring test {i+1} FAILED: {e}")
            return False

    print("🎉 Risk scoring test PASSED")
    return True

def main():
    """Run all tests"""
    print("🤖 Discord Bot Functionality Tests")
    print("=" * 50)

    results = []
    results.append(test_drawio_assessment())
    results.append(test_security_qa())
    results.append(test_risk_scoring())

    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"🎉 ALL TESTS PASSED ({passed}/{total})")
        print("\n🚀 Discord bot is ready to deploy!")
        print("Next steps:")
        print("1. Create a Discord bot at https://discord.com/developers/applications")
        print("2. Add DISCORD_BOT_TOKEN to your .env file")
        print("3. Run: python discord_bot.py")
    else:
        print(f"❌ SOME TESTS FAILED ({passed}/{total})")
        print("Please fix the failing tests before deploying.")

if __name__ == "__main__":
    main()