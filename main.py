# -*- coding: utf-8 -*-
import tkinter as tk
from core.controller import ATMController
import sys
import os

# プロジェクトのルートディレクトリをパスに追加し、モジュールの読み込みを確実にする
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def main():
    """
    アプリケーションのエントリーポイント
    """
    # Tkinterのルートウィンドウ作成
    root = tk.Tk()

    # アプリケーションコントローラの初期化
    # ここでカメラやAIモデルのロードも行われる
    app = ATMController(root)

    # ウィンドウが閉じられたときの処理を登録（リソースの解放など）
    root.protocol("WM_DELETE_WINDOW", app.on_close)

    # メインループ開始
    root.mainloop()


if __name__ == "__main__":
    main()
