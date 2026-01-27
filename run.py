import sys
import os

# srcディレクトリをモジュール検索パスに追加
current_dir = os.path.dirname(os.path.abspath(__file__))
# srcディレクトリをモジュール検索パスに追加しない (src.xxx でインポートするため)

if __name__ == "__main__":
    import traceback

    # Debug logging
    with open("debug_run.log", "w", encoding="utf-8") as f:
        sys.stdout = f
        sys.stderr = f

        try:
            # src.mainをインポート
            try:
                from src.main import main
            except ImportError as e:
                print(f"CRITICAL: Could not import src.main: {e}")
                sys.exit(1)

            if main():
                sys.exit(0)
            else:
                sys.exit(1)
        except Exception:
            traceback.print_exc()
            sys.exit(1)
