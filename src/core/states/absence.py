import time
from src.core.state_machine import State


class UserAbsentWarningState(State):
    """離席警告ステート"""

    def on_enter(self, prev_state=None):
        self.previous_state = prev_state
        self.controller.play_beep_se()
        self.start_time = time.time()
        self.timeout_sec = 10
        self.controller.ui.set_click_callback(self._on_click)

    def on_exit(self):
        self.controller.ui.set_click_callback(None)

    def _on_click(self, zone):
        self._handle_selection(zone)

    def _handle_selection(self, zone):
        if zone == "left":
            self.controller.play_button_se()
            self.controller.grace_period_frames = 90
            from src.core.states.system import FaceAlignmentState
            self.controller.change_state(FaceAlignmentState)
        elif zone == "right":
            self.controller.play_back_se()
            self.controller.grace_period_frames = 90
            from src.core.states.menu import MenuState
            self.controller.change_state(MenuState)
        else:
            self.controller.play_beep_se()

    def _resume(self):
        """元の操作へ復帰"""
        self.controller.play_button_se()
        self.controller.grace_period_frames = 90

        if self.previous_state:
            if self.previous_state.__class__ != self.__class__:
                self.controller.change_state(self.previous_state.__class__)
            else:
                from src.core.states.menu import MenuState
                self.controller.change_state(MenuState)
        else:
            from src.core.states.menu import MenuState
            self.controller.change_state(MenuState)

    def update(self, frame, gesture, key_event=None, progress=0,
               current_direction=None, debug_info=None):

        elapsed = time.time() - self.start_time
        remaining = max(0, int(self.timeout_sec - elapsed))

        if elapsed >= self.timeout_sec:
            from src.core.states.menu import MenuState
            self.controller.change_state(MenuState)
            return

        self.controller.ui.render_frame(frame, {
            "mode": "absence_warning",
            "header": "btn.confirm",
            "message": "msg.absent_warning",
            "countdown": remaining,
            "guides": {"center": "操作に戻る"},
            "progress": progress,
            "current_direction": current_direction,
            "debug_info": debug_info,
        })

        if gesture == "center" or (key_event and key_event.keysym == "Return"):
            self._resume()
