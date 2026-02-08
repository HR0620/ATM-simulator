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
        # メイン状態
        self.current_state = initial_state_cls(self.controller)
        self.current_state_name = initial_state_cls.__name__
        self.last_audio_key = None

        # モーダルスタック
        self.modal_stack = []

    def start(self):
        """最初の状態を開始"""
        self.current_state.on_enter()

    def change_state(self, next_state_cls):
        """状態を遷移させる (モーダルはクリアされる)"""
        # モーダルがあればすべて閉じる
        while self.modal_stack:
            self.pop_modal()

        if self.current_state:
            self.current_state.on_exit()

        prev_state = self.current_state
        self.current_state = next_state_cls(self.controller)
        self.current_state_name = next_state_cls.__name__

        print(f"State Transition: {prev_state.__class__.__name__} -> {self.current_state_name}")
        self.current_state.on_enter(prev_state=prev_state)

    def push_modal(self, modal_state_cls):
        """モーダル状態をスタックに積む"""
        print(f"Push Modal: {modal_state_cls.__name__}")
        modal = modal_state_cls(self.controller)
        self.modal_stack.append(modal)
        modal.on_enter()

    def pop_modal(self):
        """最前面のモーダルを閉じる"""
        if self.modal_stack:
            modal = self.modal_stack.pop()
            print(f"Pop Modal: {modal.__class__.__name__}")
            modal.on_exit()

    def update(self, frame, gesture, key_event=None, progress=0,
               current_direction=None, debug_info=None):
        """現在の（最前面の）状態のupdateメソッドを呼ぶ"""

        # 1. 判定対象の状態を決定 (モーダルがあればそちらが優先)
        active_state = self.modal_stack[-1] if self.modal_stack else self.current_state

        # 2. State Update
        if active_state:
            active_state.update(
                frame, gesture, key_event, progress,
                current_direction, debug_info
            )

        # 3. Audio Policy Check
        from src.core.audio_policy import AudioPolicy

        target_key = AudioPolicy.get_audio_key(
            active_state,
            self.controller.shared_context
        )

        if target_key:
            if target_key != self.last_audio_key:
                print(f"AudioPolicy Trigger: {self.last_audio_key} -> {target_key}")
                self.controller.audio.play_voice(target_key)
                self.last_audio_key = target_key
        else:
            self.last_audio_key = None
