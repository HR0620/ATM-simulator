import cv2
import numpy as np
import tensorflow as tf
import os
import sys


class AIModel:
    """
    Teachable MachineのKerasモデルを読み込み、推論を行うクラス。
    """

    def __init__(self, model_path, labels_path):
        """
        初期化メソッド

        Args:
            model_path (str): .h5ファイルのパス（相対パス可）
            labels_path (str): labels.txtのパス（相対パス可）
        """
        # 実行ディレクトリに依存しないよう、絶対パスに変換して解決する
        project_root = os.getcwd()
        self.model_path = os.path.abspath(os.path.join(project_root, model_path))
        self.labels_path = os.path.abspath(os.path.join(project_root, labels_path))

        self.model = None
        self.labels = []

        # 初期化時にロードを試みる
        self.load_model()

    def load_model(self):
        """
        Kerasモデルとラベルファイルをロードする。
        """
        # ファイルの存在確認
        if not os.path.exists(self.model_path):
            print(f"警告: モデルファイルが見つかりません: {self.model_path}")
            print("AI機能は無効化されます。")
            return

        if not os.path.exists(self.labels_path):
            print(f"警告: ラベルファイルが見つかりません: {self.labels_path}")
            print("AI機能は無効化されます。")
            return

        try:
            # NumPyの科学的表記を抑制（ログを見やすくするため）
            np.set_printoptions(suppress=True)

            # モデルのロード (compile=Falseは警告抑制のため推奨)
            self.model = tf.keras.models.load_model(self.model_path, compile=False)

            # ラベルファイルの読み込み
            with open(self.labels_path, "r", encoding="utf-8") as f:
                # 形式: "0 ClassName" または単に "ClassName" に対応
                self.labels = [line.strip().split(" ", 1)[-1] for line in f.readlines()]

            print(f"モデルのロード完了。クラスラベル: {self.labels}")

        except Exception as e:
            print(f"モデルのロード中にエラーが発生しました: {e}")
            self.model = None

    def predict(self, frame):
        """
        画像フレームを受け取り、予測結果を返す。

        Args:
            frame: OpenCV画像 (BGR形式)

        Returns:
            dict: {
                "class_name": 予測されたクラス名,
                "confidence": 確信度 (0.0~1.0),
                "all_scores": 全クラスのスコアリスト
            }
            モデル未ロード時は None を返す。
        """
        if self.model is None:
            return None

        # --- 画像の前処理 ---
        # 1. モデルの入力サイズ(224x224)にリサイズ
        image = cv2.resize(frame, (224, 224), interpolation=cv2.INTER_AREA)

        # 2. NumPy配列に変換し、形状を (1, 224, 224, 3) に合わせる
        image = np.asarray(image, dtype=np.float32).reshape(1, 224, 224, 3)

        # 3. 値を -1 から 1 の範囲に正規化 (Teachable Machineの仕様)
        image = (image / 127.5) - 1

        # --- 推論実行 ---
        prediction = self.model.predict(image, verbose=0)

        # 最も高いスコアのインデックスを取得
        index = np.argmax(prediction)

        # クラス名と確信度を取得
        class_name = self.labels[index] if index < len(self.labels) else str(index)
        confidence = prediction[0][index]

        return {
            "class_name": class_name,
            "confidence": float(confidence),
            "all_scores": prediction[0].tolist()
        }
