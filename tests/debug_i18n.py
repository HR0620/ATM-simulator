import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.i18n_manager import I18nManager

i18n = I18nManager()
val = i18n.get("msg.return_menu_countdown", seconds=5)
print(f"Result: {val}")

# Debug raw dict
print(f"Raw dict value: {i18n.translations['msg']['return_menu_countdown']}")
