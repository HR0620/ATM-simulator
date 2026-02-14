from src.core.state_machine import State


class LanguageModal(State):
    """言語選択モーダル"""
    _header_key = "ui.select_language"

    def on_enter(self, prev_state=None):
        self.selected_index = 0
        self.languages = []
        self.base_mode = "menu"
        self.base_header = "ui.main_menu"

        if prev_state:
            self.base_mode = prev_state.__class__.__name__
            if hasattr(prev_state, "_header_key"):
                self.base_header = prev_state._header_key

        self.controller.session.reset_activity()
        import json
        from src.paths import get_resource_path

        lang_path = get_resource_path("config/languages.json")
        with open(lang_path, "r", encoding="utf-8") as f:
            all_langs = json.load(f).get("languages", [])

        self.languages = [
            {
                "code": item["code"],
                "display_name": item.get("display_name", item["code"]),
            }
            for item in all_langs
            if item.get("enabled", True)
        ]
        if not self.languages:
            self.languages = [{"code": "JP", "display_name": "日本語"}]

        current = self.controller.i18n.current_lang
        codes = [item["code"] for item in self.languages]
        try:
            self.selected_index = codes.index(current)
        except ValueError:
            self.selected_index = 0

        self.controller.play_voice("check-screen")
        self.controller.ui.set_click_callback(self._on_click)

    def on_exit(self):
        self.controller.ui.set_click_callback(None)

    def _move_prev(self):
        self.controller.play_se("button")
        self.selected_index = (self.selected_index - 1) % len(self.languages)

    def _move_next(self):
        self.controller.play_se("button")
        self.selected_index = (self.selected_index + 1) % len(self.languages)

    def _on_click(self, action):
        if action.startswith("lang_select:"):
            index = int(action.split(":", 1)[1])
            if index != self.selected_index:
                self.controller.play_se("push-button")
                self.selected_index = index
        elif action == "lang_confirm":
            self.controller.play_button_se()
            self._confirm_selection()
        elif action == "lang_back":
            self.controller.play_back_se()
            self.controller.close_modal()

    def update(self, frame, gesture, key_event=None, progress=0,
               current_direction=None, debug_info=None):

        self.controller.ui.render_frame(frame, {
            "mode": "language_modal",
            "base_mode": self.base_mode,
            "base_header": self.base_header,
            "languages": self.languages,
            "selected_index": self.selected_index,
            "guides": {
                "left": "btn.lang_confirm",
                "right": "btn.lang_back"
            },
            "progress": progress,
            "current_direction": current_direction,
            "debug_info": debug_info
        })

        if gesture == "left":
            self.controller.play_button_se()
            self._confirm_selection()
            return

        if gesture == "right":
            self.controller.play_back_se()
            self.controller.close_modal()
            return

        if key_event:
            cols = 4
            if key_event.keysym == "Left":
                self.selected_index = (self.selected_index - 1) % len(self.languages)
                self.controller.play_se("push-button")
            elif key_event.keysym == "Right":
                self.selected_index = (self.selected_index + 1) % len(self.languages)
                self.controller.play_se("push-button")
            elif key_event.keysym == "Up":
                self.selected_index = (self.selected_index - cols) % len(self.languages)
                self.controller.play_se("push-button")
            elif key_event.keysym == "Down":
                self.selected_index = (self.selected_index + cols) % len(self.languages)
                self.controller.play_se("push-button")
            elif key_event.keysym == "Return":
                self.controller.play_button_se()
                self._confirm_selection()
            elif key_event.keysym == "Escape":
                self.controller.play_back_se()
                self.controller.close_modal()

    def _confirm_selection(self):
        lang = self.languages[self.selected_index]["code"]
        self.controller.i18n.set_language(lang)
        self.controller.audio.set_language(lang)
        self.controller.config["system"]["language"] = lang
        self.controller.play_voice("welcome")
        self.controller.close_modal()
