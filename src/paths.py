import sys
import os


def get_resource_path(relative_path):
    """
    リソースファイルの絶対パスを取得する。
    開発環境とPyInstallerによるEXE環境の両方に対応。

    Args:
        relative_path (str): resourcesフォルダからの相対パス (例: "config/atm_config.yml")

    Returns:
        str: リソースファイルの絶対パス
    """
    if getattr(sys, 'frozen', False):
        # PyInstallerでビルドされたEXE実行時
        # EXEのあるフォルダ (sys.executableの場所) を基準にする
        base_path = os.path.dirname(sys.executable)

        # EXE実行時は resources フォルダはEXEと同じ階層にある
        resource_path = os.path.join(base_path, "resources", relative_path)
    else:
        # 開発環境 (src/paths.py の位置から逆算)
        # 構成: project_root/src/paths.py
        # リソース: project_root/resources/
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        resource_path = os.path.join(project_root, "resources", relative_path)

    # パスが正しいか確認（デバッグ用）
    # print(f"DEBUG: Resource Path Resolved: {resource_path}")

    return os.path.abspath(resource_path)
