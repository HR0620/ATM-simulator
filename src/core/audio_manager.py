import pygame
import time
import os
from src.paths import get_resource_path
from src.core.config_loader import ConfigLoader


class AudioManager:
    def __init__(self):
        self.config = ConfigLoader().get("audio", {})
        self.cooldown = self.config.get("se_cooldown", 0.1)
        self._last_se_time = 0
        self._last_se_file = ""
        self.current_lang = "JP"  # Default, updated by controller

        try:
            pygame.mixer.init()
            # Reserve channel 0 for voice to allow separate control if needed
            pygame.mixer.set_reserved(1)
        except Exception as e:
            print(f"Audio init failed: {e}")

    def set_language(self, lang_code):
        self.current_lang = lang_code

    def play(self, filename: str, force: bool = False):
        """Legacy alias for play_se (or smart detection if needed)"""
        # For now, assume all legacy calls are SEs ("push-enter", "beep")
        # Map common aliases from states.py
        aliases = {
            "push-enter": "touch-button",
            "cancel": "cancel",
            "beep": "beep",
            "back": "back",
            "card-insert": "card-insert",  # if exists
            "cash-count": "cash-count",  # if exists
        }

        real_name = aliases.get(filename, filename)
        self.play_se(real_name, force)

    def play_se(self, filename: str, force: bool = False):
        """Play Sound Effect (Global, assets/effects)"""
        if not pygame.mixer.get_init():
            return

        now = time.time()
        # Debounce
        if not force:
            if filename == self._last_se_file and (now - self._last_se_time < 0.05):
                return
            if (now - self._last_se_time < self.cooldown):
                return

        # Path: resources/assets/effects/{filename}.mp3
        base_path = os.path.join("assets", "effects", filename)

        path = self._resolve_audio_path(base_path)
        if path:
            try:
                # SE uses a free channel
                pygame.mixer.find_channel(True).play(pygame.mixer.Sound(path))
                self._last_se_time = now
                self._last_se_file = filename
            except Exception as e:
                print(f"Failed to play SE {filename}: {e}")

    def play_voice(self, key: str, force: bool = True):
        """
        Play Voice Guide (Localized) with Fallback logic.
        Stops previous voice.

        Path Priority:
        1. resources/i18n/{CURRENT_LANG}/voice/{key}.mp3
        2. resources/i18n/EN/voice/{key}.mp3
        3. Fallback: Play 'assert.mp3' (SE) and Log Warning.

        Args:
            key: key name (e.g. "welcome")
        """
        if not pygame.mixer.get_init():
            return

        lang = self.current_lang
        filename = f"{key}"  # No prefix

        # 1. Try Current Language
        base_path = os.path.join("i18n", lang, "voice", filename)
        path = self._resolve_audio_path(base_path)

        # 2. Try Fallback (EN) if different
        if not path and lang != "EN":
            print(f"WARN: Voice '{key}' missing for '{lang}', trying fallback (EN).")
            base_path_en = os.path.join("i18n", "EN", "voice", filename)
            path = self._resolve_audio_path(base_path_en)

        if path:
            try:
                # Voice uses Channel 0 (reserved)
                pygame.mixer.Channel(0).stop()
                sound = pygame.mixer.Sound(path)
                pygame.mixer.Channel(0).play(sound)
                return  # Success
            except Exception as e:
                print(f"ERROR: Failed to play Voice {key} ({path}): {e}")
        else:
            print(f"ERROR: Voice file not found for key: {key} (checked {lang} and EN)")

        # 3. Total Failure -> Play Assert SE
        self.play_se("assert", force=True)

    def _resolve_audio_path(self, relative_base):
        for ext in [".mp3", ".wav", ".ogg"]:
            # Check if relative_base already has extension? The input logic sends without extension usually?
            # Actually implementation plan says filename = f"{key}", so it has no extension.
            # But wait, logic below adds extension.
            path = get_resource_path(relative_base + ext)
            if os.path.exists(path):
                return path
        return None

    def stop(self):
        if pygame.mixer.get_init():
            pygame.mixer.stop()  # Stop all channels

    def quit(self):
        if pygame.mixer.get_init():
            pygame.mixer.quit()
