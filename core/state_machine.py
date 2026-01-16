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

    def update(self, frame, gesture, key_event=None):
        """
        フレームごとの更新処理
        Args:
            frame: カメラ映像（反転済み）
            gesture: 認識されたジェスチャー ("left", "center", "right", "free")
            key_event: キーボード入力イベント (あれば)
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

    def update(self, frame, gesture, key_event=None):
        """現在の状態のupdateメソッドを呼ぶ"""
        if self.current_state:
            self.current_state.update(frame, gesture, key_event)
