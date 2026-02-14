from src.core.states.base import BaseInputState
from src.core.state_machine import State


class GenericAmountInputState(BaseInputState):
    """金額入力ステート"""
    INPUT_MAX = 7
    MIN_INPUT_LENGTH = 1
    ALIGN_RIGHT = True
    HEADER = "btn.amount"
    MESSAGE = "input.amount"
    UNIT = "unit.currency"
    GUIDANCE_EMPTY = "guidance.empty.amount"

    def on_enter(self, prev_state=None):
        if hasattr(super(), 'on_enter'):
            super().on_enter(prev_state)

        # BaseInputState already initializes _message to "" and _message_params to {}.
        # Subclass can now safely override them or set defaults.
        self.base_mode = "menu"
        self.base_header = "main_menu"

        if prev_state:
            self.base_header = getattr(prev_state, "HEADER", "main_menu")
            state_name = prev_state.__class__.__name__
            if "Withdraw" in state_name:
                self.base_mode = "withdraw"
            elif "Transfer" in state_name:
                self.base_mode = "transfer"

        txn = self.controller.shared_context.transaction
        if txn is None:
            from src.core.states.menu import MenuState
            self.controller.change_state(MenuState)
            return

        if txn == "withdraw":
            self.MESSAGE = "input.amount.balance"
            acct = self.controller.shared_context.account_number
            if acct:
                balance = self.controller.account_manager.get_balance(acct)
                self._message_params = {"balance": balance}
        else:
            self.MESSAGE = "input.amount.transfer"

        if hasattr(super(), 'on_enter'):
            super().on_enter(prev_state)

    def _confirm_input(self):
        amount_str = self.input_buffer.get_value()
        if not amount_str:
            self.controller.play_beep_se()
            return

        amount = int(amount_str)
        if amount <= 0:
            self.controller.play_beep_se()
            return

        self.controller.play_button_se()
        self.controller.shared_context.amount = amount
        self.controller.change_state(ConfirmationState)


class ConfirmationState(State):
    """確認画面ステート"""

    def on_enter(self, prev_state=None):
        # Rule 1: Explicit Initialization
        self._message = ""
        self._message_params = {}
        self.controller.ui.set_click_callback(self._on_click)
        if hasattr(super(), 'on_enter'):
            super().on_enter(prev_state)

    def on_exit(self):
        self.controller.ui.set_click_callback(None)

    def _on_click(self, zone):
        if zone:
            self._handle_selection(zone)

    def _handle_selection(self, zone):
        if zone == "left":
            self.controller.play_button_se()
            from src.core.states.auth import PinInputState
            self.controller.change_state(PinInputState)
        elif zone == "right":
            self.controller.play_cancel_se()
            from src.core.states.menu import MenuState
            self.controller.change_state(MenuState)
        else:
            self.controller.play_beep_se()

    def update(self, frame, gesture, key_event=None, progress=0,
               current_direction=None, debug_info=None):

        title_key = "confirm.title"
        ctx = self.controller.shared_context
        tx_type = ctx.transaction or ""

        msg_key = "confirm.general"
        msg_params = {}

        if tx_type == "transfer":
            msg_key = "confirm.transfer"
            msg_params = {
                "target": ctx.target_account or "",
                "amount": ctx.amount
            }
        elif tx_type == "withdraw":
            msg_key = "confirm.withdraw"
            msg_params = {
                "amount": ctx.amount
            }
        elif tx_type == "create_account":
            msg_key = "confirm.create_account"
            msg_params = {
                "name": ctx.account_name or ""
            }

        self.controller.ui.render_frame(frame, {
            "mode": "confirm",
            "header": title_key,
            "message": msg_key,
            "message_params": msg_params,
            "progress": progress,
            "current_direction": current_direction,
            "debug_info": debug_info
        })

        if gesture == "left" or (key_event and key_event.keysym == "Return"):
            self.controller.play_button_se()
            self._execute_transaction()
            return

        if gesture == "right":
            self.controller.play_back_se()
            from src.core.states.menu import MenuState
            self.controller.change_state(MenuState)
            return

        if gesture == "center":
            self.controller.ui.show_guidance("guidance.confirm_choice")

    def _execute_transaction(self):
        ctx = self.controller.shared_context
        txn = ctx.transaction
        if txn is None:
            from src.core.states.menu import MenuState
            self.controller.change_state(MenuState)
            return

        am = self.controller.account_manager
        msg = ""
        is_error = False
        is_account_created = False

        if txn == "transfer":
            target = ctx.target_account
            amt = ctx.amount
            success, msg = am.deposit(target, amt)
            is_error = not success
        elif txn == "withdraw":
            acct = ctx.account_number
            amt = ctx.amount
            success, msg = am.withdraw(acct, amt)
            if success:
                msg = "msg.withdraw_complete"
            is_error = not success
        elif txn == "create_account":
            name = ctx.account_name
            pin = ctx.pin
            account_num = am.create_account(name, pin, initial_balance=1000)
            msg = "msg.account_created"
            ctx.result_message_params = {"account_number": account_num}
            is_account_created = True

        ctx.result_message = msg
        ctx.is_error = is_error
        ctx.is_account_created = is_account_created

        from src.core.states.result import ResultState
        self.controller.change_state(ResultState)
