class GestureValidator:
    """
    AIの予測結果を検証し、誤動作を防ぐためのクラス。
    「free（何もしていない）」状態の除外や、連続フレームでの一致確認を行う。
    """

    def __init__(self, required_frames=5, confidence_threshold=0.85, free_class="free"):
        """
        Args:
            required_frames (int): 確定に必要な連続フレーム数
            confidence_threshold (float): これ未満の確信度は無視する
            free_class (str): 操作なしとみなすクラス名
        """
        self.required_frames = required_frames
        self.confidence_threshold = confidence_threshold
        self.free_class = free_class

        self.consecutive_frames = 0
        self.last_prediction = None
        self.confirmed_gesture = self.free_class

    def validate(self, prediction):
        """
        最新の予測結果を検証し、安定したジェスチャー判定を返す。

        Args:
             prediction (dict): AIModelからの出力 {"class_name": str, "confidence": float}

        Returns:
            str: 確定したジェスチャー名（または free）
        """
        if prediction is None:
            return self.free_class

        class_name = prediction["class_name"]
        confidence = prediction["confidence"]

        # 1. 確信度が低い、または「free」クラスの場合はカウントリセット
        if confidence < self.confidence_threshold or class_name == self.free_class:
            self.consecutive_frames = 0
            self.last_prediction = None
            return self.free_class

        # 2. 前回の予測と同じクラスか確認
        if class_name == self.last_prediction:
            self.consecutive_frames += 1
        else:
            self.consecutive_frames = 1  # 違うクラスになったら1から数え直し
            self.last_prediction = class_name

        # 3. 指定フレーム数連続したら確定
        if self.consecutive_frames >= self.required_frames:
            self.confirmed_gesture = class_name
            return self.confirmed_gesture
        return self.free_class
