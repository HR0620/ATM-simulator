import sys
import os

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.pin_validator import is_valid_pin


def test_pin_validator():
    test_cases = [
        # (PIN, ExpectedResult, CaseName)
        ("1112", False, "Invalid: Date-like (Nov 12 or Dec 11) - Note: Used as OK in example 1, but rule 3 makes it NG"),
        ("7890", True, "Valid PIN (7890 allowed)"),
        ("8901", True, "Valid PIN (8901 allowed)"),
        ("1232", True, "Valid PIN (Not a date, not sequential)"),
        ("3199", True, "Valid PIN (Not a real date)"),

        ("1111", False, "Invalid: Identical digits"),
        ("0000", False, "Invalid: Identical digits"),

        ("0123", False, "Invalid: Sequential +1"),
        ("1234", False, "Invalid: Sequential +1"),
        ("6789", False, "Invalid: Sequential +1"),

        ("0602", False, "Invalid: Date MMDD (June 2nd)"),
        ("1225", False, "Invalid: Date MMDD (Dec 25th)"),
        ("0315", False, "Invalid: Date MMDD (Mar 15th)"),
        ("2512", False, "Invalid: Date DDMM (Dec 25th)"),
        ("3101", False, "Invalid: Date DDMM (Jan 31st)"),

        ("123", False, "Invalid: Too short"),
        ("12345", False, "Invalid: Too long"),
        ("abcd", False, "Invalid: Non-digits"),
    ]

    print(f"{'PIN':<10} | {'Expected':<10} | {'Actual':<10} | {'Status':<10} | {'Case Name'}")
    print("-" * 70)

    all_passed = True
    for pin, expected, name in test_cases:
        actual, msg = is_valid_pin(pin)
        status = "PASS" if actual == expected else "FAIL"
        if actual != expected:
            all_passed = False
        print(f"{pin:<10} | {str(expected):<10} | {str(actual):<10} | {status:<10} | {name}")
        if not actual and actual != expected:
            print(f"  -> Error Message: {msg}")

    if all_passed:
        print("\nAll test cases passed!")
    else:
        print("\nSome test cases failed.")
        sys.exit(1)


if __name__ == "__main__":
    test_pin_validator()
