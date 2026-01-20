"""
ATMコントローラー

設計意図:
- State Machine パターンでUIフローを管理
- GestureValidator と連携し、状態遷移時に強制リセット
- 進捗情報とAI予測情報をStateに渡して視覚フィードバックを実現
"""
import yaml
import traceback
import cv2
import pygame
import os
from src.vision.camera_manager import CameraManager
from src.ai.model_loader import AIModel
from src.ui.screens import ATMUI
from src.core.gesture_validator import GestureValidator
from src.core.state_machine import StateMachine
from src.core.states import FaceAlignmentState
from src.core.account_manager import AccountManager
from src.core.input_handler import PinPad
from src.paths import get_resource_path


class ATMController:
    """
    アプリケーション全体の制御を行うクラス。
    State Machineを保持し、メインループを回す。
    """

    def __init__(self, root):
        self.root = root
        self._load_config()
        self._setup_window()
        self._init_modules()
        self._start_app()

    def _load_config(self):
        """設定ファイルの読み込み"""
        try:
            config_path = get_resource_path("config/atm_config.yml")
            with open(config_path, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f)
        except Exception as e:
            print(f"設定ファイルの読み込みに失敗しました: {e}")
            raise

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

        # Audio
        try:
            pygame.mixer.init()
        except Exception as e:
            print(f"Warning: Audio mixer failed to initialize: {e}")

        # Camera
        self.camera = CameraManager(
            device_id=self.config["camera"]["device_id"],
            width=self.config["camera"]["width"],
            height=self.config["camera"]["height"]
        )

        # AI Model
        gesture_conf = self.config.get("gesture", {})
        self.ai_model = AIModel(
            model_path=self.config["model"]["path"],
            labels_path=self.config["model"]["labels_path"],
            use_ema=gesture_conf.get("use_ema", False),
            ema_alpha=gesture_conf.get("ema_alpha", 0.4)
        )

        # Gesture Validator
        self.gesture_validator = GestureValidator(
            required_frames=self.config["gesture"]["required_frames"],
            confidence_threshold=self.config["gesture"]["confidence_threshold"],
            free_class=self.config["gesture"]["free_class_name"],
            lock_duration=0.5
        )

        # Modules
        self.account_manager = AccountManager(self.config)
        self.pin_pad = PinPad()

        from src.core.face_checker import FacePositionChecker
        self.face_checker = FacePositionChecker(required_frames=30)

        # UI
        self.ui = ATMUI(self.root, self.config)

        # Context
        self.shared_context = {}
        self.last_key_event = None

        # State Machine
        self.state_machine = StateMachine(self, FaceAlignmentState)

    def _start_app(self):
        """Start App"""
        print("Starting camera...")
        self.camera.start()
        self.state_machine.start()
        self.update_loop()

    def _on_key_press(self, event):
        """キー入力を保存"""
        if event.keysym != "Escape":
            self.last_key_event = event

    def change_state(self, next_state_cls):
        """状態遷移 + Validator強制リセット"""
        self.gesture_validator.force_reset()
        self.state_machine.change_state(next_state_cls)

    def play_sound(self, filename):
        """音声再生"""
        if not pygame.mixer.get_init():
            return

        base_filename = os.path.join("assets", "sounds", filename)

        for ext in [".mp3", ".mp4", ".wav"]:
            # get_resource_pathを使って絶対パス解決
            relative_path = base_filename + ext
            path = get_resource_path(relative_path)

            if os.path.exists(path):
                try:
                    pygame.mixer.music.load(path)
                    pygame.mixer.music.play()
                except Exception as e:
                    print(f"音声再生エラー ({path}): {e}")
                return

    def update_loop(self):
        """メインの更新ループ"""
        try:
            # 1. カメラ画像取得
            raw_frame = self.camera.get_frame()
            if raw_frame is None:
                self.root.after(50, self.update_loop)
                return

            # 2. 表示用に左右反転
            display_frame = cv2.flip(raw_frame, 1)

            # 3. AI予測
            prediction = self.ai_model.predict(display_frame)

            # 4. ジェスチャー検証
            confirmed_gesture = self.gesture_validator.validate(prediction)
            progress = self.gesture_validator.get_progress()
            current_direction = self.gesture_validator.get_current_direction()

            # 5. デバッグ情報を収集
            debug_info = {
                "state_name": self.state_machine.current_state_name,
                "prediction": prediction,
                "progress": progress,
                "is_locked": self.gesture_validator.is_locked(),
            }

            # 6. キー入力取得
            key_event = self.last_key_event
            self.last_key_event = None

            # 7. State更新
            self.state_machine.update(
                display_frame,
                confirmed_gesture,
                key_event,
                progress,
                current_direction,
                debug_info
            )

            # 8. 次フレーム (~30fps)
            self.root.after(33, self.update_loop)

        except Exception as e:
            print(f"メインループ内で予期せぬエラー: {e}")
            traceback.print_exc()
            self.root.after(1000, self.update_loop)

    def on_close(self):
        """App Exit"""
        print("Exiting application...")
        try:
            self.play_sound("come-again")
        except Exception:
            pass
        self.root.after(5000, self._finalize_exit)

    def _finalize_exit(self):
        try:
            pygame.mixer.quit()
        except Exception:
            pass
        self.camera.release()
        self.root.destroy()
        print("Exit complete")
