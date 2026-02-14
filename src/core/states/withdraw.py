from src.core.states.base import BaseInputState
from src.core.states.result import ResultState
from src.core.states.common import GenericAmountInputState


class WithdrawAccountInputState(BaseInputState):
    """引き出し時の口座番号入力"""
    INPUT_MAX = 6
    MIN_INPUT_LENGTH = 6
    ALIGN_RIGHT = False
    HEADER = "btn.withdraw"
    MESSAGE = "input.account.self"
    GUIDANCE_EMPTY = "guidance.empty.account"

    def _on_input_complete(self, value):
        if len(value) == 6:
            am = self.controller.account_manager

            # 口座存在チェック
            if am.get_account_name(value) is None:
                self.controller.play_assert_se()
                self.controller.shared_context.is_error = True
                self.controller.shared_context.result_message = "error.account.invalid"
                self.controller.change_state(ResultState)
                return

            # 口座凍結チェック
            if am.is_frozen(value):
                self.controller.play_assert_se()
                self.controller.shared_context.is_error = True
                self.controller.shared_context.result_message = "error.account.frozen"
                self.controller.change_state(ResultState)
                return

            self.controller.shared_context.account_number = value
            self.controller.change_state(GenericAmountInputState)
