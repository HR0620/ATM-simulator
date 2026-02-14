from src.core.states.base import BaseInputState


class CreateAccountNameInputState(BaseInputState):
    """名前入力"""
    INPUT_MAX = 10
    MIN_INPUT_LENGTH = 1
    ALIGN_RIGHT = False
    HEADER = "btn.create_account"
    MESSAGE = "input.name"
    GUIDANCE_EMPTY = "guidance.empty.name"
    DIGIT_ONLY = False

    def on_enter(self, prev_state=None):
        if hasattr(super(), 'on_enter'):
            super().on_enter(prev_state)

        # BaseInputState already initializes _message to "" and _message_params to {}.
        # Subclass can now safely override them or set defaults.

    def _on_input_complete(self, value):
        self.controller.shared_context.account_name = value
        self.controller.shared_context.pin_step = 1
        from src.core.states.auth import PinInputState
        self.controller.change_state(PinInputState)
