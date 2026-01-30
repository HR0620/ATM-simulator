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

            # 人数と面積の取得 (離席検知用)
            person_count = len(r.boxes)
            primary_person_area = 0.0
            if person_count > 0:
                # 最初のボックスを主要人物とする
                box = r.boxes[0].xywhn[0].cpu().numpy()
                primary_person_area = float(box[2] * box[3])

            # Security Filter 1: 人数チェック
            max_persons = self.safety_conf.get("max_persons", 2)
            if person_count > max_persons:
                return self._empty_result(person_count=person_count)

            # Security Filter 2: 面積チェック (主要な人物が遠すぎないか)
            if person_count > 0:
                min_area = self.safety_conf.get("min_person_area", 0.01)
                if primary_person_area < min_area:
                    return self._empty_result(
                        person_count=person_count,
                        primary_person_area=primary_person_area
                    )

            # 検出なし
            if r.keypoints is None or r.keypoints.conf is None or len(r.keypoints.xy) == 0:
                return self._empty_result(
                    person_count=person_count,
                    primary_person_area=primary_person_area
                )

            # 1人目のデータ
            kpts = r.keypoints.xy[0].cpu().numpy()  # (17, 2)
            confs = r.keypoints.conf[0].cpu().numpy()  # (17,)

            rw_score = confs[self.KEYPOINT_RIGHT_WRIST]
            lw_score = confs[self.KEYPOINT_LEFT_WRIST]

            target_idx = -1
            max_score = 0.0

            if rw_score > self.conf_threshold:
                target_idx = self.KEYPOINT_RIGHT_WRIST
                max_score = rw_score

            if lw_score > self.conf_threshold and lw_score > max_score:
                target_idx = self.KEYPOINT_LEFT_WRIST
                max_score = lw_score

            if target_idx == -1:
                return self._empty_result(
                    person_count=person_count,
                    primary_person_area=primary_person_area
                )

            # 座標取得
            x_px, y_px = kpts[target_idx]
            h, w = frame.shape[:2]

            # 正規化
            nx = x_px / w
            ny = y_px / h

            # キーポイント全体（デバッグ描画用）
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
                "height": h,
                "person_count": person_count,
                "primary_person_area": primary_person_area
            }

        except Exception as e:
            self.logger.error(f"Inference error: {e}")
            return self._empty_result()

    def _empty_result(self, person_count: int = 0, primary_person_area: float = 0.0) -> Dict[str, Any]:
        return {
            "detected": False,
            "point_x": 0.0,
            "point_y": 0.0,
            "point_x_px": 0,
            "point_y_px": 0,
            "confidence": 0.0,
            "keypoints": [],
            "person_count": person_count,
            "primary_person_area": primary_person_area
        }

    def release(self):
        # Ultralytics model typically doesn't need explicit release, but we can clear it
        self.model = None
