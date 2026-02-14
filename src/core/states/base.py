from src.core.state_machine import State
from src.core.input_handler import InputBuffer


class BaseInputState(State):
    """入力系Stateの共通基底クラス"""

    # サブクラスでオーバーライド
    INPUT_MAX = 6
    MIN_INPUT_LENGTH = 1
    ALIGN_RIGHT = False
    HEADER = ""
    MESSAGE = ""
    UNIT = ""
    GUIDANCE_EMPTY = "guidance.check_input"
    DIGIT_ONLY = True

    def on_enter(self, prev_state=None):
        # Rule 1: Explicit Initialization
        self.input_buffer = InputBuffer(
            max_length=self.INPUT_MAX,
            is_pin=False,
            digit_only=self.DIGIT_ONLY
        )
        self._message = ""
        self._message_params = {}
        self.controller.ui.set_click_callback(self._on_click)

        if hasattr(super(), 'on_enter'):
            super().on_enter(prev_state)

    def on_exit(self):
        self.controller.ui.set_click_callback(None)

    def _on_click(self, zone):
        if zone == "right":
            self._on_back()
        elif zone == "left":
            self._confirm_input()

    def _on_back(self):
        """戻る操作の一元管理"""
        self.controller.play_back_se()
        # MenuState to be resolved at runtime to avoid circular imports?
        # Or import inside the method.
        from src.core.states.menu import MenuState
        self.controller.change_state(MenuState)

    def _confirm_input(self):
        """入力確定処理"""
        val = self.input_buffer.get_value()
        if len(val) >= self.MIN_INPUT_LENGTH:
            self.controller.play_button_se()
            self._on_input_complete(val)
        else:
            self.controller.ui.show_guidance(self.GUIDANCE_EMPTY, is_error=True)
            self.controller.play_beep_se()

    def _on_input_complete(self, value):
        pass

    def update(self, frame, gesture, key_event=None, progress=0,
               current_direction=None, debug_info=None):

        guides = {"left": "btn.next", "right": "btn.back"}

        # Rule 1: Use initialized instance variables
        msg = self._message or self.MESSAGE

        self.controller.ui.render_frame(frame, {
            "mode": "input",
            "header": self.HEADER,
            "message": msg,
            "message_params": self._message_params,
            "input_value": self.input_buffer.get_display_value(),
            "input_max": self.INPUT_MAX,
            "input_unit": self.UNIT,
            "align_right": self.ALIGN_RIGHT,
            "guides": guides,
            "progress": progress,
            "current_direction": current_direction,
            "debug_info": debug_info,
        })

        if gesture == "right":
            self._on_back()
            return

        if gesture == "left":
            self._confirm_input()
            return

        if gesture == "center":
            self.controller.ui.show_guidance("guidance.select_action")
            return

        if key_event:
            self._handle_key(key_event)

    def _handle_key(self, key_event):
        char = key_event.char
        if char == " ":
            return
        if self.DIGIT_ONLY:
            if char.isdigit():
                if self.input_buffer.add_char(char):
                    self.controller.play_push_button_se()
                else:
                    self.controller.play_beep_se()
                return
        else:
            if len(char) == 1 and char.isprintable():
                if self.input_buffer.add_char(char):
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
