from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class IVisionEngine(ABC):
    @abstractmethod
    def get_frame(self) -> Any:
        pass

    @abstractmethod
    def stop(self):
        pass


class IAudioEngine(ABC):
    @abstractmethod
    def play_voice(self, key: str):
        pass

    @abstractmethod
    def play_se(self, key: str):
        pass


class IPersistenceManager(ABC):
    @abstractmethod
    def get_account_name(self, account_number: str) -> Optional[str]:
        pass

    @abstractmethod
    def verify_pin(self, account_number: str, pin: str) -> bool:
        pass

    @abstractmethod
    def get_balance(self, account_number: str) -> int:
        pass

    @abstractmethod
    def update_balance(self, account_number: str, new_balance: int):
        pass


class IUIService(ABC):
    @abstractmethod
    def render_frame(self, frame: Any, state_data: Dict[str, Any]):
        pass

    @abstractmethod
    def set_click_callback(self, callback):
        pass
