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
        visual_ratio = self.config["face_guide"].get("visual_box_ratio", 0.4)
        self.face_checker = FacePositionChecker(
            required_frames=30,
            guide_box_ratio=guide_ratio,
            visual_ratio=visual_ratio
        )

        # UI (Pass I18nManager)
        self.ui = ATMUI(self.root, self.config, self.i18n)

        # Context
        self.shared_context = {}
        self.last_key_event = None
        self.last_trigger_gesture = None
        self.is_exiting = False

        # 離席判定用変数 (Absence Detection)
        self.normal_area = None
        self.absence_frames = 0
        self.grace_period_frames = 0
        self.ema_alpha = 0.05
        self.det_history = []
        self.last_trigger_gesture = None

        # State Machine
        self.state_machine = StateMachine(self, FaceAlignmentState)

        # UI Callback binding
        self.ui.set_language_callback(self.toggle_language)

    def toggle_language(self):
        """言語切り替え (JP <-> EN)"""
        current = self.i18n.current_lang
        # Simple toggle for now
        next_lang = "EN" if current == "JP" else "JP"

        print(f"Switching language to {next_lang}")
        self.i18n.set_language(next_lang)
        self.audio.set_language(next_lang)
        self.config["system"]["language"] = next_lang
        # Persist config if possible? ConfigLoader doesn't have save() shown yet.
        # But runtime update is sufficient for this session.

        self.audio.play_se("touch-button")

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

    # Audio methods moved to AudioManager, but keeping play_sound for temporary compatibility if needed
    # Better: Remove them and update states.py to use self.controller.audio.play()

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

            # 4. 離席判定ロジック
            self._handle_absence_detection(detection_result)

            # 5. ジェスチャー検証 (Lock機構など)
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

            # 5. デバッグオーバーレイ描画を削除 (Viewが担当)
            # if vision_conf.get("debug_overlay", False) or self.config["ui"].get("debug_mode", False):
            #     self._draw_debug_overlay(display_frame, detection_result, tracker_result)

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
        """デバッグ情報をフレームに描画 (Viewへ移動予定だが一時的に保持)"""
        # View側で実装済みのため、ここは空にするか削除する
        # 現状は呼び出し元がコメントアウトされているため安全
        pass

    def _handle_absence_detection(self, result):
        """
        利用者の離席を検知し、必要に応じて警告状態へ遷移させる。
        """
        # 特定の状態では判定を行わない (顔合わせ中、終了処理中、警告表示中)
        current_state = self.state_machine.current_state_name
        ignore_states = ["FaceAlignmentState", "UserAbsentWarningState", "WelcomeState"]
        if getattr(self, "is_exiting", False) or current_state in ignore_states:
            return

        # 復帰直後の猶予期間中
        if self.grace_period_frames > 0:
            self.grace_period_frames -= 1
            return

        person_count = result.get("person_count", 0)
        area = result.get("primary_person_area", 0.0)

        # 複数人検知時は判定を一時停止 (誤検知防止)
        if person_count >= 2:
            return

        # 履歴更新 (断続消失判定用)
        self.det_history.append(1 if person_count > 0 else 0)
        if len(self.det_history) > 60:
            self.det_history.pop(0)

        # 条件判定
        is_absent_suspicious = False

        # 条件A: 完全消失 (45フレーム)
        if person_count == 0:
            self.absence_frames += 1
            if self.absence_frames >= 45:
                is_absent_suspicious = True
        else:
            # 条件B: 面積縮小 (基準値の40%未満)
            if self.normal_area and area < (self.normal_area * 0.4):
                self.absence_frames += 1
                if self.absence_frames >= 45:
                    is_absent_suspicious = True
            else:
                self.absence_frames = 0
                # 基準面積の動的校正 (安定している場合のみEMAで更新)
                if self.normal_area and abs(area - self.normal_area) < (self.normal_area * 0.15):
                    self.normal_area = (self.ema_alpha * area) + ((1 - self.ema_alpha) * self.normal_area)

        # 条件C: 断続消失 (直近60フレームの傾向)
        if len(self.det_history) == 60:
            det_rate = sum(self.det_history) / 60
            # 連続検出の最大値を計測
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

        # 警告状態へ遷移
        if is_absent_suspicious:
            from src.core.states import UserAbsentWarningState
            self.change_state(UserAbsentWarningState)

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
            self.audio.play("come-again", force=True)
        except Exception:
            pass
        self.root.after(5000, self._finalize_exit)

    def _finalize_exit(self):
        try:
            self.audio.quit()
        except Exception:
            pass

        if hasattr(self, 'async_detector'):
            self.async_detector.release()

        self.camera.release()
        self.root.destroy()
        print("Exit complete")
