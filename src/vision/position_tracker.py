# -*- coding: utf-8 -*-
"""
位置追跡モジュール

設計意図:
- 指先座標から left / center / right を判定
- 連続フレームでの安定化処理
- 異常検出（画面端すぎる等）
- 一定フレーム検出なしで free 判定
"""
from typing import Optional, Dict, Any, Tuple
from collections import deque
from enum import Enum


class FingerPosition(Enum):
    """指の位置を表す列挙型"""
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    FREE = "free"


class PositionTracker:
    """
    指先座標を追跡し、安定した位置判定を提供するクラス。
    座標解析と時間的フィルタリングを統合している。
    """

    def __init__(
        self,
        left_threshold: float = 1/3,
        right_threshold: float = 2/3,
        required_consecutive: int = 5,
        free_threshold: int = 5,
        edge_margin: float = 0.05,
        head_zone_ratio: float = 0.1
    ):
        """
        初期化メソッド

        Args:
            left_threshold: 左領域の閾値（0〜1の比率）
            right_threshold: 右領域の閾値（0〜1の比率）
            required_consecutive: 同一位置確定に必要な連続フレーム数
            free_threshold: この回数連続で検出なしなら free と判定
            edge_margin: 画面端のマージン（0〜1の比率、この範囲内は無視）
            head_zone_ratio: 画面上部の無視領域率 (例: 0.1なら上10%は無視)
        """
        self.left_threshold = left_threshold
        self.right_threshold = right_threshold
        self.required_consecutive = required_consecutive
        self.free_threshold = free_threshold
        self.edge_margin = edge_margin
        self.head_zone_ratio = head_zone_ratio

        # 状態管理
        self._position_history: deque = deque(maxlen=required_consecutive * 2)
        self._no_detection_count: int = 0
        self._last_stable_position: FingerPosition = FingerPosition.FREE
        self._current_candidate: Optional[FingerPosition] = None
        self._consecutive_count: int = 0
        
        # COCO Keypoints constants
        self.KP_LW = 9   # Left Wrist
        self.KP_RW = 10  # Right Wrist
        self.KP_LE = 7   # Left Elbow
        self.KP_RE = 8   # Right Elbow

    def _calculate_finger_tip(self, keypoints: list, width: int, height: int) -> Optional[Tuple[float, float]]:
        """
        手首と肘から指先座標を推測する (Vector Extrapolation)
        指先 = 手首 + (手首 - 肘) * 0.8
        
        Returns:
            (x_norm, y_norm) or None
        """
        if not keypoints or len(keypoints) < 11 or width == 0 or height == 0:
            return None
            
        # Keypoints: 7:LE, 8:RE, 9:LW, 10:RW
        # keypoints: list of (x, y, conf)
        
        rw = keypoints[self.KP_RW]
        lw = keypoints[self.KP_LW]
        re = keypoints[self.KP_RE]
        le = keypoints[self.KP_LE]
        
        # 信頼度チェック (0.3以上)
        min_conf = 0.3
        
        target_w = None
        target_e = None
        
        rw_score = rw[2] if len(rw) > 2 else 0
        lw_score = lw[2] if len(lw) > 2 else 0
        # 肘の信頼度はある程度低くても良いが、手首は必須
        
        # 右手・左手の選定 (信頼度が高い方)
        rw_valid = rw_score > min_conf
        lw_valid = lw_score > min_conf

        if rw_valid and lw_valid:
            if rw_score > lw_score:
                target_w, target_e = rw, re
            else:
                target_w, target_e = lw, le
        elif rw_valid:
            target_w, target_e = rw, re
        elif lw_valid:
            target_w, target_e = lw, le
        else:
            return None
            
        # 手首はわかったが、肘が信頼できない場合は手首をそのまま使う
        if len(target_e) > 2 and target_e[2] < min_conf:
            return (target_w[0] / width, target_w[1] / height)
            
        # ベクトル計算 (Pixel)
        wx, wy = target_w[0], target_w[1]
        ex, ey = target_e[0], target_e[1]
        
        vec_x = wx - ex
        vec_y = wy - ey
        
        # 0.8倍
        fx = wx + vec_x * 0.8
        fy = wy + vec_y * 0.8
        
        return (fx / width, fy / height)

    def update(self, detection_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        新しい検出結果で状態を更新し、安定した位置を返す。
        """
        # 検出なしの場合
        if not detection_result.get("detected", False):
            return self._handle_no_detection()
            
        # 画面サイズ取得
        w = detection_result.get("width", 0)
        h = detection_result.get("height", 0)
        
        # 指先計算
        keypoints = detection_result.get("keypoints", [])
        finger_pos = self._calculate_finger_tip(keypoints, w, h)
        
        x = 0.0
        y = 0.0
        using_finger = False

        if finger_pos:
            x, y = finger_pos
            using_finger = True
            
            # Safety: Head Zone Check (画面上部は無視)
            if y < self.head_zone_ratio:
                 # 上すぎる場合はFree扱い (検出なし扱い)
                 return self._handle_no_detection()
        else:
            # Fallback to simple Wrist point
            x = detection_result.get("point_x", 0.0)
            
        candidate = self._determine_position(x)

        # 異常検出（画面端すぎる場合は無視）
        if self._is_edge_position(x):
            return self._handle_no_detection()

        # 検出カウンタをリセット
        self._no_detection_count = 0

        # 連続性チェック
        if candidate == self._current_candidate:
            self._consecutive_count += 1
        else:
            self._current_candidate = candidate
            self._consecutive_count = 1

        # 進捗率計算
        progress = min(1.0, self._consecutive_count / self.required_consecutive)

        # デバッグ情報
        debug_info = {
            "point_x": x,
            "candidate": candidate.value,
            "consecutive": self._consecutive_count,
            "using_finger": using_finger
        }
        if using_finger:
             debug_info["finger_tip"] = (x, y)

        # 確定判定
        is_stable = self._consecutive_count >= self.required_consecutive
        if is_stable:
            self._last_stable_position = candidate
            return {
                "position": candidate.value,
                "progress": 1.0,
                "is_stable": True,
                "debug_info": debug_info
            }

        # まだ確定していない場合は前回の安定位置を維持
        return {
            "position": self._last_stable_position.value,
            "progress": progress,
            "is_stable": False,
            "debug_info": debug_info
        }

    def _handle_no_detection(self) -> Dict[str, Any]:
        """検出なしの場合の処理"""
        self._no_detection_count += 1
        self._current_candidate = None
        self._consecutive_count = 0

        # 一定フレーム検出なしなら free
        if self._no_detection_count >= self.free_threshold:
            self._last_stable_position = FingerPosition.FREE
            return {
                "position": "free",
                "progress": 0.0,
                "is_stable": True,
                "debug_info": {
                    "no_detection_count": self._no_detection_count
                }
            }

        # まだ閾値に達していない場合は前回の安定位置を維持
        return {
            "position": self._last_stable_position.value,
            "progress": 0.0,
            "is_stable": False,
            "debug_info": {
                "no_detection_count": self._no_detection_count
            }
        }

    def _determine_position(self, x: float) -> FingerPosition:
        """正規化X座標から位置を判定する"""
        if x < self.left_threshold:
            return FingerPosition.LEFT
        elif x < self.right_threshold:
            return FingerPosition.CENTER
        else:
            return FingerPosition.RIGHT

    def _is_edge_position(self, x: float) -> bool:
        """画面端すぎるかどうかを判定"""
        return x < self.edge_margin or x > (1.0 - self.edge_margin)

    def get_progress(self) -> float:
        """UI用: 0.0〜1.0 の確定進捗率"""
        if self._current_candidate is None:
            return 0.0
        return min(1.0, self._consecutive_count / self.required_consecutive)

    def get_current_direction(self) -> Optional[str]:
        """現在認識中の方向を返す（進捗表示用）"""
        if self._current_candidate is None:
            return None
        return self._current_candidate.value

    def reset(self) -> None:
        """状態をリセットする"""
        self._position_history.clear()
        self._no_detection_count = 0
        self._last_stable_position = FingerPosition.FREE
        self._current_candidate = None
        self._consecutive_count = 0
