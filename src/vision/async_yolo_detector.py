# -*- coding: utf-8 -*-
"""
非同期YOLO検出モジュール

設計意図:
- 画像処理スレッドをUIスレッドから分離
- 常に最新の検出結果を提供
"""
import threading
import time
import copy
import numpy as np
from typing import Optional, Dict, Any
from src.vision.yolo_pose_detector import YoloPoseDetector


class AsyncYoloDetector:
    """
    YoloPoseDetectorを別スレッドで実行するラッパークラス。
    """

    def __init__(
        self,
        model_path: str = "yolov8n-pose.pt",
        conf_threshold: float = 0.5,
        interval: float = 0.03,
        safety_conf: Optional[Dict[str, Any]] = None
    ):
        self.detector = YoloPoseDetector(
            model_path=model_path,
            conf_threshold=conf_threshold,
            safety_conf=safety_conf
        )
        self.interval = interval

        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()
        
        self._latest_frame: Optional[np.ndarray] = None
        self._latest_result: Dict[str, Any] = self.detector._empty_result()
        self._new_frame_event = threading.Event()

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._inference_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread is not None:
            self._new_frame_event.set() # Wake up thread
            self._thread.join(timeout=1.0)
            self._thread = None
        self.detector.release()

    def detect_async(self, frame: np.ndarray):
        if not self._running:
            return
        with self._lock:
            self._latest_frame = frame.copy()
        self._new_frame_event.set()

    def get_latest_result(self) -> Dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._latest_result)

    def _inference_loop(self):
        while self._running:
            if not self._new_frame_event.wait(timeout=0.1):
                continue
            self._new_frame_event.clear()
            
            frame_to_process = None
            with self._lock:
                if self._latest_frame is not None:
                    frame_to_process = self._latest_frame
                    self._latest_frame = None

            if frame_to_process is not None:
                start_time = time.time()
                result = self.detector.detect(frame_to_process)
                with self._lock:
                    self._latest_result = result
                
                elapsed = time.time() - start_time
                wait_time = max(0.0, self.interval - elapsed)
                if wait_time > 0:
                    time.sleep(wait_time)

    def release(self):
        self.stop()
