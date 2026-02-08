import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Mock pygame before importing src modules
# This needs to be done BEFORE any import that brings in pygame
mock_sys_modules = {'pygame': MagicMock(), 'pygame.mixer': MagicMock()}
with patch.dict('sys.modules', mock_sys_modules):
    from src.core.config_loader import ConfigLoader
    from src.core.i18n_manager import I18nManager
    from src.core.audio_manager import AudioManager
    # Also import the module itself to access the mocked pygame attached to it
    import src.core.audio_manager


class TestRefactoring(unittest.TestCase):
    def test_config_loader(self):
        loader = ConfigLoader()
        self.assertIsInstance(loader.config, dict)
        self.assertIn("ui", loader.config)
        self.assertIn("audio", loader.config)

    def test_i18n_manager(self):
        i18n = I18nManager()
        # Default is JP
        self.assertEqual(i18n.current_lang, "JP")

        # Test key resolution
        val = i18n.get("ui.main_menu")
        self.assertNotEqual(val, "MISSING:ui.main_menu")
        print(f"Resolved ui.main_menu: {val}")

        # Test formatting
        val_fmt = i18n.get("msg.return_menu_countdown", **{"seconds": 5})
        self.assertIn("5", val_fmt)
        print(f"Resolved format: {val_fmt}")

    def test_audio_manager(self):
        # Access the Mock object that AudioManager imported
        # Because we mocked sys.modules['pygame'], the module imported by AudioManager IS that mock.
        mock_pygame = src.core.audio_manager.pygame

        # Configure the mock
        mock_pygame.mixer.get_init.return_value = True

        # Reset mocks to clear initialization calls
        mock_pygame.reset_mock()

        audio = AudioManager()

        # Check if play calls music.load
        with patch("src.core.audio_manager.os.path.exists", return_value=True):
            audio.play("button", force=True)

            # Assert on the mock
            # Note: logic calls load(path) then play()
            mock_pygame.mixer.music.load.assert_called()
            mock_pygame.mixer.music.play.assert_called()


if __name__ == "__main__":
    unittest.main()
