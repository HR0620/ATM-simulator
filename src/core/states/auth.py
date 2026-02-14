from src.core.states.base import BaseInputState
from src.core.input_handler import InputBuffer
from src.core.pin_validator import is_valid_pin


class PinInputState(BaseInputState):
    """暗証番号入力"""
    INPUT_MAX = 4
    MIN_INPUT_LENGTH = 4
    ALIGN_RIGHT = False
    HEADER = "btn.confirm"
    GUIDANCE_EMPTY = "guidance.empty.pin"

    def on_enter(self, prev_state=None):
        if hasattr(super(), 'on_enter'):
            super().on_enter(prev_state)

        # BaseInputState already initializes _message to "" and _message_params to {}.
        # Subclass can now safely override them.

        txn = self.controller.shared_context.transaction
        if txn is None:
            from src.core.states.menu import MenuState
            self.controller.change_state(MenuState)
            return

        step = self.controller.shared_context.pin_step or 1
        mode = "normal"
        if txn == "create_account":
            mode = f"create_{step}"
        elif txn == "withdraw":
            mode = "auth"

        self.controller.shared_context.pin_mode = mode
        self.controller.pin_pad.reset_random_mapping()

        # Override input buffer configuration
        self.input_buffer = InputBuffer(max_length=4, is_pin=True, digit_only=True)
        self.controller.ui.set_click_callback(self._on_click)
        self._message = self._get_message()

    def _get_message(self):
        txn = self.controller.shared_context.transaction
        step = self.controller.shared_context.pin_step

        if txn == "create_account":
            if step == 1:
                return "input.pin.first"
            else:
                return "input.pin.confirm"
        return "input.pin.default"

    def update(self, frame, gesture, key_event=None, progress=0,
               current_direction=None, debug_info=None):
        keypad = self.controller.pin_pad.get_layout_info()

        self.controller.ui.render_frame(frame, {
            "mode": "pin_input",
            "header": self.HEADER,
            "message": self._message,
            "message_params": self._message_params,
            "input_value": self.input_buffer.get_display_value(),
            "keypad_layout": keypad,
            "guides": {"left": "btn.next", "right": "btn.back"},
            "progress": progress,
            "current_direction": current_direction,
            "debug_info": debug_info,
        })

        if gesture == "left":
            self._confirm_input()
            return
        if gesture == "right":
            self._on_back()
            return

        if key_event:
            self._handle_key(key_event)

    def _handle_key(self, key_event):
        char = key_event.char.lower()
        num = self.controller.pin_pad.get_number(char)

        if num is not None:
            if self.input_buffer.add_char(num):
                self.controller.play_push_button_se()
            else:
                self.controller.play_beep_se()
            return

        if key_event.keysym == "BackSpace":
            if self.input_buffer.backspace():
                self.controller.play_cancel_se()
            else:
                self.controller.play_beep_se()
        elif key_event.keysym == "Return":
            self._confirm_input()
        elif key_event.keysym == "Escape":
            self._on_back()
        else:
            if char.isprintable() and char != "":
                self.controller.play_beep_se()

    def _on_input_complete(self, value):
        self._on_pin_entered(value)

    def _on_pin_entered(self, pin):
        txn = self.controller.shared_context.transaction
        ctx = self.controller.shared_context
        am = self.controller.account_manager

        if txn == "withdraw":
            acct = ctx.account_number
            success, info = am.verify_pin(acct, pin)

            if success:
                ctx.pin = pin
                from src.core.states.common import GenericAmountInputState
                self.controller.change_state(GenericAmountInputState)
            else:
                if info == -1:  # 凍結
                    self.controller.play_assert_se()
                    ctx.is_error = True
                    ctx.result_message = "error.pin.locked"
                    from src.core.states.result import ResultState
                    self.controller.change_state(ResultState)
                elif info == -2:
                    self.controller.play_assert_se()
                    ctx.is_error = True
                    ctx.result_message = "error.account.invalid"
                    from src.core.states.result import ResultState
                    self.controller.change_state(ResultState)

                self.controller.play_retry_pin_voice()
                self.input_buffer.clear()
                self.controller.pin_pad.reset_random_mapping()
                ctx.pin_mode = "retry"
                self._message = "error.pin.incorrect"
                self._message_params = {"remaining": info}

                if info <= 0:
                    self.controller.play_assert_se()
                    ctx.is_error = True
                    ctx.result_message = "error.pin.locked"
                    from src.core.states.result import ResultState
                    self.controller.change_state(ResultState)

        elif txn == "create_account":
            step = ctx.pin_step or 1
            if step == 1:
                is_safe, _ = is_valid_pin(pin)
                if not is_safe:
                    self.controller.play_retry_pin_voice()
                    self.input_buffer.clear()
                    self.controller.pin_pad.reset_random_mapping()
                    self._message = "error.pin.safety"
                    return

                ctx.first_pin = pin
                ctx.pin_step = 2
                self.input_buffer.clear()
                self.controller.pin_pad.reset_random_mapping()
                self.controller.play_retry_pin_voice()
                self._message = "input.pin.confirm"

            elif step == 2:
                if ctx.first_pin == pin:
                    ctx.pin = pin
                    from src.core.states.common import ConfirmationState
                    self.controller.change_state(ConfirmationState)
                else:
                    ctx.pin_step = 1
                    self.input_buffer.clear()
                    self.controller.pin_pad.reset_random_mapping()
                    self.controller.play_retry_pin_se()
                    self._message = "error.pin.mismatch"
