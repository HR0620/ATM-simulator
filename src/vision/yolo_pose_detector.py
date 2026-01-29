# -*- coding: utf-8 -*-
"""
YOLOv8-Pose 検出モジュール

設計意図:
- Ultralytics YOLOv8-Pose (yolov8n-pose.pt) を使用
- 人間の手首（Wrist）座標を検出し、操作ポインタとして使用
- Python 3.13対応 (MediaPipe非対応環境への代替)
"""
from typing import Dict, Any, Optional, Tuple
import cv2
import numpy as np
import logging
try:
    from ultralytics import YOLO
    from ultralytics.engine.results import Results
except ImportError:
    YOLO = None
    Results = None

class YoloPoseDetector:
    """
    YOLOv8-Poseを使用した骨格検出クラス。
    手首(Wrist)の座標を取得して返す。
    """
    
    # COCO Keypoints indices for Wrists
    KEYPOINT_LEFT_WRIST = 9
    KEYPOINT_RIGHT_WRIST = 10
    KEYPOINT_LEFT_ELBOW = 7
    KEYPOINT_RIGHT_ELBOW = 8

    def __init__(self, model_path: str = "yolov8n-pose.pt", conf_threshold: float = 0.5, safety_conf: Optional[Dict[str, Any]] = None):
        """
        Args:
            model_path: モデルファイルパス (初回は自動ダウンロード)
            conf_threshold: 検出確信度閾値
            safety_conf: 安全設定 (max_persons, min_person_area 等)
        """
        self.logger = logging.getLogger(__name__)
        self.conf_threshold = conf_threshold
        self.safety_conf = safety_conf or {}
        self.model = None
        
        if YOLO is None:
            self.logger.error("ultralytics module not found.")
            return

        try:
            self.logger.info(f"Loading YOLOv8-Pose model: {model_path}...")
            self.model = YOLO(model_path)
            self.logger.info("YOLOv8-Pose model loaded successfully.")
        except Exception as e:
            self.logger.error(f"Failed to load YOLO model: {e}")
            self.model = None

    def detect(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        フレームから手首を検出する。

        Args:
            frame: BGR画像

        Returns:
            {
                "detected": bool,
                "point_x": float,       # 正規化X (0.0-1.0)
                "point_y": float,       # 正規化Y (0.0-1.0)
                "point_x_px": int,
                "point_y_px": int,
                "confidence": float,
                "keypoints": list       # 全キーポイント (デバッグ用)
            }
        """
        if self.model is None:
            return self._empty_result()

        try:
            # 推論実行 (verbose=Falseでログ抑制)
            results = self.model(frame, verbose=False, conf=self.conf_threshold)
            
            if not results or len(results) == 0:
                return self._empty_result()
                
            r: Results = results[0]

            # Security Filter 1: 人数チェック
            max_persons = self.safety_conf.get("max_persons", 2)
            if len(r.boxes) > max_persons:
                # 3人以上(設定値超)は誤検出リスクが高いため無視
                # logging.warning(f"Safety: Too many persons ({len(r.boxes)})")
                return self._empty_result()

            # Security Filter 2: 面積チェック (主要な人物が遠すぎないか)
            if len(r.boxes) > 0:
                min_area = self.safety_conf.get("min_person_area", 0.01)
                # normalized xywh (x, y, w, h)
                box = r.boxes[0].xywhn[0].cpu().numpy()
                area = box[2] * box[3]
                if area < min_area:
                    # logging.warning(f"Safety: Person too small ({area:.4f} < {min_area})")
                    return self._empty_result()
            
            # 検出なし
            if r.keypoints is None or r.keypoints.conf is None or len(r.keypoints.xy) == 0:
                return self._empty_result()

            # 最も信頼度の高い人物を選択、または最大サイズ？
            # ここでは最初の人物を使用
            # keypoints shape: (num_persons, 17, 2)
            # conf shape: (num_persons, 17)
            
            # 手首の検出確認
            # 左右の手首のうち、信頼度が高く、かつ画面手前(カメラに近い=サイズが大きい？)などのロジックが必要だが
            # シンプルに「信頼度が閾値を超えている手首」を探す
            
            # 1人目のデータ
            kpts = r.keypoints.xy[0].cpu().numpy()  # (17, 2)
            confs = r.keypoints.conf[0].cpu().numpy() # (17,)

            # 右手首(10)と左手首(9)のスコア比較
            # ユーザー視点では、右手を出せば画面左側(ミラー)、左手なら右側？
            # どちらか信頼度の高い方、あるいは「上にある方」などを採用
            
            rw_score = confs[self.KEYPOINT_RIGHT_WRIST]
            lw_score = confs[self.KEYPOINT_LEFT_WRIST]
            
            target_idx = -1
            max_score = 0.0
            
            # 閾値チェック
            if rw_score > self.conf_threshold:
                target_idx = self.KEYPOINT_RIGHT_WRIST
                max_score = rw_score
                
            if lw_score > self.conf_threshold and lw_score > max_score:
                target_idx = self.KEYPOINT_LEFT_WRIST
                max_score = lw_score
                
            if target_idx == -1:
                return self._empty_result()
                
            # 座標取得
            x_px, y_px = kpts[target_idx]
            h, w = frame.shape[:2]
            
            # 正規化
            nx = x_px / w
            ny = y_px / h
            
            # キーポイント全体（デバッグ描画用: (x, y, conf) or just (x, y) list）
            debug_kpts = []
            for i in range(len(kpts)):
                debug_kpts.append((kpts[i][0], kpts[i][1], confs[i]))

            return {
                "detected": True,
                "point_x": float(nx),
                "point_y": float(ny),
                "point_x_px": int(x_px),
                "point_y_px": int(y_px),
                "confidence": float(max_score),
                "keypoints": debug_kpts,
                "width": w,
                "height": h
            }

        except Exception as e:
            self.logger.error(f"Inference error: {e}")
            return self._empty_result()

    def _empty_result(self) -> Dict[str, Any]:
        return {
            "detected": False,
            "point_x": 0.0,
            "point_y": 0.0,
            "point_x_px": 0,
            "point_y_px": 0,
            "confidence": 0.0,
            "keypoints": []
        }
        
    def release(self):
        # Ultralytics model typically doesn't need explicit release, but we can clear it
        self.model = None
