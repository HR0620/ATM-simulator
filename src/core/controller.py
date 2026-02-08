"""
ATMコントローラー

設計意図:
- State Machine パターンでUIフローを管理
- GestureValidator と連携し、状態遷移時に強制リセット
- 進捗情報とAI予測情報をStateに渡して視覚フィードバックを実現
"""
import traceback
import cv2
import os
from src.vision.camera_manager import CameraManager
from src.vision.async_yolo_detector import AsyncYoloDetector
from src.vision.position_tracker import PositionTracker
from src.ui.screens import ATMUI
from src.core.gesture_validator import GestureValidator
from src.core.state_machine import StateMachine
from src.core.states import FaceAlignmentState
from src.core.account_manager import AccountManager
from src.core.input_handler import PinPad
from src.core.transaction_context import TransactionContext
from src.core.vision_pipeline import VisionPipeline
from src.core.session_supervisor import SessionSupervisor
from src.paths import get_resource_path


class ATMController:
    """
    アプリケーション全体の制御を行うクラス。
    State Machineを保持し、メインループを回す。
    """

    def __init__(self, root):
        self.root = root

        # Initialize Core Managers
        from src.core.config_loader import ConfigLoader
        from src.core.audio_manager import AudioManager
        from src.core.i18n_manager import I18nManager

        self.config_loader = ConfigLoader()
        self.config = self.config_loader.config  # Compatibility alias
        self.audio = AudioManager()
        self.i18n = I18nManager()

        # Sync initial language
        self.audio.set_language(self.i18n.current_lang)

        # Context (Type-safe)
        self.shared_context = TransactionContext()

        self._setup_window()
        self._init_modules()
        self._start_app()

    def _setup_window(self):
        """ウィンドウ設定"""
        self.root.title(self.config["ui"]["title"])

        # アイコン設定
        icon_path = get_resource_path("icon.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception as e:
                print(f"アイコンの読み込みに失敗しました: {e}")

        w = self.config['ui']['window_width']
        h = self.config['ui']['window_height']
        self.root.geometry(f"{w}x{h}")
        self.root.bind("<Key>", self._on_key_press)
        self.root.bind("<Escape>", lambda e: self.on_close())

    def _init_modules(self):
        """Module Initialization"""
        print("Initializing modules...")

        # Vision Pipeline (Encapsulated)
        self.vision = VisionPipeline(self.config)

        # Non-Vision Modules
        self.account_manager = AccountManager(self.config)
        self.pin_pad = PinPad()

        # UI (Pass I18nManager)
        self.ui = ATMUI(self.root, self.config, self.i18n)

        # Context (Type-safe)
        self.shared_context = TransactionContext()
        self.last_key_event = None
        self.is_exiting = False

        # Session Supervisor (Encapsulated)
        self.session = SessionSupervisor(self, FaceAlignmentState, self.config)

        # UI Callback binding
        self.ui.set_language_callback(self.toggle_language)

    # Proxy to SessionSupervisor
    @property
    def state_machine(self):
        return self.session.state_machine

    @property
    def grace_period_frames(self):
        return self.session.grace_period_frames

    @grace_period_frames.setter
    def grace_period_frames(self, value):
        self.session.grace_period_frames = value

    @property
    def normal_area(self):
        return self.session.normal_area

    @normal_area.setter
    def normal_area(self, value):
        self.session.normal_area = value

    def toggle_language(self):
        """言語選択モーダルを表示"""
        from src.core.states import LanguageModal
        self.open_modal(LanguageModal)

    def open_modal(self, modal_state_cls):
        """モーダルを表示"""
        self.session.push_modal(modal_state_cls)

    def close_modal(self):
        """モーダルを閉じる"""
        self.session.pop_modal()

    def play_voice(self, key):
        """Play localized voice"""
        self.audio.play_voice(key)

    def play_se(self, key):
        """Play sound effect"""
        self.audio.play_se(key)

    # Wrapper aliases for compatibility (can be removed later if states are fully updated)
    def play_sound(self, key):
        self.audio.play(key)

    def play_button_se(self):
        self.audio.play_se("button")  # or touch-button

    def play_cancel_se(self):
        self.audio.play_se("cancel")

    def play_assert_se(self):
        self.audio.play_se("assert")

    def play_error_se(self):
        self.audio.play_se("incorrect")

    def play_beep_se(self):
        self.audio.play_se("beep")

    def play_back_se(self):
        self.audio.play_se("back")

    def _start_app(self):
        """Start App"""
        print("Starting vision system and session...")
        self.vision.detector.start()
        self.vision.camera.start()
        self.session.state_machine.start()
        self.update_loop()

    def _on_key_press(self, event):
        """キー入力を保存"""
        if event.keysym != "Escape":
            self.last_key_event = event

    def change_state(self, next_state_cls):
        """状態遷移 + Validator強制リセット"""
        self.session.change_state(next_state_cls)

    # Audio methods moved to AudioManager, but keeping play_sound for temporary compatibility if needed
    # Better: Remove them and update states.py to use self.controller.audio.play()

    def update_loop(self):
        """メインの更新ループ (Orchestrated)"""
        try:
            if getattr(self, "is_exiting", False):
                self.ui.render_frame(None, {"mode": "exit"})
                self.root.after(33, self.update_loop)
                return

            # 1. Vision Logic
            frame = self.vision.get_frame()
            if frame is None:
                self.root.after(50, self.update_loop)
                return

            detection_result, tracker_result = self.vision.process(frame)

            # 2. Session Logic
            # Absence Detection
            next_state = self.session.handle_absence(detection_result)
            if next_state:
                self.change_state(next_state)

            # Gesture Analysis
            gesture, prediction = self.session.update_gestures(tracker_result)

            # 3. Input logic
            key_event = self.last_key_event
            self.last_key_event = None

            # 4. State Update
            debug_info = {
                "state_name": self.state_machine.current_state_name,
                "prediction": prediction,
                "progress": tracker_result["progress"],
                "is_locked": self.session.gesture_validator.is_locked(),
            }

            self.session.update_state(
                frame,
                gesture,
                key_event,
                tracker_result["progress"],
                tracker_result["position"],
                debug_info
            )

            # Next Frame
            self.root.after(33, self.update_loop)

        except Exception as e:
            print(f"メインループ内で予期せぬエラー: {e}")
            traceback.print_exc()
            self.root.after(1000, self.update_loop)

    def on_close(self):
        """App Exit"""
        if getattr(self, "is_exiting", False):
            return

        self.is_exiting = True
        print("Exiting application...")

        # Stop vision
        self.vision.stop()

        try:
            self.audio.play("come-again", force=True)
            self.audio.play_voice("come-again")
        except Exception:
            pass
        self.root.after(5000, self._finalize_exit)

    def _finalize_exit(self):
        try:
            self.audio.quit()
        except Exception:
            pass

        self.vision.release()
        self.root.destroy()
        print("Exit complete")
