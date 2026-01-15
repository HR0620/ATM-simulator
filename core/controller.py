import tkinter as tk
import yaml
import traceback
from vision.camera_manager import CameraManager
from ai.model_loader import AIModel
from core.face_checker import FacePositionChecker
from core.gesture_validator import GestureValidator
from ui.screens import FaceGuideScreen, ATMUI


class ATMController:
    """
    アプリケーション全体の制御を行うクラス。
    MVCモデルのControllerに相当し、カメラ・識別ロジック・UIを橋渡しする。
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

        # --- モジュール初期化 ---
        print("モジュールを初期化しています...")

        self.camera = CameraManager(
            device_id=self.config["camera"]["device_id"],
            width=self.config["camera"]["width"],
            height=self.config["camera"]["height"]
        )

        self.ai_model = AIModel(
            model_path=self.config["model"]["path"],
            labels_path=self.config["model"]["labels_path"]
        )

        self.face_checker = FacePositionChecker(
            required_frames=self.config["face_guide"]["required_frames"],
            guide_box_ratio=self.config["face_guide"]["guide_box_ratio"]
        )

        self.gesture_validator = GestureValidator(
            required_frames=self.config["gesture"]["required_frames"],
            confidence_threshold=self.config["gesture"]["confidence_threshold"],
            free_class=self.config["gesture"]["free_class_name"]
        )

        # --- アプリ状態管理 ---
        self.current_screen = None
        self.is_atm_active = False  # TrueならATM操作画面、Falseなら顔認証画面

        # アプリ開始
        print("カメラを開始します...")
        self.camera.start()

        # 最初の画面を表示
        self.show_face_guide()

        # メインループ開始
        self.update_loop()

    def show_face_guide(self):
        """顔認証ガイド画面に切り替える"""
        if self.current_screen:
            self.current_screen.destroy()

        self.is_atm_active = False
        self.face_checker.reset()  # カウンタリセット
        self.current_screen = FaceGuideScreen(self.root, self.config)
        print("画面切替: 顔認証ガイド")

    def show_atm_ui(self):
        """ATM操作画面に切り替える"""
        if self.current_screen:
            self.current_screen.destroy()

        self.is_atm_active = True
        self.current_screen = ATMUI(self.root, self.config)
        print("画面切替: ATM操作")

    def update_loop(self):
        """
        メインの更新ループ。約33ms毎(30fps)に呼び出される。
        カメラ画像を取得し、現在の状態に応じて処理を分岐する。
        """
        try:
            # 1. カメラ画像取得
            frame = self.camera.get_frame()
            if frame is None:
                # 数フレーム失敗設定ならエラーだが、ここでは単にスキップして再試行
                self.root.after(100, self.update_loop)
                return

            stop_loop_this_turn = False  # 画面遷移時は二重スケジュールを防ぐ

            if not self.is_atm_active:
                # --- 顔認証モード ---
                # 処理実行
                status, guide_box, face_rect = self.face_checker.process(frame)

                # UI更新
                if self.current_screen and hasattr(self.current_screen, 'update_image'):
                    self.current_screen.update_image(frame, status, guide_box, face_rect)

                # 認証完了チェック
                if status == "confirmed":
                    print("認証完了。ATM画面へ遷移します。")
                    # 1秒後に遷移（ユーザーに完了画面を見せるため）
                    self.root.after(1000, self.transition_to_atm)
                    stop_loop_this_turn = True

            else:
                # --- ATM操作モード ---
                # AI予測実行
                prediction = self.ai_model.predict(frame)
                # ジェスチャー安定化フィルタ
                gesture = self.gesture_validator.validate(prediction)

                # UI更新
                if self.current_screen and hasattr(self.current_screen, 'update_state'):
                    self.current_screen.update_state(gesture, frame)

            # 次のフレーム呼び出しを予約
            if not stop_loop_this_turn:
                self.root.after(33, self.update_loop)

        except Exception as e:
            # 万が一ループ内でエラーが起きてもアプリ全体を落とさない
            print(f"メインループ内で予期せぬエラー: {e}")
            traceback.print_exc()
            # 1秒後に再開を試みる
            self.root.after(1000, self.update_loop)

    def transition_to_atm(self):
        """遅延実行用のラッパーメソッド"""
        self.show_atm_ui()
        # 画面切替後にループが止まらないよう、明示的にループを再開するケースもあるが、
        # update_loop構造上、画面切り替え時にループ停止フラグを立てていたなら、ここで再開が必要。
        # 今回の設計では transition 前に stop_loop_this_turn=True にしているので、
        # ここで新しくループをキックする。
        self.update_loop()

    def on_close(self):
        """アプリ終了時のクリーンアップ"""
        print("アプリを終了します...")
        self.camera.release()
        self.root.destroy()
        print("終了完了")
