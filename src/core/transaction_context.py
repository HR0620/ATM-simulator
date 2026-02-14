from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class TransactionContext:
    """
    Transactions and State Context.
    Replaces the dictionary-based shared_context for type safety.
    """
    # Transaction Type (e.g., "withdraw", "deposit", "balance", "transfer", "create_account")
    transaction: Optional[str] = None

    # Account Operations
    account_number: Optional[str] = None
    target_account: Optional[str] = None
    account_name: Optional[str] = None
    amount: int = 0

    # PIN Flow
    pin_input: str = ""
    pin: Optional[str] = None
    first_pin: Optional[str] = None
    pin_step: int = 1      # 1 or 2 (for creation confirmation)
    pin_trials: int = 0    # Number of failed attempts
    pin_mode: str = "normal"  # "normal", "create_1", "create_2", "retry", "auth"

    # Result State
    is_account_created: bool = False
    is_error: bool = False
    result_message: str = ""
    result_message_params: Dict[str, Any] = field(default_factory=dict)

    # Temporary/Generic storage if strictly needed
    extra: Dict[str, Any] = field(default_factory=dict)

    def reset(self):
        """Reset context for a new session or transaction."""
        self.transaction = None
        self.account_number = None
        self.target_account = None
        self.account_name = None
        self.amount = 0
        self.pin_input = ""
        self.first_pin = None
        self.pin = None
        self.pin_step = 1
        self.pin_trials = 0
        self.pin_mode = "normal"
        self.is_account_created = False
        self.is_error = False
        self.result_message = ""
        self.result_message_params.clear()

    def validate_for_transaction(self):
        """Perform transition-time validation."""
        if self.transaction == "withdraw" and not self.account_number:
            raise ValueError("Withdrawal requires account_number.")
        if self.transaction == "transfer" and (not self.account_number or not self.target_account):
            raise ValueError("Transfer requires both account_number and target_account.")
        if self.transaction == "create_account" and not self.account_name:
            raise ValueError("Account creation requires account_name.")
