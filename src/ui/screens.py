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
from src.ui.styles import Colors, Fonts, Layout as StyleLayout


class Layout:
    """レイアウト定数"""
    HEADER_HEIGHT = 80
    FOOTER_HEIGHT = 80
    DEBUG_PANEL_WIDTH = 200


class ATMUI:
    def __init__(self, root, config):
        self.root = root
        self.config = config

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

        # レイアウト計算
        self._calculate_layout()

        self._state_data = {}

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
            self._calculate_layout()

    def set_click_callback(self, callback):
        self._click_callback = callback

    def _on_click(self, event):
        if self._click_callback is None:
            return

        x, y = event.x, event.y

        # メインエリア外は無視
        if x > self.main_width:
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
                if callback is not None:
                    callback(clicked_zone)

            self._click_feedback_timer = self.root.after(150, execute_callback)

    def render_frame(self, frame, state_data: dict = None):
        if state_data:
            self._state_data = state_data

        # 背景クリア
        self.canvas.delete("all")

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
        self._draw_mode_content(mode)

    def _draw_camera_background(self, frame):
        """カメラ映像をメインエリアに全画面で描画"""
        if frame is None:
            return

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)

        # メインエリア全体に引き伸ばし（アスペクト比無視）
        img = img.resize(
            (self.main_width, self.main_height),
            Image.Resampling.LANCZOS
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
                text=f"信頼度: {confidence*100:.1f}%",
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
                x + w // 2, y_pos + 9, text=f"{progress*100:.0f}%",
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

    def _draw_header(self, text):
        """ヘッダー描画"""
        self.canvas.create_rectangle(
            0, 0, self.main_width, Layout.HEADER_HEIGHT,
            fill="#004080", stipple="gray50", tags="overlay"
        )
        self.canvas.create_text(
            self.main_width // 2, Layout.HEADER_HEIGHT // 2,
            text=text, fill="white",
            font=("Meiryo UI", 28, "bold"), tags="overlay"
        )
        self.canvas.create_text(
            self.main_width - 60, 40, text="ESC: 終了",
            fill="#cccccc", font=("Meiryo UI", 10), tags="overlay"
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
        label = btn_data.get("label", "")

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
                fill=pressed_bg, stipple="gray50", outline="#ffffff", width=2, tags="overlay"
            )
            cx, cy = (bx1 + bx2) // 2 + offset, (by1 + by2) // 2 + offset
        else:
            # 通常時: 影を描画してからボタンを描画
            self.canvas.create_rectangle(
                bx1 + shadow_offset, by1 + shadow_offset,
                bx2 + shadow_offset, by2 + shadow_offset,
                fill="#000000", stipple="gray50", outline="", tags="overlay"
            )
            self.canvas.create_rectangle(
                bx1, by1, bx2, by2,
                fill=bg, stipple="gray50", outline="#ffffff", width=2, tags="overlay"
            )
            cx, cy = (bx1 + bx2) // 2, (by1 + by2) // 2

        # ラベル
        self.canvas.create_text(
            cx, cy - 10, text=label, fill=fg,
            font=Fonts.button(), tags="overlay"
        )

        # 操作説明
        self.canvas.create_text(
            cx, cy + 35, text="クリック / ジェスチャー",
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
        """入力画面"""
        message = self._state_data.get("message", "")
        input_value = self._state_data.get("input_value", "")
        max_digits = self._state_data.get("input_max", 6)
        unit = self._state_data.get("input_unit", "")
        align_right = self._state_data.get("align_right", False)

        cx = self.main_width // 2
        cy = self.height // 2
        box_w = max_digits * 45 + 80

        # 背景ボックス
        self.canvas.create_rectangle(
            cx - box_w // 2, cy - 80, cx + box_w // 2, cy + 80,
            fill="#ffffff", stipple="gray50",
            outline="#cccccc", width=2, tags="overlay"
        )

        # メッセージ
        self.canvas.create_text(
            cx, cy - 50, text=message,
            fill="#333333", font=("Meiryo UI", 16), tags="overlay"
        )

        # 入力ボックス
        start_x = cx - (max_digits * 45) // 2
        input_len = len(input_value)

        for i in range(max_digits):
            bx = start_x + i * 45
            val = ""
            bg = "#ffffff"

            if align_right:
                val_idx = i - (max_digits - input_len)
                if 0 <= val_idx < input_len:
                    val = input_value[val_idx]
                # キャレットは常に右端
                if i == max_digits - 1 and input_len < max_digits:
                    bg = "#e0f7fa"
            else:
                if i < input_len:
                    val = input_value[i]
                elif i == input_len:
                    bg = "#e0f7fa"

            self.canvas.create_rectangle(
                bx, cy - 20, bx + 38, cy + 20,
                fill=bg, outline="#999999", width=2, tags="overlay"
            )
            self.canvas.create_text(
                bx + 19, cy, text=val,
                fill="#333333", font=("Arial", 24, "bold"), tags="overlay"
            )

        # 単位
        if unit:
            self.canvas.create_text(
                start_x + max_digits * 45 + 20, cy, text=unit,
                fill="#333333", font=("Meiryo UI", 20, "bold"), tags="overlay"
            )

        self._draw_guides()

    def _draw_pin_input_overlay(self):
        """暗証番号入力画面"""
        message = self._state_data.get("message", "")
        input_value = self._state_data.get("input_value", "")
        keypad_layout = self._state_data.get("keypad_layout", [])

        cx = self.main_width // 2
        cy = self.height // 2

        # メッセージ
        self.canvas.create_text(
            cx, cy - 180, text=message,
            fill="white", font=("Meiryo UI", 16, "bold"), tags="overlay"
        )

        # PIN入力欄
        for i in range(4):
            bx = cx - 90 + i * 45
            by = cy - 145
            val = "*" if i < len(input_value) else ""
            bg = "#e0f7fa" if i == len(input_value) else "#ffffff"

            self.canvas.create_rectangle(
                bx, by, bx + 38, by + 45,
                fill=bg, outline="#999999", width=2, tags="overlay"
            )
            self.canvas.create_text(
                bx + 19, by + 22, text=val,
                fill="#333333", font=("Arial", 24, "bold"), tags="overlay"
            )

        # キーパッドグリッド
        if keypad_layout:
            gx = cx - 110
            gy = cy - 70
            cw, ch = 75, 55

            for row_idx, row in enumerate(keypad_layout):
                for col_idx, item in enumerate(row):
                    if item is None:
                        continue

                    kx = gx + col_idx * cw
                    ky = gy + row_idx * ch
                    key = item.get("key", "")
                    num = item.get("num", "")

                    self.canvas.create_rectangle(
                        kx, ky, kx + cw - 5, ky + ch - 5,
                        fill="#ffffff", outline="#444444",
                        width=2, tags="overlay"
                    )
                    self.canvas.create_text(
                        kx + (cw - 5) // 2, ky + 18,
                        text=num, fill="#333333",
                        font=("Arial", 20, "bold"), tags="overlay"
                    )
                    self.canvas.create_text(
                        kx + (cw - 5) // 2, ky + ch - 12,
                        text=f"[{key.upper()}]", fill="#888888",
                        font=("Arial", 9), tags="overlay"
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
        self.canvas.create_text(
            cx, cy, text=message, fill="#333333",
            font=("Meiryo UI", 18), tags="overlay"
        )

        # はい/いいえボタン
        left_p = progress if current_dir == "left" else 0
        self._draw_action_button(80, self.height - 90, "はい 👈", "#005bb5", left_p)

        right_p = progress if current_dir == "right" else 0
        self._draw_action_button(
            self.main_width - 230, self.height - 90,
            "いいえ 👉", "#e67e22", right_p
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
                outline="#ffffff", width=2, tags="overlay"
            )
            self.canvas.create_text(
                x + w // 2 + offset, y + h // 2 + offset, text=label,
                fill="white", font=("Meiryo UI", 14, "bold"), tags="overlay"
            )
            # 進捗ゲージ
            if progress > 0:
                gw = w * progress
                self.canvas.create_rectangle(
                    x + offset, y + h - 6 + offset, x + gw + offset, y + h + offset,
                    fill=Colors.SUCCESS, tags="overlay"
                )
        else:
            # 通常時: 影を描画
            self.canvas.create_rectangle(
                x + shadow_offset, y + shadow_offset,
                x + w + shadow_offset, y + h + shadow_offset,
                fill="#000000", stipple="gray50", outline="", tags="overlay"
            )
            self.canvas.create_rectangle(
                x, y, x + w, y + h,
                fill=color, stipple="gray50",
                outline="#ffffff", width=2, tags="overlay"
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
        message = self._state_data.get("message", "")
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
            outline="#ffffff", width=3, tags="overlay"
        )

        # メッセージとカウントダウンをまとめて描画（中央揃え）
        display_text = message
        if countdown > 0:
            display_text += f"\n\nメニューへ戻る: {countdown}秒"

        self.canvas.create_text(
            cx, cy, text=display_text, fill="white",
            font=("Meiryo UI", 18, "bold"), justify=tk.CENTER, tags="overlay"
        )

    def _draw_face_align_overlay(self):
        """顔位置合わせ画面"""
        face_result = self._state_data.get("face_result")

        cx = self.main_width // 2
        cy = self.height // 2
        box_size = min(self.main_width, self.height) // 2

        status = "waiting"
        color = "#ffffff"
        width = 2

        if face_result:
            status = face_result[0]
            if status == "detecting":
                color = "#ffff00"
                width = 4
            elif status == "confirmed":
                color = "#00ff00"
                width = 6

        self.canvas.create_rectangle(
            cx - box_size // 2, cy - box_size // 2,
            cx + box_size // 2, cy + box_size // 2,
            outline=color, width=width, tags="overlay"
        )

        msg = ""
        if status == "waiting":
            msg = "顔を枠の中に合わせてください"
        elif status == "detecting":
            msg = "認識中..."

        if msg:
            self.canvas.create_text(
                cx, cy + box_size // 2 + 35, text=msg,
                fill=color, font=("Meiryo UI", 20, "bold"), tags="overlay"
            )

    def _draw_guides(self):
        """ガイドボタン描画"""
        guides = self._state_data.get("guides", {})
        current_dir = self._state_data.get("current_direction")
        progress = self._state_data.get("progress", 0)

        if "left" in guides:
            left_p = progress if current_dir == "left" else 0
            zone = self.guide_zones["left"]
            self._draw_guide_button("left", zone, f"👈 {guides['left']}", "#005bb5", left_p)

        if "right" in guides:
            right_p = progress if current_dir == "right" else 0
            zone = self.guide_zones["right"]
            self._draw_guide_button("right", zone, f"{guides['right']} 👉", "#e67e22", right_p)

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
                outline="#ffffff", width=2, tags="overlay"
            )
            self.canvas.create_text(
                (x1 + x2) // 2 + offset, (y1 + y2) // 2 + offset, text=text,
                fill="white", font=("Meiryo UI", 12, "bold"), tags="overlay"
            )
            if progress > 0:
                gw = w * progress
                self.canvas.create_rectangle(
                    x1 + offset, y2 - 5 + offset, x1 + gw + offset, y2 + offset,
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
                outline="#ffffff", width=2, tags="overlay"
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
