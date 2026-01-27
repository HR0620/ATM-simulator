"""
ATM UI デザインシステム

色、フォント、レイアウト定数を一元管理するモジュール。
UIの一貫性を保ち、変更を容易にする。
"""


class Colors:
    """カラーパレット定義"""
    # ブランドカラー（青系）
    PRIMARY = "#004080"
    PRIMARY_DARK = "#003366"
    PRIMARY_LIGHT = "#005bb5"

    # アクセントカラー
    ACCENT_ORANGE = "#e67e22"
    ACCENT_ORANGE_DARK = "#d35400"

    # ニュートラル
    WHITE = "#ffffff"
    OFF_WHITE = "#f5f5f5"
    LIGHT_GRAY = "#cccccc"
    GRAY = "#888888"
    DARK_GRAY = "#333333"
    BLACK = "#000000"

    # ステータス
    SUCCESS = "#00cc00"
    ERROR = "#cc0000"
    WARNING = "#ffcc00"

    # デバッグパネル
    DEBUG_BG = "#1a1a2e"
    DEBUG_BORDER = "#333366"
    DEBUG_HEADER = "#0d0d1a"
    DEBUG_ACCENT = "#00aaff"

    # ボタン用色マッピング
    BUTTON = {
        "left": {"bg": "#005bb5", "fg": WHITE, "pressed": "#003d7a"},
        "center": {"bg": OFF_WHITE, "fg": DARK_GRAY, "pressed": "#d0d0d0"},
        "right": {"bg": "#e67e22", "fg": WHITE, "pressed": "#b86b1d"},
    }


class Fonts:
    """フォント定義"""
    # 日本語対応フォント
    FAMILY = "Meiryo UI"
    FAMILY_MONO = "Consolas"

    # サイズ
    SIZE_TITLE = 28
    SIZE_HEADER = 20
    SIZE_BODY = 16
    SIZE_BUTTON = 28
    SIZE_SMALL = 12
    SIZE_TINY = 9

    @staticmethod
    def title():
        return (Fonts.FAMILY, Fonts.SIZE_TITLE, "bold")

    @staticmethod
    def header():
        return (Fonts.FAMILY, Fonts.SIZE_HEADER, "bold")

    @staticmethod
    def body():
        return (Fonts.FAMILY, Fonts.SIZE_BODY)

    @staticmethod
    def button():
        return (Fonts.FAMILY, Fonts.SIZE_BUTTON, "bold")

    @staticmethod
    def small():
        return (Fonts.FAMILY, Fonts.SIZE_SMALL)

    @staticmethod
    def tiny():
        return (Fonts.FAMILY, Fonts.SIZE_TINY)


class Layout:
    """レイアウト定数"""
    HEADER_HEIGHT = 80
    FOOTER_HEIGHT = 80
    DEBUG_PANEL_WIDTH = 200

    # ボタンパディング
    BUTTON_PADDING = 15

    # 押下時のオフセット（へこみ効果）
    PRESS_OFFSET = 4

    # 影の設定
    SHADOW_OFFSET = 4
    SHADOW_COLOR = "#00000066"  # 半透明黒
