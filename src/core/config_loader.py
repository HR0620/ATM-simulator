import yaml
import os
from typing import Any, Dict
from src.paths import get_resource_path


class ConfigLoader:
    _instance = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        try:
            config_path = get_resource_path("config/atm_config.yml")
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    self._config = yaml.safe_load(f)
            else:
                print(f"Config file not found: {config_path}")
                self._config = {}
        except Exception as e:
            print(f"Failed to load config: {e}")
            self._config = {}

    @property
    def config(self) -> Dict[str, Any]:
        return self._config

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)
