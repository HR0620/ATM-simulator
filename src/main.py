# -*- coding: utf-8 -*-
"""
AI非接触ATMシミュレーター - メインエントリーポイント

このファイルはアプリケーションの起動処理を担当します。
依存関係のチェックを行い、問題があれば分かりやすいエラーメッセージを表示します。
"""

import sys
import os
import time
import tkinter as tk
from tkinter import ttk, messagebox
# import time
# from threading import Thread
from PIL import Image, ImageTk
from src.paths import get_resource_path

# ステータスメッセージの定義
LOADING_STATUS = {
    "INIT": "システムを初期化中...",
    "DEPS": "依存関係をチェック中...",
    "AI": "AIエンジンを起動中 (これには時間がかかります)...",
    "CORE": "コアコンポーネントをロード中...",
    "DONE": "準備完了！",
}

# エラーヒントの定義
ERROR_HINTS = {
    "AVX": "このCPUはAVX命令セットをサポートしていない可能性があります。より新しいPCで試してください。",
    "DLL": "必須のシステムコンポーネント(DLL)が不足しています。MSVC再配布可能パッケージをインストールしてください。",
    "MODEL": "AIモデルファイルが見つかりません。resources/model フォルダを確認してください。",
    "GENERIC": "不明なエラーが発生しました。ログを確認するか、開発者に問い合わせてください。"
}

# EXE実行時のCWD設定のみ行う（リソース参照のため）
if getattr(sys, 'frozen', False):
    base_path = os.path.dirname(sys.executable)
    os.chdir(base_path)


class SplashScreen:
    """
    起動時のスプラッシュ画面を表示するクラス
    """

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ATM Simulator Loading")

        # ウィンドウ枠を消す
        self.root.overrideredirect(True)

        # 画面中央に配置
        width, height = 400, 300
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

        # 背景色
        self.root.configure(bg='#2c3e50')

        # タイトル
        tk.Label(self.root, text="ATM Simulator", font=("Helvetica", 24, "bold"),
                 fg="white", bg='#2c3e50').pack(pady=(30, 10))

        # アイコン/画像
        try:
            # resources/assets/icon.png を試す
            img_path = get_resource_path("assets/icon.png")
            if not os.path.exists(img_path):
                img_path = get_resource_path("../resources/assets/icon.png")

            self.img_orig = Image.open(img_path)
            # 画像サイズを調整（例: 80x80）
            self.img_resized = self.img_orig.resize((80, 80), Image.Resampling.LANCZOS)
            self.img = ImageTk.PhotoImage(self.img_resized)
            tk.Label(self.root, image=self.img, bg='#2c3e50').pack(pady=10)
        except Exception as e:
            # 画像の読み込みに失敗した場合は無視
            print(f"DEBUG: Splash icon load error: {e}")
            pass

        # ステータスラベル
        self.status_label = tk.Label(
            self.root, text=LOADING_STATUS["INIT"],
            fg="white", bg='#2c3e50', font=("MS Gothic", 10)
        )
        self.status_label.pack(pady=10)

        # プログレスバー
        self.progress = ttk.Progressbar(
            self.root, orient="horizontal", length=300, mode="determinate"
        )
        self.progress.pack(pady=10)

        self.error_occurred = False
        self.error_msg = ""
        self.error_hint = ""

    def update_status(self, status_code, progress_val):
        self.status_label.config(text=LOADING_STATUS.get(status_code, status_code))
        self.progress['value'] = progress_val
        self.root.update()

    def show_error(self, message, hint_code="GENERIC"):
        self.error_occurred = True
        self.error_msg = message
        self.error_hint = ERROR_HINTS.get(hint_code, ERROR_HINTS["GENERIC"])
        self.root.destroy()


def check_dependencies(splash):
    """
    必須パッケージの依存関係をチェックする。
    """
    try:
        splash.update_status("DEPS", 20)
        import numpy as np
        import cv2
        time.sleep(0.5)  # 演出用

        splash.update_status("AI", 40)
        # YOLO (Ultralytics)のロード check
        import ultralytics
        time.sleep(0.5)

        splash.update_status("CORE", 70)
        from PIL import Image
        import yaml
        import pygame
        time.sleep(0.5)

        splash.update_status("DONE", 100)
        time.sleep(0.5)
        return True

    except Exception as e:
        error_str = str(e)
        hint = "GENERIC"
        if "AVX" in error_str or "instruction" in error_str:
            hint = "AVX"
        elif "DLL" in error_str or "ImportError" in error_str:
            hint = "DLL"
        elif "ultralytics" in error_str or "torch" in error_str:
            hint = "MODEL"

        splash.show_error(f"システム起動エラー:\n{error_str}", hint)
        return False


def main():
    """
    Application Entry Point
    """
    # スプラッシュ画面の作成
    splash = SplashScreen()

    # 依存関係チェックを別スレッドまたはそのまま実行
    # (Tkinterのmainloopが必要だが、ここでは直接updateを使ってシーケンシャルに進める)
    if not check_dependencies(splash):
        # エラー発生時はメッセージボックスを表示
        if splash.error_occurred:
            error_window = tk.Tk()
            error_window.withdraw()
            messagebox.showerror(
                "起動エラー",
                f"{splash.error_msg}\n\n【考えられる原因と対策】\n{splash.error_hint}"
            )
            error_window.destroy()
        sys.exit(1)

    # スプラッシュ画面を閉じる
    splash.root.destroy()

    # メインアプリの起動
    try:
        from src.core.controller import ATMController

        root = tk.Tk()
        app = ATMController(root)
        root.protocol("WM_DELETE_WINDOW", app.on_close)
        root.mainloop()

    except Exception as e:
        error_window = tk.Tk()
        error_window.withdraw()
        messagebox.showerror("実行エラー", f"アプリケーションの実行中にエラーが発生しました:\n{e}")
        error_window.destroy()
        sys.exit(1)


if __name__ == "__main__":
    main()
