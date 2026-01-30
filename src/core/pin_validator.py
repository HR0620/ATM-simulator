"""
PIN安全性チェックモジュール

暗証番号（PIN）の安全性を判定するロジックを提供します。
"""


def is_valid_pin(pin: str) -> tuple[bool, str]:
    """
    暗証番号の安全性をチェックします。

    Args:
        pin (str): 4桁の数字文字列

    Returns:
        tuple[bool, str]: (判定結果, NG理由)
            - 判定結果: 安全なら True, 安全でないなら False
            - NG理由: 安全でない場合の日本語メッセージ。安全な場合は空文字列。
    """
    # 前提チェック: 4桁の数字文字列であること
    if not (len(pin) == 4 and pin.isdigit()):
        return False, "暗証番号は4桁の数字で入力してください"

    # 1. 同一数字の4連続は禁止 (例: 1111, 0000)
    # なぜNGなのか: 非常に推測されやすく、セキュリティが低いため
    if len(set(pin)) == 1:
        return False, "安全性の低い暗証番号は使用できません"

    # 2. 単純な「+1連番」は禁止 (例: 0123, 1234)
    # ただし 7890, 8901 は許可する (単純な +1 のみを見る)
    # なぜNGなのか: 連番は推測されやすく、攻撃の対象になりやすいため
    is_sequential = True
    for i in range(1, 4):
        prev_digit = int(pin[i - 1])
        curr_digit = int(pin[i])
        if curr_digit != prev_digit + 1:
            is_sequential = False
            break

    if is_sequential:
        return False, "安全性の低い暗証番号は使用できません"

    # 3. 生年月日と推測されやすい並びは禁止 (MMDD, DDMM)
    # 月(01-12) + 日(01-31) の範囲に収まるものを NG とする
    # なぜNGなのか: 誕生日に関連する数字は、個人特定から最も推測されやすいため

    # 3-1. MMDD 形式のチェック
    month_mm = int(pin[0:2])
    day_dd = int(pin[2:4])
    if 1 <= month_mm <= 12 and 1 <= day_dd <= 31:
        return False, "安全性の低い暗証番号は使用できません"

    # 3-2. DDMM 形式のチェック
    day_ord = int(pin[0:2])
    month_ord = int(pin[2:4])
    if 1 <= month_ord <= 12 and 1 <= day_ord <= 31:
        return False, "安全性の低い暗証番号は使用できません"

    # すべてのチェックを通過
    return True, ""
