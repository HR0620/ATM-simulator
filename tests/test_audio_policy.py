import sys
import os

# Add src to path
sys.path.append(os.getcwd())

from src.core.audio_policy import AudioPolicy

# Mock States


class State:
    pass


class FaceAlignmentState(State):
    pass


class MenuState(State):
    pass


class ConfirmationState(State):
    pass


class WithdrawAccountInputState(State):
    pass


class TransferTargetInputState(State):
    pass


class CreateAccountNameInputState(State):
    pass


class GenericAmountInputState(State):
    pass


class PinInputState(State):
    pass


class ResultState(State):
    pass


def test_audio_policy():
    print("Testing AudioPolicy...")

    # 1. Simple Mapping
    assert AudioPolicy.get_audio_key(FaceAlignmentState(), {}) == "welcome", "FaceAlignment failed"
    assert AudioPolicy.get_audio_key(MenuState(), {}) == "push-button", "Menu failed"
    assert AudioPolicy.get_audio_key(ConfirmationState(), {}) == "check-screen", "Confirmation failed"

    # 2. PinInputState Logic
    # Normal
    ctx = {"pin_mode": "normal"}
    assert AudioPolicy.get_audio_key(PinInputState(), ctx) == "enter-pin", "Pin Normal failed"

    # Create 1
    ctx = {"pin_mode": "create_1"}
    assert AudioPolicy.get_audio_key(PinInputState(), ctx) == "enter-new-pin", "Pin Create 1 failed"

    # Retry
    ctx = {"pin_mode": "retry"}
    assert AudioPolicy.get_audio_key(PinInputState(), ctx) == "retry-pin", "Pin Retry failed"

    # Fallback (no mode set)
    ctx = {}
    assert AudioPolicy.get_audio_key(PinInputState(), ctx) == "enter-pin", "Pin Default failed"

    # 3. ResultState Logic
    # Account Created
    ctx = {"is_account_created": True}
    assert AudioPolicy.get_audio_key(ResultState(), ctx) == "create-account", "Result Create Account failed"

    # Normal Result
    ctx = {"is_account_created": False}
    assert AudioPolicy.get_audio_key(ResultState(), ctx) == "come-again", "Result Normal failed"

    print("ALL TESTS PASSED")


if __name__ == "__main__":
    try:
        test_audio_policy()
    except AssertionError as e:
        print(f"TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
