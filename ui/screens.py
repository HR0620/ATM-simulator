import tkinter as tk
from tkinter import font
from PIL import Image, ImageTk
import cv2


class FaceGuideScreen(tk.Frame):
    """
    顔認証ガイド画面。
    カメラ映像を表示し、顔の位置合わせを指示する。
    """

    def __init__(self, master, config):
        super().__init__(master)
        self.config = config
        self.pack(fill=tk.BOTH, expand=True)

        # 背景は黒で没入感を出す
        self.canvas = tk.Canvas(self, bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # 画面中央の指示テキスト
        # 日本語フォントは環境依存があるため、デフォルトのHelveticaやsans-serifを使う
        # Windowsなら "Meiryo" UI などが使える場合もあるが、安全策で汎用フォント指定
        self.instruction_label = tk.Label(
            self,
            text="起動中...",
            font=("Helvetica", 24, "bold"),
            bg="black",
            fg="white"
        )
        self.instruction_label.place(relx=0.5, rely=0.1, anchor="center")

        self.colors = self.config["face_guide"]["colors"]

    def update_image(self, frame, status, guide_box, face_rect):
        """
        フレームと状態を受け取り、画面を描画更新する。
        """
        # OpenCV (BGR) -> PIL (RGB) -> Tkinter Image
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_frame)
        tk_image = ImageTk.PhotoImage(image=pil_image)

        # ガベージコレクション対策
        self.canvas.image = tk_image

        # 画像をキャンバス中央に配置
        canvas_width = self.winfo_width()
        canvas_height = self.winfo_height()
        # ウィンドウ初期化直後はサイズが1になってしまう対策
        if canvas_width <= 1:
            canvas_width = self.config["ui"]["window_width"]
        if canvas_height <= 1:
            canvas_height = self.config["ui"]["window_height"]

        x = (canvas_width - tk_image.width()) // 2
        y = (canvas_height - tk_image.height()) // 2

        self.canvas.create_image(x, y, image=tk_image, anchor="nw")

        # --- ガイド枠とテキストの描画 ---
        gx, gy, gw, gh = guide_box
        # 画像のオフセットを加算して描画位置を合わせる
        gx += x
        gy += y

        box_color = self.colors["waiting"]
        instruction_text = "枠に合わせてください"

        if status == "detecting":
            box_color = self.colors["detecting"]
            instruction_text = "そのままお待ちください..."
        elif status == "confirmed":
            box_color = self.colors["confirmed"]
            instruction_text = "認証完了！"

        # ガイド枠
        self.canvas.create_rectangle(gx, gy, gx + gw, gy + gh, outline=box_color, width=3)
        # ラベル更新
        self.instruction_label.config(text=instruction_text, fg=box_color)

        # 顔検出デバッグ枠（オプション）
        if face_rect is not None:
            fx, fy, fw, fh = face_rect
            fx += x
            fy += y
            self.canvas.create_rectangle(fx, fy, fx + fw, fy + fh, outline="blue", width=1)


class ATMUI(tk.Frame):
    """
    ATM操作画面。
    ジェスチャーでボタンを選択する。
    """

    def __init__(self, master, config):
        super().__init__(master)
        self.config = config
        self.pack(fill=tk.BOTH, expand=True)

        bg_color = self.config["atm"]["colors"]["default_bg"]
        self.configure(bg=bg_color)

        # タイトル
        self.title_label = tk.Label(
            self,
            text="いらっしゃいませ",
            font=("Helvetica", 32, "bold"),
            bg=bg_color
        )
        self.title_label.pack(pady=50)

        # ボタンコンテナ
        self.button_frame = tk.Frame(self, bg=bg_color)
        self.button_frame.pack(fill=tk.X, expand=True, padx=50, pady=50)

        self.buttons = {}
        # configのボタン定義をロード
        btn_data = self.config["atm"]["buttons"]
        # 左・中・右の順序を保証するためのリスト
        order = ["left", "center", "right"]

        for name in order:
            if name not in btn_data:
                continue

            text = btn_data[name]
            lbl = tk.Label(
                self.button_frame,
                text=text,
                font=("Helvetica", 24),
                width=10,
                height=3,
                relief="raised",
                bg="white"
            )
            lbl.pack(side=tk.LEFT, expand=True, padx=20)
            self.buttons[name] = lbl

        # ステータス表示
        self.status_label = tk.Label(
            self,
            text="ジェスチャー待ち...",
            font=("Helvetica", 18),
            bg=bg_color,
            fg="#555"
        )
        self.status_label.pack(side=tk.BOTTOM, pady=20)

        # カメラプレビュー（画面右下）
        self.camera_canvas = tk.Canvas(self, width=160, height=120, bg="black")
        self.camera_canvas.place(relx=1.0, rely=1.0, x=-10, y=-10, anchor="se")

    def update_state(self, gesture, frame):
        """
        ジェスチャーに応じてボタンのハイライトを切り替える。
        """
        # カメラプレビュー更新
        if frame is not None:
            small_frame = cv2.resize(frame, (160, 120))
            rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_frame)
            tk_image = ImageTk.PhotoImage(image=pil_image)

            self.camera_canvas.image = tk_image
            self.camera_canvas.create_image(0, 0, image=tk_image, anchor="nw")

        # ボタンのハイライト処理
        highlight_color = self.config["atm"]["colors"]["highlight_bg"]
        free_class = self.config["gesture"]["free_class_name"]

        for name, btn in self.buttons.items():
            if name == gesture:
                # 選択されているボタン
                btn.config(bg=highlight_color, fg="white", relief="sunken")
            else:
                # 選択されていないボタン
                btn.config(bg="white", fg="black", relief="raised")

        # テキスト更新
        if gesture == free_class:
            self.status_label.config(text="操作待ち...", fg="#555")
        else:
            # 視覚的フィードバック
            display_text = self.config["atm"]["buttons"].get(gesture, gesture)
            self.status_label.config(text=f"選択中: {display_text}", fg=highlight_color)
