import cv2
import mediapipe as mp

# Explicitly load solutions for robustness
try:
    from mediapipe import solutions
except ImportError:
    pass


class HandTracker:
    """
    MediaPipeを使用したハンドトラッキングクラス。
    指先の位置座標(x, y)を取得するために使用する。
    """

    def __init__(self, max_num_hands=1, min_detection_confidence=0.5):
        # mp.solutionsが直接参照できないケースへの対応
        if hasattr(mp, 'solutions'):
            self.mp_hands = mp.solutions.hands
        else:
            # from mediapipe import solutions が効いているか、あるいは直接タスクAPIを使うべきか
            # ここでは一般的な解決策として solutions を使ってみる
            import mediapipe.python.solutions.hands as mp_hands
            self.mp_hands = mp_hands

        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_num_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=0.5
        )

    def get_index_finger_x(self, frame):
        """
        画像から人差し指の先端のX座標(0.0 ~ 1.0)を取得する。
        手が検出されない場合は None を返す。
        """
        # MediaPipeはRGB画像を期待する
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)

        if results.multi_hand_landmarks:
            # 最初に見つかった手だけを使用
            hand_landmarks = results.multi_hand_landmarks[0]

            # 人差し指の先端 (INDEX_FINGER_TIP = 8)
            index_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]

            return index_tip.x

        return None
