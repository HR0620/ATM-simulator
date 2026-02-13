"""
ATM UI モジュール

設計意図:
- レイアウト定数を明示的に定義
- カメラ領域(4:3)とデバッグパネル(右側)を意図的に分離
- 保守性を高めるため描画メソッドを細分化
"""
import tkinter as tk
from PIL import Image, ImageTk
import cv2
import os
from src.ui.styles import Colors, Fonts, Layout as StyleLayout
from src.paths import get_resource_path


class Layout:
    """レイアウト定数"""
    HEADER_HEIGHT = 80
    FOOTER_HEIGHT = 80
    DEBUG_PANEL_WIDTH = 200


class ATMUI:
    def __init__(self, root, config, i18n_manager):
        self.root = root
        self.config = config
        self.i18n = i18n_manager

        # 初期ウィンドウサイズ
        self.width = config["ui"]["window_width"]
        self.height = config["ui"]["window_height"]

        # Canvas
        self.canvas = tk.Canvas(
            root, bg="black", highlightthickness=0,
            width=self.width, height=self.height
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # リサイズイベント
        self.canvas.bind("<Configure>", self._on_resize)

        # クリックイベント
        self.canvas.bind("<Button-1>", self._on_click)
        self._click_callback = None
        self._photo = None

        # クリックフィードバック用
        self._clicked_zone = None
        self._click_feedback_timer = None

        # 画像リソース
        self.bow_image = None
        self._load_images()

        # ガイダンス表示用
        self._guidance_text = ""
        self._guidance_timer = None
        self._last_guidance_time = 0
        self._guidance_cooldown = 2.0  # 2秒間隔
        self._guidance_is_error = False

        # レイアウト計算
        self.last_input_bottom = 0
        self._calculate_layout()

        self._state_data = {}

    def _resolve_text(self, text_or_key, **kwargs):
        """Resolve text if it's a key, otherwise return as is (for safety)"""
        # Simple heuristic: if it contains ".", try to resolve
        # Better: States should pass keys, but sometimes dynamic values.
        # We assume if it looks like a key, we try.
        # Or we always try i18n.get, if missing it returns formatting string?
        # i18n_manager.get returns "MISSING:key" if not found.
        # We should probably trust the I18nManager to handle non-keys gracefully or check existence.
        # Actually, let's assume inputs are keys if they match a pattern, or just try.
        if not isinstance(text_or_key, str):
            return str(text_or_key)

        # Try to resolve
        translated = self.i18n.get(text_or_key, **kwargs)
        if translated.startswith("MISSING:") or translated.startswith("ERROR:"):
            # It might be a raw string
            return text_or_key
        return translated

    def _load_images(self):
        """画像リソース読み込み"""
        try:
            path = get_resource_path("assets/images/bow.png")
            if (os.path.exists(path)):
                self.bow_image = Image.open(path)
        except Exception as e:
            print(f"画像読み込みエラー: {e}")

    def _calculate_layout(self):
        """現在のウィンドウサイズに基づいてレイアウトを計算"""
        # デバッグモード判定
        is_debug = self.config.get("ui", {}).get("debug_mode", True)
        self.panel_width = Layout.DEBUG_PANEL_WIDTH if is_debug else 0

        # メインエリアとデバッグパネル
        self.main_width = self.width - self.panel_width
        self.main_height = self.height

        # ボタン領域
        content_y1 = Layout.HEADER_HEIGHT
        content_y2 = self.height - Layout.FOOTER_HEIGHT
        third = self.main_width // 3

        self.button_zones = {
            "left": {
                "x1": 0, "y1": content_y1,
                "x2": third, "y2": content_y2
            },
            "center": {
                "x1": third, "y1": content_y1,
                "x2": third * 2, "y2": content_y2
            },
            "right": {
                "x1": third * 2, "y1": content_y1,
                "x2": self.main_width, "y2": content_y2
            },
        }

        # 言語ボタン領域 (ヘッダー右端)
        lang_btn_w = 120
        lang_btn_h = 40
        lx = self.main_width - lang_btn_w - 20
        ly = (Layout.HEADER_HEIGHT - lang_btn_h) // 2
        self.language_zone = {
            "x1": lx, "y1": ly,
            "x2": lx + lang_btn_w, "y2": ly + lang_btn_h
        }

        # ガイドボタン領域
        footer_y = self.height - Layout.FOOTER_HEIGHT + 10
        self.guide_zones = {
            "left": {
                "x1": 20, "y1": footer_y,
                "x2": 180, "y2": footer_y + 60
            },
            "right": {
                "x1": self.main_width - 180, "y1": footer_y,
                "x2": self.main_width - 20, "y2": footer_y + 60
            },
        }

    def _on_resize(self, event):
        """ウィンドウリサイズ時にレイアウトを再計算"""
        new_width = event.width
        new_height = event.height

        # サイズが変わった場合のみ更新
        if new_width != self.width or new_height != self.height:
            self.width = new_width
            self.height = new_height
            self.width = new_width
            self.height = new_height
            self._calculate_layout()

    def set_language_callback(self, callback):
        self._language_callback = callback

    def set_click_callback(self, callback):
        self._click_callback = callback

    def _on_click(self, event):
        if self._click_callback is None:
            return

        x, y = event.x, event.y

        # メインエリア外は無視
        if x > self.main_width:
            return

        # モーダル表示中は背景のクリックを無効化
        # モーダル表示中は背景クリックを無効化し、モーダル要素だけを受け付ける
        mode = self._state_data.get("mode", "")
        if mode == "language_modal":
            # 現在は言語選択モーダルのみ
            # 必要に応じてここでモーダル内の要素クリック判定を行う
            # 今のところジェスチャーとキーボードのみのため、クリックは無視
            modal_zones = self._state_data.get("modal_hit_areas", [])
            for zone in modal_zones:
                if (zone["x1"] <= x <= zone["x2"] and
                        zone["y1"] <= y <= zone["y2"]):
                    clicked_zone = zone["action"]
                    clicked_type = "modal"
                    self._clicked_zone = (clicked_zone, clicked_type)

                    if self._click_feedback_timer:
                        self.root.after_cancel(self._click_feedback_timer)

                    callback = self._click_callback

                    def execute_modal_callback():
                        self._clicked_zone = None
                        if callback is not None:
                            callback(clicked_zone)

                    self._click_feedback_timer = self.root.after(150, execute_modal_callback)
                    return
            return

        clicked_zone = None
        clicked_type = None  # "button" or "guide"

        for zone_name, zone in self.button_zones.items():
            if (zone["x1"] <= x <= zone["x2"] and
                    zone["y1"] <= y <= zone["y2"]):
                clicked_zone = zone_name
                clicked_type = "button"
                break

        if clicked_zone is None:
            for zone_name, zone in self.guide_zones.items():
                if (zone["x1"] <= x <= zone["x2"] and
                        zone["y1"] <= y <= zone["y2"]):
                    clicked_zone = zone_name
                    clicked_type = "guide"
                    break

        if clicked_zone is None:
            lz = self.language_zone
            if (lz["x1"] <= x <= lz["x2"] and
                    lz["y1"] <= y <= lz["y2"]):
                clicked_zone = "language"
                clicked_type = "language"

        if clicked_zone is not None:
            # クリックフィードバック: 押下状態を設定
            self._clicked_zone = (clicked_zone, clicked_type)

            # 既存のタイマーをキャンセル
            if self._click_feedback_timer:
                self.root.after_cancel(self._click_feedback_timer)

            # 150ms後にコールバックを実行してフィードバックをクリア
            callback = self._click_callback  # キャプチャ

            def execute_callback():
                self._clicked_zone = None
                if clicked_type == "language" and hasattr(self, "_language_callback"):
                    if self._language_callback:
                        self._language_callback()
                elif callback is not None:
                    callback(clicked_zone)

            self._click_feedback_timer = self.root.after(150, execute_callback)

    def render_frame(self, frame, state_data: dict | None = None):
        if state_data:
            self._state_data = state_data

        # 背景クリア
        self.canvas.delete("all")

        # ガイダンス表示の自動クリア（もしあれば）
        # (タイマーで管理されるが念のため描画前に状態確認)

        # 1. カメラ映像をメインエリアに描画
        self._draw_camera_background(frame)

        # 2. デバッグパネル (右側) - 表示モードのみ
        if self.panel_width > 0:
            self._draw_debug_panel()

        # 3. ヘッダー
        header = self._state_data.get("header", "")
        self._draw_header(header)

        # 4. モード別コンテンツ
        mode = self._state_data.get("mode", "menu")
        if mode == "language_modal":
            # ユーザー要望: 背景に元の画面を少し暗くなった状態で表示
            base_mode = self._state_data.get("base_mode", "menu")
            self._draw_mode_content(base_mode)
            # 背景としてのヘッダーも描画 (翻訳を適用)
            base_header_key = self._state_data.get("base_header", "")
            if base_header_key:
                self._draw_header(self._resolve_text(base_header_key))

        self._draw_mode_content(mode)

        # 5. クレジット表記 (常時表示)
        self._draw_credits()

    def _draw_camera_background(self, frame):
        """カメラ映像をメインエリアに全画面で描画"""
        if frame is None:
            return

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)

        # メインエリア全体に引き伸ばし（アスペクト比無視）
        img = img.resize(
            (self.main_width, self.main_height),
            Image.Resampling.BILINEAR
        )

        self._photo = ImageTk.PhotoImage(img)
        self.canvas.create_image(
            0, 0, anchor=tk.NW, image=self._photo, tags="background"
        )

    def _draw_debug_panel(self):
        """右側のデバッグパネル（全体を埋める）"""
        x = self.main_width
        w = Layout.DEBUG_PANEL_WIDTH
        h = self.height

        # 背景（全体を塗りつぶし）
        self.canvas.create_rectangle(
            x, 0, x + w, h,
            fill="#1a1a2e", outline="", tags="overlay"
        )

        # 区切り線
        self.canvas.create_line(
            x, 0, x, h,
            fill="#333366", width=2, tags="overlay"
        )

        # タイトル
        self.canvas.create_rectangle(
            x, 0, x + w, 40,
            fill="#0d0d1a", tags="overlay"
        )
        self.canvas.create_text(
            x + w // 2, 20, text="🔍 デバッグ情報",
            fill="#00aaff", font=("Meiryo UI", 11, "bold"), tags="overlay"
        )

        # デバッグ情報取得
        debug = self._state_data.get("debug_info", {})
        if not debug:
            self.canvas.create_text(
                x + w // 2, h // 2, text="情報なし",
                fill="#666666", font=("Meiryo UI", 12), tags="overlay"
            )
            return

        y_pos = 55

        # 状態名
        state_name = debug.get("state_name", "---")
        self.canvas.create_text(
            x + 10, y_pos, anchor=tk.NW, text="📌 State",
            fill="#888888", font=("Meiryo UI", 9), tags="overlay"
        )
        y_pos += 18
        # 長い名前は短縮
        short_name = state_name.replace("State", "")
        self.canvas.create_text(
            x + 10, y_pos, anchor=tk.NW, text=short_name,
            fill="#ffffff", font=("Consolas", 11, "bold"), tags="overlay"
        )
        y_pos += 35

        # AI予測
        pred = debug.get("prediction")
        if pred:
            class_name = pred.get("class_name", "---")
            confidence = pred.get("confidence", 0)
            color = self._get_class_color(class_name)

            self.canvas.create_text(
                x + 10, y_pos, anchor=tk.NW, text="🤖 AI認識",
                fill="#888888", font=("Meiryo UI", 9), tags="overlay"
            )
            y_pos += 20

            # クラス名（大きく）
            self.canvas.create_text(
                x + w // 2, y_pos + 15, text=class_name.upper(),
                fill=color, font=("Consolas", 18, "bold"), tags="overlay"
            )
            y_pos += 45

            # 信頼度
            self.canvas.create_text(
                x + 10, y_pos, anchor=tk.NW,
                text=f"信頼度: {confidence * 100:.1f}%",
                fill="#aaaaaa", font=("Meiryo UI", 9), tags="overlay"
            )
            y_pos += 18

            bar_w = w - 20
            self.canvas.create_rectangle(
                x + 10, y_pos, x + 10 + bar_w, y_pos + 12,
                fill="#333333", outline="#444444", tags="overlay"
            )
            self.canvas.create_rectangle(
                x + 10, y_pos, x + 10 + bar_w * confidence, y_pos + 12,
                fill=color, tags="overlay"
            )
            y_pos += 30

        # 認識進捗
        progress = debug.get("progress", 0)
        self.canvas.create_text(
            x + 10, y_pos, anchor=tk.NW, text="⏳ 認識進捗",
            fill="#888888", font=("Meiryo UI", 9), tags="overlay"
        )
        y_pos += 18

        bar_w = w - 20
        self.canvas.create_rectangle(
            x + 10, y_pos, x + 10 + bar_w, y_pos + 18,
            fill="#333333", outline="#444444", tags="overlay"
        )
        if progress > 0:
            self.canvas.create_rectangle(
                x + 10, y_pos, x + 10 + bar_w * progress, y_pos + 18,
                fill="#00ff00", tags="overlay"
            )
            # パーセント表示
            self.canvas.create_text(
                x + w // 2, y_pos + 9, text=f"{progress * 100:.0f}%",
                fill="white", font=("Consolas", 10, "bold"), tags="overlay"
            )
        y_pos += 35

        # ロック状態
        is_locked = debug.get("is_locked", False)
        self.canvas.create_text(
            x + 10, y_pos, anchor=tk.NW, text="🔒 ステータス",
            fill="#888888", font=("Meiryo UI", 9), tags="overlay"
        )
        y_pos += 20

        lock_text = "LOCKED" if is_locked else "READY"
        lock_color = "#ff6666" if is_locked else "#66ff66"
        lock_bg = "#440000" if is_locked else "#004400"

        self.canvas.create_rectangle(
            x + 20, y_pos, x + w - 20, y_pos + 30,
            fill=lock_bg, outline=lock_color, width=2, tags="overlay"
        )
        self.canvas.create_text(
            x + w // 2, y_pos + 15, text=lock_text,
            fill=lock_color, font=("Consolas", 14, "bold"), tags="overlay"
        )
        y_pos += 50

        # 操作ヒント
        self.canvas.create_text(
            x + 10, y_pos, anchor=tk.NW, text="💡 操作ガイド",
            fill="#888888", font=("Meiryo UI", 9), tags="overlay"
        )
        y_pos += 20

        hints = [
            "左に手を振る → 左選択",
            "中央に手を出す → 中央",
            "右に手を振る → 右選択",
            "ESC → 終了",
        ]
        for hint in hints:
            self.canvas.create_text(
                x + 10, y_pos, anchor=tk.NW, text=hint,
                fill="#666666", font=("Meiryo UI", 8), tags="overlay"
            )
            y_pos += 16

    def _get_class_color(self, class_name):
        """クラス名に応じた色"""
        colors = {
            "left": "#00aaff",
            "center": "#ffffff",
            "right": "#ff8800",
            "free": "#888888",
        }
        return colors.get(class_name, "#ffffff")

    def _draw_header(self, text_key):
        """ヘッダー描画"""
        text = self._resolve_text(text_key)

        self.canvas.create_rectangle(
            0, 0, self.main_width, Layout.HEADER_HEIGHT,
            fill="#004080", stipple="gray50", tags="overlay"
        )
        self.canvas.create_text(
            self.main_width // 2, Layout.HEADER_HEIGHT // 2,
            text=text, fill="white",
            font=("Meiryo UI", 28, "bold"), tags="overlay"
        )

        exit_text = self._resolve_text("ui.esc_exit")
        self.canvas.create_text(
            self.main_width - 160, Layout.HEADER_HEIGHT // 2, text=exit_text,
            fill="#cccccc", font=("Meiryo UI", 10), tags="overlay", anchor="e"
        )

        # 言語ボタン描画
        self._draw_language_button()

    def _draw_language_button(self):
        zone = self.language_zone
        is_pressed = (self._clicked_zone == ("language", "language"))

        x1, y1, x2, y2 = zone["x1"], zone["y1"], zone["x2"], zone["y2"]
        offset = 2 if is_pressed else 0

        # 影 (通常時のみ)
        if not is_pressed:
            self.canvas.create_rectangle(
                x1 + 2, y1 + 2, x2 + 2, y2 + 2,
                fill="black", stipple="gray50", tags="overlay"
            )

        # 本体
        self.canvas.create_rectangle(
            x1 + offset, y1 + offset, x2 + offset, y2 + offset,
            fill="#0055aa", outline="white", width=2, tags="overlay"
        )

        # テキスト (常に英語)
        self.canvas.create_text(
            (x1 + x2) // 2 + offset, (y1 + y2) // 2 + offset,
            text="Language", fill="white",
            font=("Arial", 10, "bold"), tags="overlay"
        )

    def _draw_mode_content(self, mode):
        """モード別コンテンツ描画"""
        if mode == "menu":
            self._draw_menu_overlay()
        elif mode == "input":
            self._draw_input_overlay()
        elif mode == "pin_input":
            self._draw_pin_input_overlay()
        elif mode == "confirm":
            self._draw_confirm_overlay()
        elif mode == "face_align":
            self._draw_face_align_overlay()
        elif mode == "result":
            self._draw_result_overlay()
        elif mode == "exit":
            self._draw_exit_overlay()
        elif mode == "absence_warning":
            self._draw_result_overlay()
        elif mode == "language_modal":
            self._draw_language_modal_overlay()

        # ガイダンスがあれば最前面に描画
        if self._guidance_text:
            self._draw_guidance_overlay()

    def _draw_menu_overlay(self):
        """メインメニュー"""
        buttons = self._state_data.get("buttons", [])
        current_dir = self._state_data.get("current_direction")
        progress = self._state_data.get("progress", 0)

        for btn in buttons:
            zone_name = btn.get("zone")
            btn_progress = progress if zone_name == current_dir else 0
            self._draw_button_zone(btn, btn_progress)

    def _draw_button_zone(self, btn_data, progress=0):
        """ボタン領域描画（押下エフェクト付き）"""
        zone_name = btn_data.get("zone")
        zone = self.button_zones.get(zone_name)
        if not zone:
            return

        x1, y1, x2, y2 = zone["x1"], zone["y1"], zone["x2"], zone["y2"]
        label_key = btn_data.get("label", "")
        label = self._resolve_text(label_key)

        # 色設定（styles.pyから取得）
        btn_colors = Colors.BUTTON.get(zone_name, Colors.BUTTON["center"])
        bg = btn_colors["bg"]
        fg = btn_colors["fg"]
        pressed_bg = btn_colors["pressed"]

        pad = StyleLayout.BUTTON_PADDING
        shadow_offset = StyleLayout.SHADOW_OFFSET
        press_offset = StyleLayout.PRESS_OFFSET

        # 押下状態の判定（進捗が0.3以上、またはマウスクリック中で押下とみなす）
        is_clicked = (self._clicked_zone is not None and
                      self._clicked_zone[0] == zone_name and
                      self._clicked_zone[1] == "button")
        is_pressed = progress > 0.3 or is_clicked

        # ボタン座標
        bx1, by1, bx2, by2 = x1 + pad, y1 + pad, x2 - pad, y2 - pad

        if is_pressed:
            # 押下時: 影なし、ボタンを少し下・右にずらす
            offset = press_offset
            self.canvas.create_rectangle(
                bx1 + offset, by1 + offset, bx2 + offset, by2 + offset,
                fill=pressed_bg, stipple="gray50",
                outline=Colors.WHITE, width=2, tags="overlay"
            )
            cx, cy = (bx1 + bx2) // 2 + offset, (by1 + by2) // 2 + offset
        else:
            # 通常時: 影を描画してからボタンを描画
            self.canvas.create_rectangle(
                bx1 + shadow_offset, by1 + shadow_offset,
                bx2 + shadow_offset, by2 + shadow_offset,
                fill=Colors.BLACK, stipple="gray50", outline="", tags="overlay"
            )
            self.canvas.create_rectangle(
                bx1, by1, bx2, by2,
                fill=bg, stipple="gray50",
                outline=Colors.WHITE, width=2, tags="overlay"
            )
            cx, cy = (bx1 + bx2) // 2, (by1 + by2) // 2

        # ラベル (自動サイズ調整)
        self._draw_text_fit(
            cx, cy - 10, label,
            font_family=Fonts.button()[0],
            max_size=Fonts.button()[1],
            max_width=bx2 - bx1 - 10,
            fill=fg
        )

        # 操作説明
        # "ui.guidance.action" -> "クリックまたはジェスチャーで選択"
        guide_text = self._resolve_text("guidance.action")
        self.canvas.create_text(
            cx, cy + 35, text=guide_text,
            fill=fg, font=Fonts.tiny(), tags="overlay"
        )

        # 進捗ゲージ
        if progress > 0:
            gy = by2 - 25 + (press_offset if is_pressed else 0)
            gx1 = bx1 + 10 + (press_offset if is_pressed else 0)
            gx2 = bx2 - 10 + (press_offset if is_pressed else 0)
            gw = (gx2 - gx1) * progress
            self.canvas.create_rectangle(
                gx1, gy, gx2, gy + 15,
                fill="#333333", outline="#666666", tags="overlay"
            )
            self.canvas.create_rectangle(
                gx1, gy, gx1 + gw, gy + 15,
                fill=Colors.SUCCESS, tags="overlay"
            )

    def _draw_input_overlay(self):
        """入力画面 (Unified)"""
        msg_key = self._state_data.get("message", "")
        msg_params = self._state_data.get("message_params", {})
        label = self._resolve_text(msg_key, **msg_params)
        input_text = self._state_data.get("input_value", "")
        char_count = self._state_data.get("input_max", 6)
        unit = self._state_data.get("input_unit", "")
        align_right = self._state_data.get("align_right", False)

        self._draw_input_visual(label, input_text, char_count, False, unit, align_right)
        self._draw_guides()

    def _draw_pin_input_overlay(self):
        """暗証番号入力画面 (Unified - Ratio Based Layout)"""
        msg_key = self._state_data.get("message", "")
        msg_params = self._state_data.get("message_params", {})
        label = self._resolve_text(msg_key, **msg_params)
        input_text = self._state_data.get("input_value", "")
        keypad_layout = self._state_data.get("keypad_layout", [])

        # Rule 3: Container Ratios
        upper_cy = int(self.height * 0.35)
        lower_cy = int(self.height * 0.70)

        # Upper Container: Input Visual
        self._draw_input_visual(label, input_text, 4, True, override_cy=upper_cy)

        # Lower Container: Keypad Grid
        if keypad_layout:
            cx = self.main_width // 2

            # Rule 3: Base sizes relative to screen
            cw = min(85, int(self.main_width * 0.12))
            ch = min(65, int(self.height * 0.1))
            padding = 5

            grid_w = (cw + padding) * 3 - padding
            grid_h = (ch + padding) * 4 - padding

            gx = cx - grid_w // 2
            gy = lower_cy - grid_h // 2

            # Rule 4: Keep-Out Rule (Collision Guard)
            # input_bottom + min_padding < keypad_top
            min_padding = int(self.height * 0.05)
            if hasattr(self, "last_input_bottom"):
                if self.last_input_bottom + min_padding > gy:
                    # Implement Shrink Strategy (Rule 3 Fallback)
                    # For now, shift keypad down slightly if possible, or scale down
                    shift = (self.last_input_bottom + min_padding) - gy
                    gy += shift
                    # Ensure we don't go off header/footer (omitted for brevity but implied)

            for row_idx, row in enumerate(keypad_layout):
                for col_idx, item in enumerate(row):
                    if item is None:
                        continue

                    kx = gx + col_idx * (cw + padding)
                    ky = gy + row_idx * (ch + padding)
                    key = item.get("key", "")
                    num = item.get("num", "")

                    # Draw key background
                    self.canvas.create_rectangle(
                        kx, ky, kx + cw, ky + ch,
                        fill="#ffffff", outline="#444444",
                        width=2, tags="overlay"
                    )

                    # Number fits keypad cell
                    num_font_size = int(ch * 0.45)
                    self.canvas.create_text(
                        kx + cw // 2, ky + ch // 3,
                        text=num, fill="#333333",
                        font=("Arial", num_font_size, "bold"), tags="overlay"
                    )

                    # Key ID fits keypad cell
                    id_font_size = max(8, int(ch * 0.15))
                    self.canvas.create_text(
                        kx + cw // 2, ky + (ch * 4) // 5,
                        text=f"[{key.upper()}]", fill="#888888",
                        font=("Arial", id_font_size), tags="overlay"
                    )

        self._draw_guides()

    def _draw_confirm_overlay(self):
        """確認画面"""
        message = self._state_data.get("message", "")
        current_dir = self._state_data.get("current_direction")
        progress = self._state_data.get("progress", 0)

        cx = self.main_width // 2
        cy = self.height // 2

        # メッセージボックス
        self.canvas.create_rectangle(
            cx - 280, cy - 90, cx + 280, cy + 90,
            fill="#ffffff", stipple="gray50",
            outline="#cccccc", width=2, tags="overlay"
        )

        message_key = self._state_data.get("message", "")
        msg_params = self._state_data.get("message_params", {})
        message = self._resolve_text(message_key, **msg_params)

        self.canvas.create_text(
            cx, cy, text=message, fill="#333333",
            font=("Meiryo UI", 18), tags="overlay"
        )

        # はい/いいえボタン
        left_p = progress if current_dir == "left" else 0
        self._draw_action_button(80, self.height - 90, self._resolve_text("btn.yes"), "#005bb5", left_p)

        right_p = progress if current_dir == "right" else 0
        self._draw_action_button(
            self.main_width - 230, self.height - 90,
            self._resolve_text("btn.no"), "#e67e22", right_p
        )

    def _draw_action_button(self, x, y, label, color, progress=0):
        """アクションボタン描画（押下エフェクト付き）"""
        w, h = 150, 55
        shadow_offset = StyleLayout.SHADOW_OFFSET
        press_offset = StyleLayout.PRESS_OFFSET

        is_pressed = progress > 0.3

        if is_pressed:
            # 押下時: 影なし、ボタンをずらす
            offset = press_offset
            self.canvas.create_rectangle(
                x + offset, y + offset, x + w + offset, y + h + offset,
                fill=color, stipple="gray50",
                outline=Colors.WHITE, width=2, tags="overlay"
            )
            self.canvas.create_text(
                x + w // 2 + offset, y + h // 2 + offset, text=label,
                fill="white", font=("Meiryo UI", 14, "bold"), tags="overlay"
            )
            # 進捗ゲージ
            if progress > 0:
                gw = w * progress
                self.canvas.create_rectangle(
                    x + offset, y + h - 6 + offset,
                    x + gw + offset, y + h + offset,
                    fill=Colors.SUCCESS, tags="overlay"
                )
        else:
            # 通常時: 影を描画
            self.canvas.create_rectangle(
                x + shadow_offset, y + shadow_offset,
                x + w + shadow_offset, y + h + shadow_offset,
                fill=Colors.BLACK, stipple="gray50", outline="", tags="overlay"
            )
            self.canvas.create_rectangle(
                x, y, x + w, y + h,
                fill=color, stipple="gray50",
                outline=Colors.WHITE, width=2, tags="overlay"
            )
            self.canvas.create_text(
                x + w // 2, y + h // 2, text=label,
                fill="white", font=("Meiryo UI", 14, "bold"), tags="overlay"
            )
            # 進捗ゲージ
            if progress > 0:
                gw = w * progress
                self.canvas.create_rectangle(
                    x, y + h - 6, x + gw, y + h,
                    fill=Colors.SUCCESS, tags="overlay"
                )

    def _draw_result_overlay(self):
        """結果画面"""
        message_key = self._state_data.get("message", "")
        msg_params = self._state_data.get("message_params", {})
        message = self._resolve_text(message_key, **msg_params)
        # データがない場合はFalse
        is_error = self._state_data.get("is_error", False)
        countdown = self._state_data.get("countdown", 0)

        cx = self.main_width // 2
        cy = self.height // 2
        bg = "#cc0000" if is_error else "#004080"

        # メッセージ行数を計算してボックスの高さを調整
        lines = message.count('\n') + 1
        # カウントダウンも含める
        if countdown > 0:
            lines += 2  # カウントダウン用の空行とテキスト

        box_w = 560
        box_h = max(240, lines * 45 + 60)

        # 背景ボックス
        self.canvas.create_rectangle(
            cx - box_w // 2, cy - box_h // 2, cx + box_w // 2, cy + box_h // 2,
            fill=bg, stipple="gray50",
            outline=Colors.WHITE, width=3, tags="overlay"
        )

        # メッセージとカウントダウンをまとめて描画（中央揃え）
        display_text = message
        if countdown > 0:
            cd_text = self._resolve_text("msg.return_menu_countdown", **{"seconds": countdown})
            display_text += f"\n\n{cd_text}"

        self.canvas.create_text(
            cx, cy, text=display_text, fill="white",
            font=("Meiryo UI", 18, "bold"), justify=tk.CENTER, tags="overlay"
        )

    def _draw_exit_overlay(self):
        """終了画面 (お辞儀)"""
        cx = self.main_width // 2
        cy = self.height // 2

  # 背景 (黒)
        self.canvas.create_rectangle(
            0, 0, self.main_width, self.height,
            fill="black", tags="overlay"
        )

        # bow.png 表示
        if self.bow_image:
            # アスペクト比維持でリサイズ (高さの50%程度)
            target_h = int(self.height * 0.5)
            aspect = self.bow_image.width / self.bow_image.height
            target_w = int(target_h * aspect)

            resized = self.bow_image.resize(
                (target_w, target_h), Image.Resampling.LANCZOS
            )
            self._photo_bow = ImageTk.PhotoImage(resized)

            self.canvas.create_image(
                cx, cy, image=self._photo_bow, tags="overlay"
            )

        # テキスト (かぶらないように下部に配置)
        self.canvas.create_text(
            cx, self.height - 100,
            text=self._resolve_text("ui.thank_you"),
            fill="white", font=("Meiryo UI", 28, "bold"),
            justify=tk.CENTER, tags="overlay"
        )

    def _draw_credits(self):
        """クレジット表記 (常時表示)"""
        # 画面右下 (フッターの少し上、またはフッター内)
        x = self.main_width - 20
        y = self.height - 15

        self.canvas.create_text(
            x, y, text="Voice: ondoku3.com",
            fill="#888888", font=("Arial", 9),
            anchor="se", tags="overlay"
        )

    def _draw_language_modal_overlay(self):
        """ATM風言語選択モーダル (背景保持/グリッド/分離ボタン)"""
        # 背景を暗くする (パフォーマンスのためstippleは控えめに、あるいはソリッドで)
        # 以前のパフォーマンス修正に基づき、stippleを避けつつモーダル感を出す
        self.canvas.create_rectangle(
            0, 0, self.main_width, self.height,
            fill="#000000", stipple="gray25", tags="overlay"
        )

        languages = self._state_data.get("languages", [])
        selected_index = self._state_data.get("selected_index", 0)

        cx = self.main_width // 2
        cy = self.height // 2

        # 1. モーダル中央ボックス
        box_w, box_h = 760, 480
        self.canvas.create_rectangle(
            cx - box_w // 2, cy - box_h // 2,
            cx + box_w // 2, cy + box_h // 2,
            fill="#f0f0f0", outline="#333333", width=2, tags="overlay"
        )

        # 2. ヘッダータイトル (Localized)
        title_text = self._resolve_text("ui.select_language")
        self.canvas.create_text(
            cx, cy - box_h // 2 + 40,
            text=title_text, fill="#004080",
            font=("Meiryo UI", 24, "bold"), tags="overlay"
        )

        # 3. グリッド設定 (4列固定)
        cols = 4
        rows = (len(languages) + cols - 1) // cols

        btn_w, btn_h = 160, 80
        gap = 15

        grid_w = cols * btn_w + (cols - 1) * gap
        grid_h = rows * btn_h + (rows - 1) * gap

        start_x = cx - grid_w // 2
        start_y = cy - grid_h // 2 + 20

        modal_hit_areas = []

        # 4. 言語ボタンの描画
        for idx, lang in enumerate(languages):
            r = idx // cols
            c = idx % cols

            x1 = start_x + c * (btn_w + gap)
            y1 = start_y + r * (btn_h + gap)
            x2 = x1 + btn_w
            y2 = y1 + btn_h

            is_selected = (idx == selected_index)
            is_clicked = self._clicked_zone == (f"lang_select:{idx}", "modal")

            if is_selected:
                bg = "#0055aa"  # 選択中: 濃い青
                fg = "white"
                border = "#ffffff"
                width = 4
            else:
                bg = "#ffffff"  # 通常: 白
                fg = "#333333"
                border = "#cccccc"
                if is_clicked:
                    bg = "#dddddd"
                width = 1

            self.canvas.create_rectangle(
                x1, y1, x2, y2,
                fill=bg, outline=border, width=width, tags="overlay"
            )

            display_name = lang.get("display_name", lang["code"])
            self.canvas.create_text(
                (x1 + x2) // 2, (y1 + y2) // 2,
                text=display_name, fill=fg,
                font=("Meiryo UI", 14, "bold"), tags="overlay"
            )

            modal_hit_areas.append({
                "action": f"lang_select:{idx}",
                "x1": x1, "y1": y1, "x2": x2, "y2": y2
            })

        # 5. ガイドボタン (確定/戻る) - 視覚的に分かりやすく
        gz_l = self.guide_zones["left"]
        gz_r = self.guide_zones["right"]

        # Confirm (左)
        is_conf_clicked = self._clicked_zone == ("lang_confirm", "modal")
        self._draw_action_button(
            gz_l["x1"], gz_l["y1"], self._resolve_text("btn.lang_confirm"),
            "#005bb5", 1 if is_conf_clicked else 0
        )
        modal_hit_areas.append({
            "action": "lang_confirm",
            "x1": gz_l["x1"], "y1": gz_l["y1"],
            "x2": gz_l["x1"] + 150, "y2": gz_l["y1"] + 55
        })

        # Back (右)
        is_back_clicked = self._clicked_zone == ("lang_back", "modal")
        self._draw_action_button(
            gz_r["x1"] - 30, gz_r["y1"], self._resolve_text("btn.lang_back"),
            "#e67e22", 1 if is_back_clicked else 0
        )
        modal_hit_areas.append({
            "action": "lang_back",
            "x1": gz_r["x1"] - 30, "y1": gz_r["y1"],
            "x2": gz_r["x1"] + 120, "y2": gz_r["y1"] + 55
        })

        self._state_data["modal_hit_areas"] = modal_hit_areas

    def _draw_face_align_overlay(self):
        """顔位置合わせ画面 (中央配置を保証)"""
        face_result = self._state_data.get("face_result")

        cx = self.main_width // 2
        cy = self.height // 2

        # 表示用枠サイズ (キャンバスサイズから計算して中央固定を保証)
        v_ratio = self.config["face_guide"].get("visual_box_ratio", 0.4)
        v_size = int(self.height * v_ratio)
        vx = cx - v_size // 2
        vy = cy - v_size // 2

        status = "waiting"
        color = "#ffffff"
        width = 2

        if face_result:
            status = face_result[0]  # (status, visual_box, face_rect)
            if status == "detecting":
                color = "#ffff00"
                width = 4
            elif status == "confirmed":
                color = "#00ff00"
                width = 6

        # ガイド枠描画
        self.canvas.create_rectangle(
            vx, vy, vx + v_size, vy + v_size,
            outline=color, width=width, tags="overlay"
        )

        # ステータスごとの説明を表示 (ユーザー要望)
        msg_key = f"msg.face.{status}"
        text = self._resolve_text(msg_key)
        self.canvas.create_text(
            cx, vy + v_size + 40, text=text,
            fill="white", font=("Meiryo UI", 16, "bold"), tags="overlay"
        )

        # ガイド枠の描画
        self.canvas.create_rectangle(
            vx, vy, vx + v_size, vy + v_size,
            outline=color, width=width, tags="overlay"
        )

    def show_guidance(self, text, is_error=False):
        """ガイダンスメッセージを一時的に表示 (レート制限あり)"""
        import time
        now = time.time()
        # クールダウンを短縮 (2.0s -> 0.2s) し、連続したエラーでも表示されやすくする
        if now - self._last_guidance_time < 0.2:
            return

        self._guidance_text = text
        self._guidance_is_error = is_error
        self._last_guidance_time = now

        if self._guidance_timer:
            self.root.after_cancel(self._guidance_timer)

        self._guidance_timer = self.root.after(3000, self._clear_guidance)

    def _clear_guidance(self):
        self._guidance_text = ""
        self._guidance_is_error = False
        self._guidance_timer = None

    def _draw_guidance_overlay(self):
        """ガイダンスメッセージを最前面に描画 (動的リサイズ)"""
        text = self._resolve_text(self._guidance_text)

        # テキストの長さに基づいてボックスの幅を決定
        # 日本語: 1文字30px程度, 英語: 1文字15px程度
        # 安全を見て全角基準で多めに確保
        text_len = len(text)
        # フォントサイズに合わせて計算
        box_width = min(self.main_width - 60, max(450, text_len * 20 + 40))
        box_height = 70

        cx = self.main_width // 2
        cy = self.height - 130  # フッターの上あたり

        # 色設定
        if self._guidance_is_error:
            bg = Colors.GUIDANCE_ERROR_BG
            fg = Colors.GUIDANCE_ERROR_FG
            border = Colors.ERROR
        else:
            bg = Colors.GUIDANCE_BG
            fg = Colors.GUIDANCE_FG
            border = Colors.LIGHT_GRAY

        # 背景 (シンプルかつ高品質なボックス)
        self.canvas.create_rectangle(
            cx - box_width // 2, cy - box_height // 2, cx + box_width // 2, cy + box_height // 2,
            fill=bg, outline=border, width=1, tags="overlay"
        )

        # テキスト (落ち着いたフォントと色)
        self.canvas.create_text(
            cx, cy, text=f"{text}",
            fill=fg, font=("Meiryo UI", 20, "bold"), justify=tk.CENTER, tags="overlay"
        )

    def _draw_guides(self):
        """ガイドボタン描画 (進む/戻るボタンを実体化)"""
        guides = self._state_data.get("guides", {})
        current_dir = self._state_data.get("current_direction")
        progress = self._state_data.get("progress", 0)

        # 左ボタン (進む/はい)
        if "left" in guides:
            left_p = progress if current_dir == "left" else 0
            zone = self.guide_zones["left"]
            label = self._resolve_text(guides['left'])
            color = Colors.BUTTON["left"]["bg"]
            self._draw_guide_button("left", zone, label, color, left_p)

        # 右ボタン (戻る/いいえ)
        if "right" in guides:
            right_p = progress if current_dir == "right" else 0
            zone = self.guide_zones["right"]
            label = self._resolve_text(guides['right'])
            color = Colors.BUTTON["right"]["bg"]
            self._draw_guide_button("right", zone, label, color, right_p)

    def _draw_guide_button(self, zone_name, zone, text, color, progress=0):
        """ガイドボタン描画（押下エフェクト付き）"""
        x1, y1, x2, y2 = zone["x1"], zone["y1"], zone["x2"], zone["y2"]
        w = x2 - x1
        shadow_offset = 3  # ガイドボタンは小さいので影も小さく
        press_offset = 2

        # 押下状態の判定（進捗が0.3以上、またはマウスクリック中で押下とみなす）
        is_clicked = (self._clicked_zone is not None and
                      self._clicked_zone[0] == zone_name and
                      self._clicked_zone[1] == "guide")
        is_pressed = progress > 0.3 or is_clicked

        if is_pressed:
            # 押下時
            offset = press_offset
            self.canvas.create_rectangle(
                x1 + offset, y1 + offset, x2 + offset, y2 + offset,
                fill=color, stipple="gray50",
                outline=Colors.WHITE, width=2, tags="overlay"
            )
            self.canvas.create_text(
                (x1 + x2) // 2 + offset, (y1 + y2) // 2 + offset, text=text,
                fill="white", font=("Meiryo UI", 12, "bold"), tags="overlay"
            )
            if progress > 0:
                gw = w * progress
                self.canvas.create_rectangle(
                    x1 + offset, y2 - 5 + offset,
                    x1 + gw + offset, y2 + offset,
                    fill=Colors.SUCCESS, tags="overlay"
                )
        else:
            # 通常時: 影を描画
            self.canvas.create_rectangle(
                x1 + shadow_offset, y1 + shadow_offset,
                x2 + shadow_offset, y2 + shadow_offset,
                fill="#000000", stipple="gray50", outline="", tags="overlay"
            )
            self.canvas.create_rectangle(
                x1, y1, x2, y2, fill=color, stipple="gray50",
                outline=Colors.WHITE, width=2, tags="overlay"
            )
            self.canvas.create_text(
                (x1 + x2) // 2, (y1 + y2) // 2, text=text,
                fill="white", font=("Meiryo UI", 12, "bold"), tags="overlay"
            )
            if progress > 0:
                gw = w * progress
                self.canvas.create_rectangle(
                    x1, y2 - 5, x1 + gw, y2,
                    fill=Colors.SUCCESS, tags="overlay"
                )

    def _draw_text_fit(self, x, y, text, font_family, max_size, max_width, fill, **kwargs):
        """指定幅に収まるようにフォントサイズを縮小して描画"""
        size = max_size
        font = (font_family, size, "bold")

        # 簡易計測 (厳密な計測にはtk.Fontが必要だが、ここではCanvasで試行は重いのでループ制限)
        # PillowのImageFontを使う手もあるが、依存を増やしたくないため
        # 文字数ベースのヒューリスティック + 減衰で対応

        # キャンバスの一時テキストで幅計測
        temp_tag = "_temp_text_measure"
        self.canvas.create_text(x, y, text=text, font=font, tags=temp_tag)
        bbox = self.canvas.bbox(temp_tag)
        self.canvas.delete(temp_tag)

        if bbox:
            curr_width = bbox[2] - bbox[0]

            # 幅が超えていれば縮小
            while curr_width > max_width and size > 8:
                size -= 2
                font = (font_family, size, "bold")
                self.canvas.create_text(x, y, text=text, font=font, tags=temp_tag)
                bbox = self.canvas.bbox(temp_tag)
                self.canvas.delete(temp_tag)
                if bbox:
                    curr_width = bbox[2] - bbox[0]
                else:
                    break

        # 描画
        self.canvas.create_text(
            x, y, text=text, fill=fill,
            font=(font_family, size, "bold"), tags="overlay", **kwargs
        )

    def _draw_input_visual(self, label, input_text, char_count=4, is_password=True, unit="", align_right=False, override_cy=None):
        """入力可視化パーツ (相対レイアウト計算・動的リサイズ)"""
        cx = self.main_width // 2
        # Rule 3: Math-based centering
        cy = override_cy if override_cy is not None else (self.height // 2)

        # 1. レイアウト定数 (相対計算の基準)
        max_total_width = self.main_width * 0.8
        # box_size は文字数に応じて可変だが最大値を制限
        box_size = min(70, int(max_total_width / (char_count + (char_count - 1) * 0.2)))
        padding = int(box_size * 0.2)
        total_width = (box_size + padding) * char_count - padding

        # 垂直位置の計算 (全体を中央付近に配置)
        # ラベル(約30px) + 余白(box_size*0.4) + ボックス(box_size)
        label_box_gap = int(box_size * 0.5)
        total_group_h = 30 + label_box_gap + box_size

        # グループ全体の開始Y (ラベル位置)
        label_y = cy - (total_group_h // 2) + 15
        start_y = label_y + label_box_gap + 15
        start_x = cx - total_width // 2

        # 2. 背景ボックス (Relative padding)
        bg_padx = int(box_size * 0.5)
        bg_pady = int(box_size * 0.6)
        box_bg_w = total_width + bg_padx * 2

        # Rule 4: Track bottom for Keep-Out math
        self.last_input_bottom = start_y + box_size + bg_pady // 2

        self.canvas.create_rectangle(
            cx - box_bg_w // 2, label_y - bg_pady,
            cx + box_bg_w // 2, self.last_input_bottom,
            fill="white", stipple="gray50", outline="#cccccc", width=1, tags="overlay"
        )

        # 3. 入力ボックス描画
        input_len = len(input_text)
        for i in range(char_count):
            bx = start_x + i * (box_size + padding)
            val = ""
            bg = "white"

            if align_right:
                val_idx = i - (char_count - input_len)
                if 0 <= val_idx < input_len:
                    val = input_text[val_idx] if not is_password else "●"
                if i == char_count - 1 and input_len < char_count:
                    bg = "#f0f9ff"
            else:
                if i < input_len:
                    val = input_text[i] if not is_password else "●"
                elif i == input_len:
                    bg = "#f0f9ff"

            self.canvas.create_rectangle(
                bx, start_y, bx + box_size, start_y + box_size,
                fill=bg, outline="#666666", width=2, tags="overlay"
            )

            if val:
                # 文字サイズもボックスに比例
                font_size = int(box_size * 0.5)
                self.canvas.create_text(
                    bx + box_size // 2, start_y + box_size // 2,
                    text=val, fill="black", font=("Arial", font_size, "bold"),
                    tags="overlay"
                )

        # 4. ラベル (見出し) - Dynamic Fitting
        if label:
            text = self._resolve_text(label)
            # フォントサイズを16に下げて視覚的な重さを軽減 (max 16)
            self._draw_text_fit(
                cx, label_y, text, "Meiryo UI", 16, max_total_width - 40, "#333333"
            )

        # 5. 単位 (Relative to boxes)
        if unit:
            u_text = self._resolve_text(unit)
            self.canvas.create_text(
                cx + total_width // 2 + 20, start_y + box_size // 2,
                text=u_text, fill="#333333", font=("Meiryo UI", 16, "bold"),
                anchor="w", tags="overlay"
            )

    # ===== 後方互換性 =====

    def set_header(self, text):
        self._state_data["header"] = text

    def clear_content(self):
        self._state_data = {}
        self.canvas.delete("overlay")

    def show_main_menu(self):
        pass

    def show_message(self, text, visible=True):
        if visible:
            self._state_data["message"] = text

    def update_background(self, frame, face_result=None):
        if face_result:
            self._state_data["face_result"] = face_result
        self.render_frame(frame, self._state_data)

    def destroy(self):
        try:
            self.canvas.destroy()
        except Exception:
            pass
