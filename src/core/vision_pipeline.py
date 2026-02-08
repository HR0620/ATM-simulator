import cv2
from src.vision.camera_manager import CameraManager
from src.vision.async_yolo_detector import AsyncYoloDetector
from src.vision.position_tracker import PositionTracker
from src.core.face_checker import FacePositionChecker


class VisionPipeline:
    """
    Handles Camera, Detection, Tracking, and Face Alignment.
    """

    def __init__(self, config):
        self.config = config

        # Camera
        fps = self.config["camera"].get("fps", 30)
        self.camera = CameraManager(
            device_id=self.config["camera"]["device_id"],
            width=self.config["camera"]["width"],
            height=self.config["camera"]["height"],
            fps=fps
        )

        # Vision System (YOLOv8-Pose + Async)
        vision_conf = self.config.get("vision", {})
        pos_conf = self.config.get("position", {})
        safety_conf = self.config.get("safety", {})

        self.detector = AsyncYoloDetector(
            model_path=vision_conf.get("model_path", "yolov8n-pose.pt"),
            conf_threshold=vision_conf.get("min_detection_confidence", 0.5),
            interval=vision_conf.get("inference_interval", 0.03),
            safety_conf=safety_conf
        )

        self.tracker = PositionTracker(
            left_threshold=pos_conf.get("left_threshold", 0.333),
            right_threshold=pos_conf.get("right_threshold", 0.667),
            required_consecutive=pos_conf.get("required_consecutive", 5),
            free_threshold=pos_conf.get("free_threshold", 5)
        )

        guide_ratio = self.config["face_guide"].get("guide_box_ratio", 0.6)
        visual_ratio = self.config["face_guide"].get("visual_box_ratio", 0.4)
        self.face_checker = FacePositionChecker(
            required_frames=30,
            guide_box_ratio=guide_ratio,
            visual_ratio=visual_ratio
        )

    def get_frame(self):
        """Captures raw frame and returns flipped display frame."""
        raw_frame = self.camera.get_frame()
        if raw_frame is None:
            return None
        return cv2.flip(raw_frame, 1)

    def process(self, frame):
        """Runs detection and tracking on the given frame."""
        self.detector.detect_async(frame)
        detection_result = self.detector.get_latest_result()
        tracker_result = self.tracker.update(detection_result)

        return detection_result, tracker_result

    def check_face(self, frame):
        """Checks if face is aligned."""
        return self.face_checker.process(frame)

    def stop(self):
        """Stops background threads."""
        self.detector.stop()

    def release(self):
        """Releases camera and detector resources."""
        self.detector.release()
        self.camera.release()
