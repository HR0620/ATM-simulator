import cv2
import numpy as np
import tensorflow as tf
import os


class AIModel:
    """
    Teachable MachineのKerasモデルを読み込み、推論を行うクラス。
    """

    def __init__(self, model_path, labels_path, use_ema=False, ema_alpha=0.4):
        """
        初期化メソッド

        Args:
            model_path (str): .h5ファイルのパス
            labels_path (str): labels.txtのパス
            use_ema (bool): 指数移動平均(EMA)による平滑化を行うか
            ema_alpha (float): EMAの平滑化係数 (0 < alpha <= 1)
        """
        # 実行ディレクトリに依存しないよう、絶対パスに変換して解決する
        # 実行ディレクトリに依存しないよう、絶対パスに変換して解決する
        from src.paths import get_resource_path
        self.model_path = get_resource_path(model_path)
        self.labels_path = get_resource_path(labels_path)

        self.model = None
        self.labels = []

        # EMA用状態
        self.use_ema = use_ema
        self.ema_alpha = ema_alpha
        self._ema_scores = None

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

        #画像の前処理
        #BGRからRGBに変換 (Teachable MachineはRGB学習)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        #モデルの入力サイズ(224x224)にリサイズ
        image = cv2.resize(frame_rgb, (224, 224), interpolation=cv2.INTER_AREA)

        #NumPy配列に変換し、形状を (1, 224, 224, 3) に合わせる
        image = np.asarray(image, dtype=np.float32).reshape(1, 224, 224, 3)

        #値を -1 から 1 の範囲に正規化 (Teachable Machineの仕様)
        image = (image / 127.5) - 1

        #推論実行
        prediction = self.model.predict(image, verbose=0)
        current_scores = prediction[0]

        #EMA (指数移動平均) フィルタ
        if self.use_ema:
            if self._ema_scores is None:
                self._ema_scores = current_scores
            else:
                self._ema_scores = (self.ema_alpha * current_scores) + \
                                   ((1 - self.ema_alpha) * self._ema_scores)

            #判定には平滑化されたスコアを使用
            scores_to_use = self._ema_scores
        else:
            scores_to_use = current_scores

        #最も高いスコアのインデックスを取得
        index = np.argmax(scores_to_use)

        #クラス名と確信度を取得
        class_name = self.labels[index] if index < len(self.labels) else str(index)
        confidence = scores_to_use[index]

        return {
            "class_name": class_name,
            "confidence": float(confidence),
            "all_scores": scores_to_use.tolist()
        }
