"""
ジェスチャー検証モジュール

設計意図:
- 確定直後に即座にロック状態に入り、連続誤作動を防ぐ
- ロック解除は「時間経過」または「freeポーズ検出」のいずれか早い方
- UI用の進捗情報を提供 (get_progress)
"""
import time


class GestureValidator:
    """
    AIの予測結果を検証し、誤動作を防ぐためのクラス。
    確定後のロック機構により、連続誤作動と遅延の両方を解決。
    """

    def __init__(self, required_frames=5, confidence_threshold=0.7,
                 free_class="free", lock_duration=0.5):
        """
        Args:
            required_frames: 確定に必要な連続フレーム数
            confidence_threshold: これ未満の確信度は無視
            free_class: 操作なしとみなすクラス名
            lock_duration: 確定後のロック時間（秒）
        """
        self.required_frames = required_frames
        self.confidence_threshold = confidence_threshold
        self.free_class = free_class
        self.lock_duration = lock_duration

        self._consecutive_count = 0
        self._last_class = None
        self._locked_until = 0  # ロック解除時刻 (UNIX timestamp)

    def validate(self, prediction: dict) -> str | None:
        """
        最新の予測結果を検証し、確定したジェスチャーを返す。

        Returns:
            確定したジェスチャー名 or None
        """
        if prediction is None:
            return None

        now = time.time()

        # ロック中は何も返さない（ただしfreeでロック解除可能）
        if now < self._locked_until:
            if prediction["class_name"] == self.free_class:
                self._locked_until = 0  # 早期ロック解除
            return None

        class_name = prediction["class_name"]
        confidence = prediction["confidence"]

        # 信頼度不足 or freeクラス → リセット
        if confidence < self.confidence_threshold or class_name == self.free_class:
            self._reset_streak()
            return None

        # 連続性チェック
        if class_name == self._last_class:
            self._consecutive_count += 1
        else:
            self._consecutive_count = 1
            self._last_class = class_name

        # 確定判定
        if self._consecutive_count >= self.required_frames:
            self._confirm_and_lock()
            return class_name

        return None

    def _reset_streak(self):
        """連続カウントをリセット"""
        self._consecutive_count = 0
        self._last_class = None

    def _confirm_and_lock(self):
        """確定直後: カウンタリセット + ロック開始"""
        self._reset_streak()
        self._locked_until = time.time() + self.lock_duration

    def force_reset(self):
        """外部（StateMachine）からの強制リセット"""
        self._reset_streak()
        self._locked_until = time.time() + self.lock_duration

    def get_progress(self) -> float:
        """UI用: 0.0〜1.0 の確定進捗率"""
        if self._last_class is None:
            return 0.0
        return min(1.0, self._consecutive_count / self.required_frames)

    def get_current_direction(self) -> str | None:
        """現在認識中の方向を返す (進捗表示用)"""
        return self._last_class

    def is_locked(self) -> bool:
        """ロック中かどうか"""
        return time.time() < self._locked_until
