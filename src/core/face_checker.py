import cv2
import time
from typing import Tuple, List, Optional


class FacePositionChecker:
    """
    顔の位置を確認し、ガイド枠内に収まっているか判定するクラス。
    """

    def __init__(self, required_frames: int = 30, guide_box_ratio: float = 0.6):
        """
        Args:
            required_frames (int): 認証完了までに必要な連続フレーム数
            guide_box_ratio (float): ガイド枠の画面に対する比率
        """
        self.required_frames = required_frames
        self.guide_box_ratio = guide_box_ratio

        self.consecutive_frames = 0  # 条件を満たした連続フレーム数
        self.is_verified = False     # 認証完了フラグ

        # Load Haar Cascade classifier from resources
        from src.paths import get_resource_path
        cascade_path = get_resource_path("config/haarcascade_frontalface_default.xml")
        self.face_cascade = cv2.CascadeClassifier(cascade_path)

        if self.face_cascade.empty():
            print(f"Error: Could not load Haar Cascade file from: {cascade_path}")
            print("Fallback: Trying system-wide cv2 data path...")
            # Fallback to system-wide cv2 data path
            fallback_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.face_cascade = cv2.CascadeClassifier(fallback_path)
            if self.face_cascade.empty():
                print(f"Critical: All cascade load attempts failed.")

    def detect_faces(self, frame) -> List[Tuple[int, int, int, int]]:
        """
        フレーム内の顔を検出する。

        Returns:
            list: (x, y, w, h) のリスト
        """
        # 処理高速化のためグレースケールに変換
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 顔検出実行 (scaleFactor=1.1, minNeighbors=4 は一般的な推奨値)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
        return faces

    def get_largest_face(self, faces) -> Optional[Tuple[int, int, int, int]]:
        """
        検出された複数の顔の中から、一番大きい顔（＝一番近くにいるユーザー）を選ぶ。
        """
        if len(faces) == 0:
            return None

        # 面積 (w * h) が最大のものを取得
        largest_face = max(faces, key=lambda rect: rect[2] * rect[3])
        return largest_face

    def check_face_alignment(self, frame_shape, face_rect) -> Tuple[str, Tuple[int, int, int, int], Optional[Tuple[int, int, int, int]]]:
        """
        顔がガイド枠内に収まっているか判定し、状態を返す。

        Args:
            frame_shape: 画像の形状 (height, width, channels)
            face_rect: 顔の矩形 (x, y, w, h)

        Returns:
            status (str): "waiting"(待機中), "detecting"(認識中), "confirmed"(完了)
            guide_box (tuple): ガイド枠の座標 (x, y, w, h)
            face_rect (tuple): 検出された顔（そのまま返す）
        """
        height, width, _ = frame_shape

        # ガイド枠の計算（画面中央に正方形）
        box_size = int(height * self.guide_box_ratio)
        box_x = (width - box_size) // 2
        box_y = (height - box_size) // 2
        guide_box = (box_x, box_y, box_size, box_size)

        if face_rect is None:
            self.consecutive_frames = 0
            return "waiting", guide_box, None

        fx, fy, fw, fh = face_rect
        face_center_x = fx + fw // 2
        face_center_y = fy + fh // 2

        # 顔の中心がガイド枠内にあるかチェック
        is_x_inside = box_x < face_center_x < box_x + box_size
        is_y_inside = box_y < face_center_y < box_y + box_size

        if is_x_inside and is_y_inside:
            self.consecutive_frames += 1
        else:
            self.consecutive_frames = 0

        # おおよそN秒間（FPSによるがNフレーム）留まっていたらOK
        if self.consecutive_frames >= self.required_frames:
            self.is_verified = True
            return "confirmed", guide_box, face_rect
        elif self.consecutive_frames > 0:
            return "detecting", guide_box, face_rect
        else:
            return "waiting", guide_box, face_rect

    def process(self, frame):
        """
        メイン処理メソッド。画像を受け取り、検出・判定までを一括で行う。
        """
        if self.face_cascade.empty():
            # カスケードがない場合は処理できないため待機状態を返す
            h, w = frame.shape[:2]
            return "waiting", (0, 0, w, h), None

        faces = self.detect_faces(frame)
        largest_face = self.get_largest_face(faces)
        return self.check_face_alignment(frame.shape, largest_face)

    def reset(self):
        """状態をリセットする（再認証時など）"""
        self.consecutive_frames = 0
        self.is_verified = False
