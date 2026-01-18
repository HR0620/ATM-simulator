import unittest
import sys
import os
import cv2
import numpy as np

# Ensure we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.face_checker import FacePositionChecker
from core.gesture_validator import GestureValidator


class TestFacePositionChecker(unittest.TestCase):
    def setUp(self):
        self.checker = FacePositionChecker(required_frames=5, guide_box_ratio=0.5)
        # Mocking frame size 100x100
        self.frame_shape = (100, 100, 3)

    def test_alignment_logic(self):
        # Guide box: 50x50 at (25,25)

        # 1. Face right in center: (40, 40, 20, 20) -> Center (50, 50)
        # Should detect
        status, _, _ = self.checker.check_face_alignment(self.frame_shape, (40, 40, 20, 20))
        self.assertEqual(status, "detecting")
        self.assertEqual(self.checker.consecutive_frames, 1)

        # 2. 5 frames later -> confirmed
        for _ in range(4):
            self.checker.check_face_alignment(self.frame_shape, (40, 40, 20, 20))

        status, _, _ = self.checker.check_face_alignment(self.frame_shape, (40, 40, 20, 20))  # 6th frame effectively
        self.assertEqual(status, "confirmed")
        self.assertTrue(self.checker.is_verified)

    def test_out_of_bounds_reset(self):
        # Good frame
        self.checker.check_face_alignment(self.frame_shape, (40, 40, 20, 20))
        self.assertEqual(self.checker.consecutive_frames, 1)

        # Bad frame (Face at 0,0) -> Center 10,10 which is outside box (25~75 range)
        status, _, _ = self.checker.check_face_alignment(self.frame_shape, (0, 0, 20, 20))
        self.assertEqual(status, "waiting")
        self.assertEqual(self.checker.consecutive_frames, 0)


class TestGestureValidator(unittest.TestCase):
    def setUp(self):
        self.validator = GestureValidator(required_frames=3, confidence_threshold=0.8, free_class="free")

    def test_free_class(self):
        # Free class should reset
        pred = {"class_name": "free", "confidence": 0.99}
        res = self.validator.validate(pred)
        self.assertEqual(res, "free")
        self.assertEqual(self.validator.consecutive_count, 0)

    def test_low_confidence(self):
        # Low confidence -> free
        pred = {"class_name": "left", "confidence": 0.5}
        res = self.validator.validate(pred)
        self.assertEqual(res, "free")

    def test_valid_gesture_confirmation(self):
        pred = {"class_name": "left", "confidence": 0.9}

        # 1. First frame
        res = self.validator.validate(pred)
        self.assertEqual(res, "free")  # Not yet confirmed
        self.assertEqual(self.validator.consecutive_count, 1)

        # 2. Second frame
        res = self.validator.validate(pred)
        self.assertEqual(res, "free")
        self.assertEqual(self.validator.consecutive_count, 2)

        # 3. Third frame (Required=3)
        res = self.validator.validate(pred)
        self.assertEqual(res, "left")  # Confirmed!
        self.assertEqual(self.validator.confirmed_gesture, "left")


if __name__ == '__main__':
    unittest.main()
