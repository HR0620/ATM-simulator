# -*- coding: utf-8 -*-
"""
AI非接触ATMシミュレーター - メインエントリーポイント

このファイルはアプリケーションの起動処理を担当します。
依存関係のチェックを行い、問題があれば分かりやすいエラーメッセージを表示します。
"""

import sys
import os

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


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
                f"❌ NumPyのバージョンが新しすぎます (現在: {np.__version__})\n"
                "   OpenCVとの互換性問題が発生します。\n"
                "   解決策: 以下のコマンドを実行してください:\n"
                "   pip uninstall numpy -y\n"
                "   pip install numpy==1.26.4"
            )
    except ImportError:
        errors.append(
            "❌ NumPyがインストールされていません\n"
            "   解決策: pip install numpy==1.26.4"
        )

    # OpenCVのインポートチェック
    try:
        import cv2
        print(f"✓ OpenCV {cv2.__version__} - 正常")
    except ImportError as e:
        errors.append(
            f"❌ OpenCVのインポートに失敗しました\n"
            f"   詳細: {e}\n"
            "   解決策: pip install opencv-python==4.9.0.80"
        )
    except AttributeError as e:
        errors.append(
            f"❌ OpenCVの内部エラー (NumPy互換性問題の可能性)\n"
            f"   詳細: {e}\n"
            "   解決策: NumPyを1.26.4にダウングレードしてください"
        )

    # TensorFlowのインポートチェック
    try:
        import tensorflow as tf
        # 警告メッセージを抑制
        tf.get_logger().setLevel('ERROR')
        print(f"✓ TensorFlow {tf.__version__} - 正常")
    except ImportError as e:
        errors.append(
            f"❌ TensorFlowのインポートに失敗しました\n"
            f"   詳細: {e}\n"
            "   解決策: pip install tensorflow==2.15.0"
        )

    # その他の必須パッケージ
    try:
        from PIL import Image
        print("✓ Pillow - 正常")
    except ImportError:
        errors.append(
            "❌ Pillowがインストールされていません\n"
            "   解決策: pip install Pillow==10.2.0"
        )

    try:
        import yaml
        print("✓ PyYAML - 正常")
    except ImportError:
        errors.append(
            "❌ PyYAMLがインストールされていません\n"
            "   解決策: pip install PyYAML==6.0.1"
        )

    # エラーがある場合は表示して終了
    if errors:
        print("\n" + "=" * 60)
        print("依存関係のエラーが検出されました")
        print("=" * 60 + "\n")
        for error in errors:
            print(error)
            print()
        print("=" * 60)
        print("すべての問題を解決してから再度実行してください。")
        print("=" * 60)
        return False

    print("\n依存関係チェック: すべて正常 ✓\n")
    return True


def main():
    """
    アプリケーションのメインエントリーポイント
    """
    print("=" * 60)
    print("AI非接触ATMシミュレーター")
    print("=" * 60)
    print("\n依存関係をチェックしています...\n")

    # 依存関係チェック
    if not check_dependencies():
        sys.exit(1)

    # チェック完了後にTkinterとコントローラをインポート
    try:
        import tkinter as tk
        from core.controller import ATMController
    except ImportError as e:
        print(f"\n❌ モジュールのインポートに失敗しました: {e}")
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
        print(f"\n❌ アプリケーションの起動中にエラーが発生しました:")
        print(f"   {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
