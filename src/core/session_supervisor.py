import time
from typing import Optional, Type, Dict, Any
from src.core.state_machine import StateMachine
from src.core.gesture_validator import GestureValidator
from src.vision.async_yolo_detector import AsyncYoloDetector


class SessionSupervisor:
    """
    Manages State Machine, Session Lifecycle, and Gesture Validation.
    """

    def __init__(self, controller, initial_state_cls, config):
        self.controller = controller
        self.config = config

        # Gesture Validator
        self.gesture_validator = GestureValidator(
            required_frames=self.config["gesture"]["required_frames"],
            confidence_threshold=self.config["gesture"]["confidence_threshold"],
            free_class=self.config["gesture"]["free_class_name"],
            lock_duration=0.5
        )

        # State Machine
        self.state_machine = StateMachine(self.controller, initial_state_cls)

        # Session State
        self.normal_area = None
        self.absence_frames = 0
        self.grace_period_frames = 0
        self.ema_alpha = 0.05
        self.det_history = []
        self.last_trigger_gesture = None

    def update_gestures(self, tracker_result):
        """Stable gesture detection from tracker results."""
        prediction = {
            "class_name": tracker_result["position"],
            "confidence": 1.0 if tracker_result["is_stable"] else 0.5,
            "all_scores": []
        }

        confirmed_gesture = self.gesture_validator.validate(prediction)

        # Same-Gesture Blocking
        if tracker_result["position"] == "free" and tracker_result["is_stable"]:
            self.last_trigger_gesture = None

        effective_gesture = None
        if confirmed_gesture:
            if confirmed_gesture != self.last_trigger_gesture:
                self.last_trigger_gesture = confirmed_gesture
                effective_gesture = confirmed_gesture

        return effective_gesture, prediction

    def handle_absence(self, detection_result):
        """Checks for user absence and transitions to warning state if needed."""
        # This logic is complex and state-dependent, so it needs access to state_machine.
        current_state = self.state_machine.current_state_name
        ignore_states = ["FaceAlignmentState", "UserAbsentWarningState", "WelcomeState"]

        if getattr(self.controller, "is_exiting", False) or current_state in ignore_states:
            return None

        if self.grace_period_frames > 0:
            self.grace_period_frames -= 1
            return None

        person_count = detection_result.get("person_count", 0)
        area = detection_result.get("primary_person_area", 0.0)

        if person_count >= 2:
            return None

        # History for intermittent loss
        self.det_history.append(1 if person_count > 0 else 0)
        if len(self.det_history) > 60:
            self.det_history.pop(0)

        is_absent_suspicious = False
        if person_count == 0:
            self.absence_frames += 1
            if self.absence_frames >= 45:
                is_absent_suspicious = True
        else:
            if self.normal_area and area < (self.normal_area * 0.4):
                self.absence_frames += 1
                if self.absence_frames >= 45:
                    is_absent_suspicious = True
            else:
                self.absence_frames = 0
                if self.normal_area and abs(area - self.normal_area) < (self.normal_area * 0.15):
                    self.normal_area = (self.ema_alpha * area) + ((1 - self.ema_alpha) * self.normal_area)

        # Intermittent loss check
        if len(self.det_history) == 60:
            det_rate = sum(self.det_history) / 60
            max_consecutive = 0
            current_consecutive = 0
            for d in self.det_history:
                if d == 1:
                    current_consecutive += 1
                    max_consecutive = max(max_consecutive, current_consecutive)
                else:
                    current_consecutive = 0
            if det_rate <= 0.2 and max_consecutive < 5:
                is_absent_suspicious = True

        if is_absent_suspicious:
            from src.core.states import UserAbsentWarningState
            return UserAbsentWarningState
        return None

    def change_state(self, next_state_cls):
        """Transitions state and resets validator."""
        self.gesture_validator.force_reset()
        self.state_machine.change_state(next_state_cls)

    def push_modal(self, modal_state_cls):
        self.state_machine.push_modal(modal_state_cls)

    def pop_modal(self):
        self.state_machine.pop_modal()

    def update_state(self, frame, gesture, key_event, progress,
                     direction, debug_info):
        """Delegates update to state machine."""
        self.state_machine.update(
            frame, gesture, key_event, progress, direction, debug_info
        )
