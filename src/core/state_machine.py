class State:
    """
    ATMの各状態（画面・処理ステップ）の基底クラス
    """

    def __init__(self, controller):
        self.controller = controller

    def on_enter(self, prev_state=None):
        """状態に入った時の処理（UI初期化、音声再生など）"""
        pass

    def on_exit(self):
        """状態から出る時の処理"""
        pass

    def update(self, frame, gesture, key_event=None, progress=0,
               current_direction=None, debug_info=None):
        """
        フレームごとの更新処理
        Args:
            frame: カメラ映像（反転済み）
            gesture: 確定したジェスチャー (None or "left", "center", "right")
            key_event: キーボード入力イベント (あれば)
            progress: ジェスチャー認識進捗 (0.0〜1.0)
            current_direction: 現在認識中の方向
            debug_info: デバッグ情報 (AI予測など)
        """
        pass


class StateMachine:
    """
    状態遷移を管理するクラス
    """

    def __init__(self, controller, initial_state_cls):
        self.controller = controller
        # 初期状態はインスタンス化せず、クラスだけ渡しておく
        self.current_state = initial_state_cls(self.controller)
        self.current_state_name = initial_state_cls.__name__
        self.last_audio_key = None

        # Initial Audio Trigger (for first state)
        # Note: We rely on the first update loop to trigger this,
        # but pure StateMachine instantiation usually happens before loop starts.

    def start(self):
        """最初の状態を開始"""
        self.current_state.on_enter()

    def change_state(self, next_state_cls):
        """状態を遷移させる"""
        if self.current_state:
            self.current_state.on_exit()

        # 前の状態を保持しておきたい場合などはここで保存可能
        prev_state = self.current_state

        # 新しい状態を生成して切り替え
        self.current_state = next_state_cls(self.controller)
        self.current_state_name = next_state_cls.__name__

        print(f"State Transition: {prev_state.__class__.__name__} -> {self.current_state_name}")
        self.current_state.on_enter(prev_state=prev_state)

    def update(self, frame, gesture, key_event=None, progress=0,
               current_direction=None, debug_info=None):
        """現在の状態のupdateメソッドを呼ぶ"""

        # 1. State Update
        if self.current_state:
            self.current_state.update(
                frame, gesture, key_event, progress, current_direction, debug_info
            )

        # 2. Audio Policy Check
        # Check if the current state/context dictates a new audio key
        # We do this AFTER update in case the state changed context during update
        from src.core.audio_policy import AudioPolicy

        target_key = AudioPolicy.get_audio_key(
            self.current_state,
            self.controller.shared_context
        )

        if target_key:
            if target_key != self.last_audio_key:
                print(f"AudioPolicy Trigger: {self.last_audio_key} -> {target_key}")
                self.controller.audio.play_voice(target_key)
                self.last_audio_key = target_key
        else:
            # If policy returns None, we usually do nothing (keep laying? or stop?)
            # Usually we don't stop voice guide abruptly unless specific requirement.
            # But if the state changed to one with NO audio, maybe we should?
            # User spec: "State transition -> Audio".
            # If target is None, it means "No Voice for this state".
            # Reset detection so if we go back to a state WITH audio, it plays.
            self.last_audio_key = None
