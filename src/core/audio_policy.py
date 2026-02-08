"""
Audio Policy Module

Responsible for mapping the current applications state and context to a specific audio voice key.
This module is PURELY DECLARATIVE and should not contain UI logic or side effects.
"""


from src.core.transaction_context import TransactionContext


class AudioPolicy:
    @staticmethod
    def get_audio_key(state_instance, context: TransactionContext) -> str | None:
        """
        Determines the audio key to play based on the state and context.

        Args:
            state_instance: The current State instance.
            context: The TransactionContext instance from the controller.

        Returns:
            str: The audio key (e.g., "welcome", "retry-pin") or None if no audio should play.
        """
        state_name = state_instance.__class__.__name__

        # 1. FaceAlignmentState -> "welcome"
        if state_name == "FaceAlignmentState":
            return "welcome"

        # 2. MenuState -> "push-button"
        if state_name == "MenuState":
            return "push-button"

        # 3. ConfirmationState -> "check-screen"
        if state_name == "ConfirmationState":
            return "check-screen"

        # 4. WithdrawAccountInputState -> "withdrawl-account"
        if state_name == "WithdrawAccountInputState":
            return "withdrawl-account"

        # 5. TransferTargetInputState -> "recipient-account"
        if state_name == "TransferTargetInputState":
            return "recipient-account"

        # 6. CreateAccountNameInputState -> "enter-name"
        if state_name == "CreateAccountNameInputState":
            return "enter-name"

        # 7. GenericAmountInputState -> "pay-money"
        if state_name == "GenericAmountInputState":
            return "pay-money"

        # 8. PinInputState -> Context Dependent
        if state_name == "PinInputState":
            # Determine mode from context
            # "pin_mode" should be set by the state logic (normal, create_1, create_2, retry)
            mode = context.pin_mode if context.pin_mode else "normal"

            if mode == "create_1":
                return "enter-new-pin"
            if mode == "create_2":
                return "enter-new-pin"
            if mode == "retry":
                return "retry-pin"

            # Default "normal" or withdrawal auth
            return "enter-pin"

        # 9. ResultState -> result type Dependent
        if state_name == "ResultState":
            if context.is_account_created:
                return "create-account"
            return "come-again"

        # Default: No audio
        return None
