import time
from src.core.state_machine import State


class ResultState(State):
    """結果/エラー画面"""

    def on_enter(self, prev_state=None):
        # Rule 1: Explicit Initialization
        self._message = ""
        self._message_params = {}

        is_account_created = self.controller.shared_context.is_account_created
        is_error = self.controller.shared_context.is_error

        if is_error:
            self.controller.play_assert_se()

        self.start_time = time.time()
        self.countdown = 10 if is_account_created else 5
        self._start_countdown()

        if hasattr(super(), 'on_enter'):
            super().on_enter(prev_state)

    def on_exit(self):
        pass

    def _start_countdown(self):
        if self.countdown > 0:
            self.controller.root.after(1000, self._tick)
        else:
            from src.core.states.menu import MenuState
            self.controller.change_state(MenuState)

    def _tick(self):
        self.countdown -= 1
        if self.countdown <= 0:
            from src.core.states.menu import MenuState
            self.controller.change_state(MenuState)
        else:
            self.controller.root.after(1000, self._tick)

    def update(self, frame, gesture, key_event=None, progress=0,
               current_direction=None, debug_info=None):
        msg = self.controller.shared_context.result_message or "msg.complete"
        msg_params = self.controller.shared_context.result_message_params
        is_error = self.controller.shared_context.is_error

        self.controller.ui.render_frame(frame, {
            "mode": "result",
            "header": "btn.confirm",
            "message": msg,
            "message_params": msg_params,
            "is_error": is_error,
            "countdown": self.countdown,
            "debug_info": debug_info,
        })
