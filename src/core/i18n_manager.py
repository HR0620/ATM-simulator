import json
import os
from typing import Dict, Any
from src.paths import get_resource_path
from src.core.config_loader import ConfigLoader


class I18nManager:
    def __init__(self):
        self.config = ConfigLoader().config
        self.current_lang = self.config.get("language", "JP")
        self.translations: Dict[str, Any] = {}
        self.load_language(self.current_lang)

    def load_language(self, lang_code: str):
        """Load specific language JSON"""
        # Path: resources/i18n/{LANG}/text/{LANG}.json
        # Check if lang_code is simplified/traditional for file path if needed
        # Assuming folder structure matches lang_code exactly

        relative_path = f"i18n/{lang_code}/text/{lang_code}.json"
        path = get_resource_path(relative_path)

        if not os.path.exists(path):
            print(f"Language file not found: {path} (Falling back to JP)")
            # Fallback to JP if target not found
            if lang_code != "JP":
                self.load_language("JP")
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                self.translations = json.load(f)
            self.current_lang = lang_code
        except Exception as e:
            print(f"Failed to load language {lang_code}: {e}")

    def get(self, key: str, **kwargs) -> str:
        """
        Get translated string by key (e.g. "ui.main_menu").
        Supports formatting (e.g. {amount}).
        """
        keys = key.split(".")
        val = self.translations

        try:
            for k in keys:
                val = val.get(k, None)
                if val is None:
                    return f"MISSING:{key}"

            if isinstance(val, str):
                if kwargs:
                    try:
                        return val.format(**kwargs)
                    except Exception:
                        return val  # Return unformatted on error, safer than crashing
                        # return f"ERROR:{key}"
                return val
            return str(val)

        except Exception:
            return f"ERROR:{key}"

    def set_language(self, lang_code: str):
        self.load_language(lang_code)
