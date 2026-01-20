import json
import os
import hashlib


class AccountManager:
    """
    口座情報の管理（読み込み・保存・認証・更新）を行うクラス。
    データは data/accounts.json に永続化される。
    """
    DATA_FILE = "data/accounts.json"

    def __init__(self, config=None):
        self.accounts = {}
        # 安全のためデフォルトソルトを設定（configがない場合）
        self.salt = "default_salt"
        self.max_amount = 999999
        self.max_pin_trials = 3

        if config and "security" in config:
            self.salt = config["security"].get("pin_salt", "default_salt")
            self.max_amount = config["security"].get("max_amount", 999999)
            self.max_pin_trials = config["security"].get("max_pin_trials", 3)

        # データディレクトリの作成を保証
        data_dir = os.path.dirname(self.DATA_FILE)
        if data_dir and not os.path.exists(data_dir):
            try:
                os.makedirs(data_dir)
            except OSError as e:
                print(f"ディレクトリ作成エラー: {e}")

        self.load_data()

    def load_data(self):
        """JSONファイルから口座データを読み込む"""
        if not os.path.exists(self.DATA_FILE):
            # ファイルがない場合は初期データを作成（デモ用）
            self.accounts = {
                "123456": {
                    "name": "デモタロウ",
                    "pin_hash": self._hash_pin("1234"),
                    "balance": 1000000,
                    "trials": 0,
                    "is_frozen": False
                }
            }
            self.save_data()
        else:
            try:
                with open(self.DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.accounts = data.get("accounts", {})
                    # 互換性のため、フィールドが欠けている場合は補完する
                    for acc in self.accounts.values():
                        if "trials" not in acc:
                            acc["trials"] = 0
                        if "is_frozen" not in acc:
                            acc["is_frozen"] = False
            except Exception as e:
                print(f"データ読み込みエラー: {e}")
                self.accounts = {}

    def save_data(self):
        """現在の口座データをJSONファイルに書き込む"""
        try:
            # 常に最新の状態を保存
            with open(self.DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    {"accounts": self.accounts},
                    f,
                    indent=4,
                    ensure_ascii=False
                )
        except Exception as e:
            print(f"データ保存エラー: {e}")

    def _hash_pin(self, pin):
        """PINコードをハッシュ化する（ソルト付きSHA256）"""
        # ソルト + PIN を結合してハッシュ化
        salted_pin = f"{self.salt}{pin}"
        return hashlib.sha256(salted_pin.encode()).hexdigest()

    def verify_pin(self, account_number, pin):
        """
        口座番号とPINが一致するか確認する
        Returns: 
            (True, 0): 成功
            (False, remaining): 失敗（残り回数を返す）
            (False, -1): 口座が凍結されている
            (False, -2): 口座が存在しない
        """
        if account_number not in self.accounts:
            return False, -2

        acc = self.accounts[account_number]
        if acc.get("is_frozen", False):
            return False, -1

        stored_hash = acc["pin_hash"]
        if stored_hash == self._hash_pin(pin):
            # 成功したら試行回数をリセット
            acc["trials"] = 0
            self.save_data()
            return True, 0
        else:
            # 失敗したら試行回数をインクリメント
            acc["trials"] += 1
            remaining = self.max_pin_trials - acc["trials"]

            if remaining <= 0:
                acc["is_frozen"] = True

            self.save_data()
            return False, remaining

    def is_frozen(self, account_number):
        """口座が凍結されているか確認する"""
        if account_number in self.accounts:
            return self.accounts[account_number].get("is_frozen", False)
        return False

    def get_account_name(self, account_number):
        """口座名義を取得する"""
        if account_number in self.accounts:
            return self.accounts[account_number]["name"]
        return None

    def get_balance(self, account_number):
        """残高を取得する"""
        if account_number in self.accounts:
            return self.accounts[account_number]["balance"]
        return 0

    def create_account(self, name, pin, initial_balance=0):
        """
        新規口座を作成する
        Returns: 作成された口座番号 (str)
        """
        import random
        # 6桁のランダムな口座番号を生成
        for _ in range(1000):
            account_number = str(random.randint(100000, 999999))
            if account_number not in self.accounts:
                break
        else:
            raise Exception("口座番号の生成に失敗しました")

        self.accounts[account_number] = {
            "name": name,
            "pin_hash": self._hash_pin(pin),
            "balance": initial_balance,
            "trials": 0,
            "is_frozen": False
        }
        self.save_data()
        return account_number

    def withdraw(self, account_number, amount):
        """
        引き出し処理
        Returns: (success: bool, message: str)
        """
        if account_number not in self.accounts:
            return False, "口座が存在しません"

        acc = self.accounts[account_number]
        if acc.get("is_frozen", False):
            return False, "該当口座は凍結されています"

        if amount > self.max_amount:
            return False, f"取引上限額({self.max_amount}円)を超えています"

        if amount <= 0:
            return False, "金額が不正です"

        current_balance = acc["balance"]
        if current_balance < amount:
            return False, "残高不足です"

        acc["balance"] -= amount
        self.save_data()
        return True, "引き出し完了"

    def deposit(self, account_number, amount):
        """
        預け入れ（振込受け取り）処理
        Returns: (success: bool, message: str)
        """
        if account_number not in self.accounts:
            return False, "振込先口座が存在しません"

        if self.accounts[account_number].get("is_frozen", False):
            return False, "振込先口座が凍結されています"

        if amount > self.max_amount:
            return False, f"取引上限額({self.max_amount}円)を超えています"

        if amount <= 0:
            return False, "金額が不正です"

        self.accounts[account_number]["balance"] += amount
        self.save_data()
        return True, "振込完了"

    def transfer(self, source_account, target_account, amount):
        # 現金振込として実装（対象口座にお金を増やすだけ）
        return self.deposit(target_account, amount)
