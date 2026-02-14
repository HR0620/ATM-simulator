from src.core.state_machine import State


class MenuState(State):
    """メインメニュー"""
    IDLE_TIMEOUT_SEC = 10  # アイドル検知時間

    def on_enter(self, prev_state=None):
        # Rule 1: Explicit Initialization
        self._message = ""
        self._message_params = {}

        self.controller.shared_context.reset()
        self.controller.ui.set_click_callback(self._on_click)

        # アイドルタイマー開始
        self._idle_timer_id = None
        self._start_idle_timer()

        if hasattr(super(), 'on_enter'):
            super().on_enter(prev_state)

    def on_exit(self):
        self.controller.ui.set_click_callback(None)
        self._cancel_idle_timer()

    def _start_idle_timer(self):
        self._cancel_idle_timer()
        self._idle_timer_id = self.controller.root.after(
            self.IDLE_TIMEOUT_SEC * 1000,
            self._on_idle
        )

    def _cancel_idle_timer(self):
        if hasattr(self, '_idle_timer_id') and self._idle_timer_id:
            self.controller.root.after_cancel(self._idle_timer_id)
            self._idle_timer_id = None

    def _on_idle(self):
        """アイドル状態になったらタイマー再開"""
        self._start_idle_timer()

    def _on_click(self, zone):
        self._start_idle_timer()
        self._handle_selection(zone)

    def _handle_selection(self, zone):
        if zone == "left":
            self.controller.play_button_se()
            self.controller.shared_context.reset()
            self.controller.shared_context.transaction = "transfer"
            from src.core.states.transfer import TransferTargetInputState
            self.controller.change_state(TransferTargetInputState)
        elif zone == "center":
            self.controller.play_button_se()
            self.controller.shared_context.reset()
            self.controller.shared_context.transaction = "withdraw"
            from src.core.states.withdraw import WithdrawAccountInputState
            self.controller.change_state(WithdrawAccountInputState)
        elif zone == "right":
            self.controller.play_button_se()
            self.controller.shared_context.reset()
            self.controller.shared_context.transaction = "create_account"
            from src.core.states.create_account import CreateAccountNameInputState
            self.controller.change_state(CreateAccountNameInputState)
        else:
            self.controller.play_beep_se()

    def update(self, frame, gesture, key_event=None, progress=0,
               current_direction=None, debug_info=None):
        if key_event:
            self.controller.play_beep_se()

        self.controller.ui.render_frame(frame, {
            "mode": "menu",
            "header": "ui.main_menu",
            "buttons": [
                {"zone": "left", "label": "btn.transfer"},
                {"zone": "center", "label": "btn.withdraw"},
                {"zone": "right", "label": "btn.create_account"},
            ],
            "progress": progress,
            "current_direction": current_direction,
            "debug_info": debug_info,
        })

        if gesture:
            self._start_idle_timer()
            self._handle_selection(gesture)
