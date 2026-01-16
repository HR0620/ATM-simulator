import tkinter as tk
from PIL import Image, ImageTk
import cv2


class ATMUI:
    """
    ATMの汎用画面クラス (ATMスタイル UI)
    - UIが主役、カメラは右上にPIP表示 (操作ボタンを隠さないため)
    - メインメニューは 3カラム (左: 振込, 中: 引出, 右: 口座作成)
    """

    def __init__(self, root, config):
        self.root = root
        self.config = config

        # 全体背景
        self.root.configure(bg="#e0e0e0")

        # --- メインコンテナ ---
        self.main_frame = tk.Frame(self.root, bg="#f0f0f0")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. ヘッダーエリア
        self.header_frame = tk.Frame(self.main_frame, bg="#004080", height=80)
        self.header_frame.pack(fill=tk.X, side=tk.TOP)

        self.header_label = tk.Label(self.header_frame, text="メインメニュー", font=(
            "Meiryo UI", 28, "bold"), bg="#004080", fg="white")
        self.header_label.pack(side=tk.LEFT, padx=30, pady=15)

        # "ESC: 終了" ラベル (ヘッダー右)
        self.esc_label = tk.Label(self.header_frame, text="ESC: 終了", font=("Meiryo UI", 12), bg="#004080", fg="#cccccc")
        self.esc_label.pack(side=tk.RIGHT, padx=20)

        # 2. コンテンツエリア
        self.content_frame = tk.Frame(self.main_frame, bg="#f0f0f0")
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # A. メッセージ表示
        self.message_label = tk.Label(self.content_frame, text="", font=(
            "Meiryo UI", 24), bg="#f0f0f0", fg="#333", justify=tk.CENTER)

        # B. 入力フィールド (桁区切り表示)
        self.input_container = tk.Frame(self.content_frame, bg="#f0f0f0")
        self.digit_labels = []  # List of Label widgets for digits

        # C. 3カラムメニュー (ボタンエリア)
        self.menu_grid_frame = tk.Frame(self.content_frame, bg="#f0f0f0")

        # 左ボタン (振込)
        self.btn_left = tk.Frame(self.menu_grid_frame, bg="#005bb5", bd=5, relief="raised")
        self.lbl_left_title = tk.Label(self.btn_left, text="振込", font=(
            "Meiryo UI", 32, "bold"), bg="#005bb5", fg="white")

        # 中央ボタン (引き出し)
        self.btn_center = tk.Frame(self.menu_grid_frame, bg="#f5f5f5", bd=5, relief="raised")
        self.lbl_center_title = tk.Label(self.btn_center, text="引き出し", font=(
            "Meiryo UI", 32, "bold"), bg="#f5f5f5", fg="#333")

        # 右ボタン (口座作成)
        self.btn_right = tk.Frame(self.menu_grid_frame, bg="#e67e22", bd=5, relief="raised")
        self.lbl_right_title = tk.Label(self.btn_right, text="口座作成", font=(
            "Meiryo UI", 32, "bold"), bg="#e67e22", fg="white")

        # D. キーパッド
        self.keypad_frame = tk.Frame(self.main_frame, bg="#cfcfcf", bd=3, relief="groove")

        # E. 汎用ガイド (Yes/No 等)
        self.guide_frame = tk.Frame(self.main_frame, bg="#f0f0f0", height=80)

        self.left_guide_container = tk.Frame(self.guide_frame, bg="#005bb5", padx=20, pady=10, relief="raised", bd=3)
        self.left_guide_lbl = tk.Label(self.left_guide_container, text="", font=(
            "Meiryo UI", 20, "bold"), bg="#005bb5", fg="white")
        self.left_guide_lbl.pack()

        self.right_guide_container = tk.Frame(self.guide_frame, bg="#e67e22", padx=20, pady=10, relief="raised", bd=3)
        self.right_guide_lbl = tk.Label(self.right_guide_container, text="", font=(
            "Meiryo UI", 20, "bold"), bg="#e67e22", fg="white")
        self.right_guide_lbl.pack()

        # 3. カメラ映像エリア (PIP) - 右上に配置
        # ヘッダーの下、右端に寄せる
        self.camera_frame = tk.Frame(self.root, bg="black", bd=2, relief="solid")
        # placeはroot基準
        self.camera_frame.place(relx=0.98, rely=0.12, anchor=tk.NE, width=280, height=210)

        self.camera_label = tk.Label(self.camera_frame, text="Security Camera",
                                     font=("Arial", 8), fg="white", bg="black")
        self.camera_label.pack(side=tk.TOP, fill=tk.X)

        self.canvas = tk.Canvas(self.camera_frame, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Face Guide Overlay (Canvas上のタグ管理)
        self.guide_rect_id = None
        self.face_rect_id = None

    def update_background(self, frame, face_result=None):
        """
        カメラ映像を右上のPIPエリアに描画
        face_result: (status, guide_box, face_rect) from FacePositionChecker
        """
        if frame is None:
            return

        # BGR -> RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(frame_rgb)

        # Canvasサイズに合わせてリサイズ
        cw = 280
        ch = 210

        # 比率を維持しつつリサイズするか、単純にリサイズするか
        # ここでは単純リサイズ (OpenCV側で既にアスペクト比考慮されている前提なら)
        pil_image = pil_image.resize((cw, ch), Image.Resampling.LANCZOS)

        self.photo = ImageTk.PhotoImage(image=pil_image)
        self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)

        # ガイド枠描画
        self.canvas.delete("guide")  # 前のフレームの描画を消す

        if face_result:
            status, guide_box, face_rect = face_result

            # guide_box scaling
            # guide_box は元の frame 解像度 (例: 640x480) 基準
            # これを (cw, ch) に変換する必要がある
            orig_h, orig_w = frame.shape[:2]
            scale_x = cw / orig_w
            scale_y = ch / orig_h

            gx, gy, gw, gh = guide_box
            cx1 = gx * scale_x
            cy1 = gy * scale_y
            cx2 = (gx + gw) * scale_x
            cy2 = (gy + gh) * scale_y

            color = "white"
            width = 2
            if status == "detecting":
                color = "yellow"
                width = 3
            elif status == "confirmed":
                color = "#00ff00"
                width = 5

            self.canvas.create_rectangle(cx1, cy1, cx2, cy2, outline=color, width=width, tags="guide")

            if status == "waiting":
                # ガイドテキスト
                self.canvas.create_text(cw / 2, ch / 2, text="顔を枠に合わせてください", fill="white",
                                        font=("Meiryo UI", 10, "bold"), tags="guide")

    def set_header(self, text):
        self.header_label.config(text=text)

    def clear_content(self):
        """コンテンツエリアをリセット"""
        self.message_label.pack_forget()
        self.input_container.pack_forget()
        self.menu_grid_frame.pack_forget()
        self.keypad_frame.place_forget()
        self.guide_frame.pack_forget()
        # Input digits reset
        for w in self.input_container.winfo_children():
            w.destroy()

    def show_main_menu(self):
        """3カラムのメインメニューを表示"""
        self.clear_content()
        self.set_header("メインメニュー")

        self.menu_grid_frame.pack(fill=tk.BOTH, expand=True, padx=50, pady=50)

        # Grid構成 (1行3列)
        self.menu_grid_frame.columnconfigure(0, weight=1)
        self.menu_grid_frame.columnconfigure(1, weight=1)
        self.menu_grid_frame.columnconfigure(2, weight=1)
        self.menu_grid_frame.rowconfigure(0, weight=1)

        # 左ボタン
        self.btn_left.grid(row=0, column=0, sticky="nsew", padx=20)
        self.lbl_left_title.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # 中央ボタン
        self.btn_center.grid(row=0, column=1, sticky="nsew", padx=20)
        self.lbl_center_title.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # 右ボタン
        self.btn_right.grid(row=0, column=2, sticky="nsew", padx=20)
        self.lbl_right_title.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    def show_message(self, text, visible=True):
        if visible:
            self.message_label.config(text=text)
            self.message_label.pack(pady=40, anchor=tk.CENTER)
        else:
            self.message_label.pack_forget()

    def show_fixed_input_field(self, current_text, max_digits=4, is_pin=False, unit_text=""):
        """
        固定枠による入力フィールド表示
        [ 1 ] [ 2 ] [ _ ] [ ]  円
        """
        self.input_container.pack(pady=40)

        # 再描画 (効率化のためDiff更新したいが、簡易実装として全再生成)
        for w in self.input_container.winfo_children():
            w.destroy()

        # 枠コンテナ (中央寄せ)
        box_frame = tk.Frame(self.input_container, bg="#f0f0f0")
        box_frame.pack()

        # 枠生成
        for i in range(max_digits):
            val = ""
            bg_color = "white"

            if i < len(current_text):
                val = "*" if is_pin else current_text[i]
            elif i == len(current_text):
                # キャレット位置（まだ入力していないが次はここ）
                # キャレットを表示するか、あるいは空枠を目立たせるか
                bg_color = "#e0f7fa"  # 薄い水色でフォーカス表現

            lbl = tk.Label(box_frame, text=val, font=("Arial", 36, "bold"),
                           bg=bg_color, relief="solid", bd=1, width=2, height=1)
            lbl.pack(side=tk.LEFT, padx=5)

        # 単位 (枠外)
        if unit_text:
            unit_lbl = tk.Label(box_frame, text=unit_text, font=("Meiryo UI", 24, "bold"), bg="#f0f0f0")
            unit_lbl.pack(side=tk.LEFT, padx=10, anchor=tk.S)

    def show_name_input_field(self, current_text):
        """名前入力用のフリーテキスト風フィールド"""
        self.input_container.pack(pady=40)
        for w in self.input_container.winfo_children():
            w.destroy()

        lbl = tk.Label(self.input_container, text=current_text + "_", font=("Meiryo UI", 32),
                       bg="white", relief="sunken", bd=2, width=20)
        lbl.pack()

    def show_selection_guides(self, left_text=None, right_text=None, center_text=None):
        """画面下部にガイドを表示"""
        self.guide_frame.pack_forget()
        self.left_guide_container.pack_forget()
        self.right_guide_container.pack_forget()

        has_guide = False
        if left_text:
            self.left_guide_lbl.config(text=f"👈 {left_text}")
            self.left_guide_container.pack(side=tk.LEFT, padx=50, pady=20)
            has_guide = True

        if right_text:
            self.right_guide_lbl.config(text=f"{right_text} 👉")
            self.right_guide_container.pack(side=tk.RIGHT, padx=50, pady=20)
            has_guide = True

        if has_guide:
            self.guide_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=20)

    def show_keypad(self, layout_data, visible=True):
        """ランダムキーパッド表示"""
        if not visible:
            self.keypad_frame.place_forget()
            return

        # 画面中央下寄りに配置
        self.keypad_frame.place(relx=0.5, rely=0.6, anchor=tk.CENTER)

        # Gridリセット
        for w in self.keypad_frame.winfo_children():
            w.destroy()

        for r, row in enumerate(layout_data):
            for c, item in enumerate(row):
                if item:
                    text = f"[{item['key'].upper()}]\n{item['num']}"
                    lbl = tk.Label(self.keypad_frame, text=text, font=("Consolas", 18, "bold"),
                                   width=6, height=2, bg="white", relief="raised", bd=2)
                    lbl.grid(row=r, column=c, padx=4, pady=4)

    def destroy(self):
        try:
            self.main_frame.destroy()
            self.camera_frame.destroy()
        except:
            pass
