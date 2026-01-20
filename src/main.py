# -*- coding: utf-8 -*-
"""
AI非接触ATMシミュレーター - メインエントリーポイント

このファイルはアプリケーションの起動処理を担当します。
依存関係のチェックを行い、問題があれば分かりやすいエラーメッセージを表示します。
"""

import sys
import os

# プロジェクトのルートディレクトリをパスに追加
from src.paths import get_resource_path

# EXE実行時のCWD設定のみ行う（リソース参照のため）
if getattr(sys, 'frozen', False):
    base_path = os.path.dirname(sys.executable)
    os.chdir(base_path)


def check_dependencies():
    """
    必須パッケージの依存関係をチェックする。
    問題がある場合は具体的な解決策を提示して終了する。

    Returns:
        bool: すべての依存関係が正常ならTrue
    """
    errors = []

    # NumPyのバージョンチェック
    try:
        import numpy as np
        numpy_version = tuple(map(int, np.__version__.split('.')[:2]))
        if numpy_version[0] >= 2:
            errors.append(
                f"[X] NumPy version too new (Current: {np.__version__})\n"
                "   Compatibility issue with OpenCV.\n"
                "   Solution: Run the following:\n"
                "   pip uninstall numpy -y\n"
                "   pip install numpy==1.26.4"
            )
    except ImportError:
        errors.append(
            "[X] NumPy not installed\n"
            "   Solution: pip install numpy==1.26.4"
        )

    # OpenCV Check
    try:
        import cv2
        print(f"[OK] OpenCV {cv2.__version__} - OK")
    except ImportError as e:
        errors.append(
            f"[X] OpenCV import failed\n"
            f"   Detail: {e}\n"
            "   Solution: pip install opencv-python==4.9.0.80"
        )
    except AttributeError as e:
        errors.append(
            f"[X] OpenCV internal error (Possible NumPy mismatch)\n"
            f"   Detail: {e}\n"
            "   Solution: Downgrade NumPy to 1.26.4"
        )

    # TensorFlow Check
    try:
        import tensorflow as tf
        tf.get_logger().setLevel('ERROR')
        print(f"[OK] TensorFlow {tf.__version__} - OK")
    except ImportError as e:
        errors.append(
            f"[X] TensorFlow import failed\n"
            f"   Detail: {e}\n"
            "   Solution: pip install tensorflow==2.15.0"
        )

    # Other Packages
    try:
        from PIL import Image
        print("[OK] Pillow - OK")
    except ImportError:
        errors.append(
            "[X] Pillow not installed\n"
            "   Solution: pip install Pillow==10.2.0"
        )

    try:
        import yaml
        print("[OK] PyYAML - OK")
    except ImportError:
        errors.append(
            "[X] PyYAML not installed\n"
            "   Solution: pip install PyYAML==6.0.1"
        )

    # Error Reporting
    if errors:
        print("\n" + "=" * 60)
        print("Dependency Errors Detected")
        print("=" * 60 + "\n")
        for error in errors:
            print(error)
            print()
        print("=" * 60)
        print("Please resolve all issues before running.")
        print("=" * 60)
        return False

    print("\nDependency Check: All OK [OK]\n")
    return True


def main():
    """
    Application Entry Point
    """
    print("=" * 60)
    print("AI Contactless ATM Simulator")
    print("=" * 60)
    print("\nChecking dependencies...\n")

    # Dependency Check
    if not check_dependencies():
        sys.exit(1)

    # Import Controller
    try:
        import tkinter as tk
        from src.core.controller import ATMController
    except ImportError as e:
        print(f"\n[X] Module import failed: {e}")
        print("requirements.txtからすべてのパッケージを再インストールしてください:")
        print("pip install -r requirements.txt")
        sys.exit(1)

    try:
        # Tkinterのルートウィンドウ作成
        root = tk.Tk()

        # アプリケーションコントローラの初期化
        app = ATMController(root)

        # ウィンドウが閉じられたときの処理を登録
        root.protocol("WM_DELETE_WINDOW", app.on_close)

        print("アプリケーションを起動しています...\n")

        # メインループ開始
        root.mainloop()

    except Exception as e:
        print(f"\n[X] アプリケーションの起動中にエラーが発生しました:")
        print(f"   {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
