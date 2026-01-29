import cv2
import sys


class CameraManager:
    """
    OpenCVを使用したWebカメラのアクス管理クラス。
    カメラの接続、フレーム取得、リソース解放を担当する。
    """

    def __init__(self, device_id=0, width=640, height=480, fps=30):
        """
        初期化メソッド

        Args:
            device_id (int): 使用するカメラのデバイスID
            width (int): 設定する横幅
            height (int): 設定する縦幅
            fps (int): 設定するフレームレート
        """
        self.device_id = device_id
        self.width = width
        self.height = height
        self.fps = fps
        self.cap = None

    def start(self):
        """
        カメラのキャプチャを開始する。
        指定したIDで開けなかった場合、ID 0（デフォルト）での接続を試みる。
        """
        if self.cap is not None:
            return

        try:
            # 指定されたデバイスIDでカメラオープンを試行
            self.cap = cv2.VideoCapture(self.device_id)

            if not self.cap.isOpened():
                print(f"警告: カメラID {self.device_id} を開けませんでした。デフォルト(0)を試行します。")
                self.cap = cv2.VideoCapture(0)

            if not self.cap.isOpened():
                print("エラー: 有効なカメラが見つかりませんでした。接続を確認してください。")
                return

            # 解像度とFPSの設定
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)

            print(f"カメラを開始しました。")

        except Exception as e:
            print(f"カメラ初期化中に例外が発生しました: {e}")

    def get_frame(self):
        """
        カメラから1フレームを取得する。

        Returns:
            numpy.ndarray: 取得したフレーム（左右反転済み）
            None: 取得失敗時
        """
        if self.cap is None or not self.cap.isOpened():
            return None

        ret, frame = self.cap.read()
        if not ret:
            return None

        # 呼び出し元で反転/非反転を制御できるように、ここでは生データを返すように変更
        # ユーザー指摘の「判定逆転」問題を解決するため、AIにはRawデータ、UIにはFlipデータを渡す設計にする
        return frame

    def release(self):
        """
        カメラリソースを解放する。アプリ終了時に必ず呼ぶこと。
        """
        if self.cap is not None:
            self.cap.release()
            self.cap = None
            print("カメラリソースを解放しました。")

    def __del__(self):
        self.release()
