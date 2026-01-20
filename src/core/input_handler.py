import random


class PinPad:
    """
    ランダム暗証番号入力パッドのロジック。
    物理キー 't', 'y', 'u', 'g', 'h', 'j', 'v', 'b', 'n', 'm' を
    0〜9の数字にランダムに割り当てる。
    """
    PHYSICAL_KEYS = ['t', 'y', 'u', 'g', 'h', 'j', 'v', 'b', 'n', 'm']
    # 画面表示用のレイアウト（3x3 + 1）
    GRID_LAYOUT = [
        ['t', 'y', 'u'],
        ['g', 'h', 'j'],
        ['v', 'b', 'n'],
        [None, 'm', None]  # mは0の位置（下段中央）
    ]

    def __init__(self):
        self.key_mapping = {}   # physical_key -> number
        self.display_map = {}   # physical_key -> number (UI表示用)
        self.reset_random_mapping()

    def reset_random_mapping(self):
        """数字の割り当てをシャッフルする"""
        numbers = list(range(10))  # 0-9
        random.shuffle(numbers)

        self.key_mapping = {}
        for i, key in enumerate(self.PHYSICAL_KEYS):
            self.key_mapping[key] = str(numbers[i])

        # 表示用にも保持（UIからアクセスする）
        self.display_map = self.key_mapping.copy()

    def get_number(self, key):
        """物理キーに対応する数字を返す。無効ならNone。"""
        return self.key_mapping.get(key)

    def get_layout_info(self):
        """UI描画用の情報を返す (key, allocated_number) の2次元リスト"""
        layout_data = []
        for row in self.GRID_LAYOUT:
            row_data = []
            for key in row:
                if key:
                    row_data.append({"key": key, "num": self.key_mapping[key]})
                else:
                    row_data.append(None)
            layout_data.append(row_data)
        return layout_data


class NumericInputBuffer:
    """
    数値入力（口座番号・金額・PIN）のバッファ管理クラス
    """

    def __init__(self, max_length=10, is_pin=False):
        self.buffer = ""
        self.max_length = max_length
        self.is_pin = is_pin  # PINモードならアスタリスク表示用

    def add_char(self, char):
        """文字を追加（数字のみ）"""
        if len(self.buffer) < self.max_length:
            if char.isdigit():
                self.buffer += char
                return True
        return False

    def backspace(self):
        """一文字消去"""
        self.buffer = self.buffer[:-1]

    def clear(self):
        self.buffer = ""

    def get_value(self):
        return self.buffer

    def get_display_value(self):
        """画面表示用の値を返す（PINならマスクする）"""
        if self.is_pin:
            return "*" * len(self.buffer)
        return self.buffer
