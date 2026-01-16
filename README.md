#!/bin/bash

echo "========================================"
echo "AI非接触ATMシミュレーター セットアップ"
echo "========================================"
echo

echo "[1/4] 仮想環境を作成しています..."
python3 -m venv .venv
if [ $? -ne 0 ]; then
    echo "エラー: 仮想環境の作成に失敗しました"
    exit 1
fi

echo "[2/4] 仮想環境を有効化しています..."
source .venv/bin/activate

echo "[3/4] NumPyをインストールしています..."
pip install numpy==1.26.4
if [ $? -ne 0 ]; then
    echo "エラー: NumPyのインストールに失敗しました"
    exit 1
fi

echo "[4/4] その他の依存パッケージをインストールしています..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "エラー: パッケージのインストールに失敗しました"
    exit 1
fi

echo
echo "========================================"
echo "セットアップが完了しました!"
echo "========================================"
echo
echo "次回からは以下のコマンドでアプリを起動できます:"
echo "  source .venv/bin/activate"
echo "  python main.py"
echo
```

## 5. .gitignore (更新版)
```
# 仮想環境
.venv/
venv/
env/

# テストファイル
tests/

# Pythonキャッシュ
__pycache__/
*.py[cod]
*$py.class
*.so

# IDE設定
.vscode/
.idea/
*.swp
*.swo
*~

# OSファイル
.DS_Store
Thumbs.db

# ログファイル
*.log

# AIモデル (大容量のため)
model/keras_model.h5

# 一時ファイル
*.tmp
*.bak
```

---

# 初心者向け解説

## この修正で何が良くなったか

### 1. **依存関係の問題を根本から解決**

**問題だったこと:**
- NumPy 2.xとOpenCV 4.9が互換性がない
- 適切なバージョンがインストールされていなかった

**修正内容:**
- `requirements.txt`で互換性のあるバージョンを厳密に指定
- NumPy 1.26.4を使用することでOpenCVと正常に動作

**例え話:**
レゴブロック(OpenCV)を組み立てるとき、新しい規格の台座(NumPy 2.x)では穴の大きさが合わなくてはまりません。古い規格の台座(NumPy 1.x)を使うことで、ちゃんとはまるようになります。

### 2. **エラーを事前に検出する仕組み**

**問題だったこと:**
- アプリが起動してからクラッシュする
- エラーメッセージが技術的すぎて分かりにくい

**修正内容:**
- `check_dependencies()`関数で起動前にチェック
- 問題があれば具体的な解決策を日本語で表示

**効果:**
```
従来: アプリ起動 → クラッシュ → 「何が問題?」
改善後: チェック → 問題発見 → 「こうすれば直る!」を表示