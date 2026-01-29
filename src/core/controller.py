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
from src.vision.async_yolo_detector import AsyncYoloDetector
from src.vision.position_tracker import PositionTracker
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
        
        self.async_detector = AsyncYoloDetector(
            model_path=vision_conf.get("model_path", "yolov8n-pose.pt"),
            conf_threshold=vision_conf.get("min_detection_confidence", 0.5),
            interval=vision_conf.get("inference_interval", 0.03),
            safety_conf=safety_conf
        )
        
        self.position_tracker = PositionTracker(
            left_threshold=pos_conf.get("left_threshold", 0.333),
            right_threshold=pos_conf.get("right_threshold", 0.667),
            required_consecutive=pos_conf.get("required_consecutive", 5),
            free_threshold=pos_conf.get("free_threshold", 5)
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
        guide_ratio = self.config["face_guide"].get("guide_box_ratio", 0.6)
        self.face_checker = FacePositionChecker(
            required_frames=30,
            guide_box_ratio=guide_ratio
        )

        # UI
        self.ui = ATMUI(self.root, self.config)

        # Context
        # Context
        self.shared_context = {}
        self.last_key_event = None
        self.last_trigger_gesture = None  # UX Loop防止用
        self.is_exiting = False

        # State Machine
        self.state_machine = StateMachine(self, FaceAlignmentState)

    def _start_app(self):
        """Start App"""
        print("Starting camera and vision system...")
        self.async_detector.start()
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

        # 終了シーケンス中は come-again 以外の音声を無視する
        if getattr(self, "is_exiting", False) and filename != "come-again":
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
            # 終了処理中は Exit画面 (bow.png) を表示してループ継続
            if getattr(self, "is_exiting", False):
                self.ui.render_frame(None, {"mode": "exit"})
                self.root.after(33, self.update_loop)
                return

            # 1. カメラ画像取得
            raw_frame = self.camera.get_frame()
            if raw_frame is None:
                self.root.after(50, self.update_loop)
                return

            # 2. 表示用に左右反転
            display_frame = cv2.flip(raw_frame, 1)

            # 3. Vision Pipeline
            # 非同期検出リクエスト
            self.async_detector.detect_async(display_frame)
            
            # 最新結果の取得
            detection_result = self.async_detector.get_latest_result()
            
            # 位置追跡と安定化
            tracker_result = self.position_tracker.update(detection_result)
            
            # AIModel互換の予測辞書を作成 (GestureValidator用)
            # PositionTrackerですでに安定化されているため、Validatorの連続判定は補助的なものになる
            prediction = {
                "class_name": tracker_result["position"],
                "confidence": 1.0 if tracker_result["is_stable"] else 0.5,
                "all_scores": []
            }

            # 4. ジェスチャー検証 (Lock機構など)
            # Trackerがunstableな場合はValidatorに渡さない（またはfree扱い）方が安全かもしれないが、
            # confidenceで制御する
            confirmed_gesture = self.gesture_validator.validate(prediction)
            
            # UX Loop防止: 同一ジェスチャーの連続発火をブロック (Same-Gesture Blocking)
            # Free状態（手がなくなった）ならリセットして次の動作を受け付ける
            if tracker_result["position"] == "free" and tracker_result["is_stable"]:
                self.last_trigger_gesture = None

            # 意図の変更（ジェスチャーの変化）のみを受け入れる
            effective_gesture = None
            if confirmed_gesture:
                if confirmed_gesture == self.last_trigger_gesture:
                    # 前回と同じジェスチャー（押しっぱなし）は無視
                    effective_gesture = None
                else:
                    # ジェスチャーが変化した -> 採用
                    self.last_trigger_gesture = confirmed_gesture
                    effective_gesture = confirmed_gesture
            # confirmed_gestureがNone（不安定）の場合は状態を更新しない（ノイズ対策）
            
            # 進捗はTrackerまたはValidatorから取得
            # Trackerのprogressの方が直感的かもしれない
            progress = tracker_result["progress"]
            current_direction = tracker_result["position"]

            # 5. デバッグオーバーレイ描画
            vision_conf = self.config.get("vision", {})
            if vision_conf.get("debug_overlay", False) or self.config["ui"].get("debug_mode", False):
                self._draw_debug_overlay(display_frame, detection_result, tracker_result)

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
                effective_gesture,
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

    def _draw_debug_overlay(self, frame, detection, tracker_result):
        """デバッグ情報をフレームに描画"""
        h, w = frame.shape[:2]
        
        # 領域境界線
        pos_conf = self.config.get("position", {})
        l_th = int(w * pos_conf.get("left_threshold", 0.333))
        r_th = int(w * pos_conf.get("right_threshold", 0.667))
        
        cv2.line(frame, (l_th, 0), (l_th, h), (0, 255, 255), 1)
        cv2.line(frame, (r_th, 0), (r_th, h), (0, 255, 255), 1)
        
        # 検出点 (Wrist)
        if detection.get("detected"):
            px = detection["point_x_px"]
            py = detection["point_y_px"]
            cv2.circle(frame, (px, py), 10, (0, 0, 255), -1)
            cv2.putText(frame, "Wrist", (px + 15, py), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

            # 全キーポイント（青色）
            if "keypoints" in detection:
                for kp in detection["keypoints"]:
                    # kp = [x, y, conf]
                    if len(kp) >= 2:
                        cx, cy = int(kp[0]), int(kp[1])
                        if cx > 0 and cy > 0:
                            cv2.circle(frame, (cx, cy), 3, (255, 0, 0), -1)

        
        # 判定ステータス
        status_text = f"Pos: {tracker_result['position']} ({tracker_result['progress']:.0%})"
        if tracker_result.get("is_stable"):
            color = (0, 255, 0)
        else:
            color = (0, 255, 255)
            
        cv2.putText(frame, status_text, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        # Lock状態
        if self.gesture_validator.is_locked():
            cv2.putText(frame, "LOCKED", (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    def on_close(self):
        """App Exit"""
        if getattr(self, "is_exiting", False):
            return

        self.is_exiting = True
        print("Exiting application...")
        
        # Stop vision
        if hasattr(self, 'async_detector'):
            self.async_detector.stop()
            
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
        
        if hasattr(self, 'async_detector'):
            self.async_detector.release()
            
        self.camera.release()
        self.root.destroy()
        print("Exit complete")
