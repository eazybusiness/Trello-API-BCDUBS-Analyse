#!/usr/bin/env python3
"""
Test script to verify custom field parsing functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from generate_completed_html import _parse_minutes_from_custom_field

def test_parse_minutes():
    """Test the minutes parsing function with various inputs."""
    test_cases = [
        ("45", 45),
        ("45 minuten", 45),
        ("60 Minuten", 60),
        ("30", 30),
        ("120 min", 120),
        ("", None),
        (None, None),
        ("no number here", None),
        ("video is 75 minutes long", 75),
        ("approx 90 min", 90),
    ]
    
    print("Testing _parse_minutes_from_custom_field:")
    print("=" * 50)
    
    all_passed = True
    for input_str, expected in test_cases:
        result = _parse_minutes_from_custom_field(input_str)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        print(f"{status}: '{input_str}' -> {result} (expected {expected})")
        if result != expected:
            all_passed = False
    
    print("=" * 50)
    if all_passed:
        print("🎉 All tests passed!")
    else:
        print("❌ Some tests failed!")
    
    return all_passed

if __name__ == "__main__":
    test_parse_minutes()
