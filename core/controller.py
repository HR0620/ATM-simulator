import tkinter as tk
import yaml
import traceback
import cv2
import pygame
import os
from vision.camera_manager import CameraManager
from ai.model_loader import AIModel
from ui.screens import ATMUI
from core.gesture_validator import GestureValidator
from core.state_machine import StateMachine
from core.states import MenuState, FaceAlignmentState
from core.account_manager import AccountManager
from core.input_handler import PinPad


class ATMController:
    """
    アプリケーション全体の制御を行うクラス。
    State Machineを保持し、メインループを回す。
    """

    def __init__(self, root):
        self.root = root

        # 設定ファイルのロード
        try:
            with open("config/atm_config.yml", "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f)
        except Exception as e:
            print(f"設定ファイルの読み込みに失敗しました: {e}")
            raise e

        # ウィンドウ設定
        self.root.title(self.config["ui"]["title"])
        self.root.geometry(f"{self.config['ui']['window_width']}x{self.config['ui']['window_height']}")

        # キーボード入力バインディング
        self.root.bind("<Key>", self._on_key_press)
        # ESCキーで終了
        self.root.bind("<Escape>", lambda e: self.on_close())

        # --- モジュール初期化 ---
        print("モジュールを初期化しています...")

        try:
            pygame.mixer.init()
        except Exception as e:
            print(f"Warning: Audio mixer failed to initialize: {e}")

        self.camera = CameraManager(
            device_id=self.config["camera"]["device_id"],
            width=self.config["camera"]["width"],
            height=self.config["camera"]["height"]
        )

        self.ai_model = AIModel(
            model_path=self.config["model"]["path"],
            labels_path=self.config["model"]["labels_path"]
        )

        self.gesture_validator = GestureValidator(
            required_frames=self.config["gesture"]["required_frames"],
            confidence_threshold=self.config["gesture"]["confidence_threshold"],
            free_class=self.config["gesture"]["free_class_name"]
        )

        # 新しいモジュール
        self.account_manager = AccountManager()
        self.pin_pad = PinPad()

        # 顔位置判定
        from core.face_checker import FacePositionChecker
        self.face_checker = FacePositionChecker(required_frames=30)  # 1秒程度 (30FPS想定)

        # UI初期化
        self.ui = ATMUI(self.root, self.config)

        # コンテキスト（State間で共有するデータ）
        self.shared_context = {}

        # 入力制御用 (チャタリング防止)
        self.last_input_time = 0
        self.input_cooldown = 1.0  # 秒

        # ステートマシン初期化 (初期状態: FaceAlignmentState)
        self.state_machine = StateMachine(self, FaceAlignmentState)

        # キーイベントバッファ
        self.last_key_event = None

        # アプリ開始
        print("カメラを開始します...")
        self.camera.start()

        self.state_machine.start()
        self.update_loop()

    def _on_key_press(self, event):
        """キー入力を保存し、次のupdateループで処理する"""
        if event.keysym != "Escape":  # ESCは別枠
            self.last_key_event = event

    def change_state(self, next_state_cls):
        """ステートマシンへのプロキシ"""
        self.state_machine.change_state(next_state_cls)
        # 状態遷移時もクールダウンを入れる（誤操作防止）
        self.trigger_cooldown()

    def is_input_allowed(self):
        """クールダウン中かどうか判定"""
        import time
        return (time.time() - self.last_input_time) > self.input_cooldown

    def trigger_cooldown(self):
        """入力を受け付けたのでクールダウンを開始"""
        import time
        self.last_input_time = time.time()

    def _play_sound(self, filename):
        """
        音声を再生するヘルパーメソッド。
        Args:
            filename (str): assets/sounds/ 以下のファイル名 (拡張子なし)
        """
        if not pygame.mixer.get_init():
            return

        # 拡張子の候補 (ユーザーはmp3を持っているためmp3を優先)
        extensions = [".mp3", ".mp4", ".wav"]
        target_path = None

        base_path = os.path.join("assets", "sounds", filename)

        for ext in extensions:
            p = base_path + ext
            if os.path.exists(p):
                target_path = p
                break

        if target_path is None:
            # print(f"音声ファイルが見つかりません: {base_path}")
            return

        try:
            pygame.mixer.music.load(target_path)
            pygame.mixer.music.play()
        except Exception as e:
            print(f"音声再生エラー ({target_path}): {e}")

    # 公開用エイリアス
    def play_sound(self, filename):
        self._play_sound(filename)

    def update_loop(self):
        """
        メインの更新ループ。
        """
        try:
            # 1. カメラ画像取得
            raw_frame = self.camera.get_frame()
            if raw_frame is None:
                self.root.after(100, self.update_loop)
                return

            # 2. 表示用・座標計算用に左右反転したフレームを作る
            display_frame = cv2.flip(raw_frame, 1)

            # 3. AI予測
            prediction = self.ai_model.predict(display_frame)
            gesture = self.gesture_validator.validate(prediction)

            # 4. State更新
            key_event = self.last_key_event
            self.last_key_event = None  # 消費

            self.state_machine.update(display_frame, gesture, key_event)

            # 5. 次フレーム
            self.root.after(33, self.update_loop)

        except Exception as e:
            print(f"メインループ内で予期せぬエラー: {e}")
            traceback.print_exc()
            self.root.after(1000, self.update_loop)

    def on_close(self):
        """アプリ終了時のクリーンアップ"""
        print("アプリを終了します...")
        try:
            self._play_sound("come-again")
        except:
            pass

        self.root.after(1500, self._finalize_exit)

    def _finalize_exit(self):
        try:
            pygame.mixer.quit()
        except:
            pass
        self.camera.release()
        self.root.destroy()
        print("終了完了")
