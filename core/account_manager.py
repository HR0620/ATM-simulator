import json
import os
import hashlib


class AccountManager:
    """
    口座情報の管理（読み込み・保存・認証・更新）を行うクラス。
    データは data/accounts.json に永続化される。
    """
    DATA_FILE = "data/accounts.json"

    def __init__(self):
        self.accounts = {}
        self.load_data()

    def load_data(self):
        """JSONファイルから口座データを読み込む"""
        if not os.path.exists(self.DATA_FILE):
            # ファイルがない場合は初期データを作成（デモ用）
            self.accounts = {
                "1234567890": {
                    "name": "デモタロウ",
                    "pin_hash": self._hash_pin("1234"),
                    "balance": 1000000
                }
            }
            self.save_data()
        else:
            try:
                with open(self.DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.accounts = data.get("accounts", {})
            except Exception as e:
                print(f"データ読み込みエラー: {e}")
                self.accounts = {}

    def save_data(self):
        """現在の口座データをJSONファイルに書き込む"""
        try:
            with open(self.DATA_FILE, "w", encoding="utf-8") as f:
                json.dump({"accounts": self.accounts}, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"データ保存エラー: {e}")

    def _hash_pin(self, pin):
        """PINコードをハッシュ化する（簡易的なセキュリティ）"""
        return hashlib.sha256(pin.encode()).hexdigest()

    def verify_pin(self, account_number, pin):
        """
        口座番号とPINが一致するか確認する
        Returns: True/False
        """
        if account_number not in self.accounts:
            return False

        stored_hash = self.accounts[account_number]["pin_hash"]
        return stored_hash == self._hash_pin(pin)

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
        # 簡易的にランダムな10桁の数字を生成（既存との重複チェック付き）
        import random
        while True:
            account_number = str(random.randint(1000000000, 9999999999))
            if account_number not in self.accounts:
                break

        self.accounts[account_number] = {
            "name": name,
            "pin_hash": self._hash_pin(pin),
            "balance": initial_balance
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

        current_balance = self.accounts[account_number]["balance"]
        if current_balance < amount:
            return False, "残高不足です"

        self.accounts[account_number]["balance"] -= amount
        self.save_data()
        return True, "引き出し完了"

    def deposit(self, account_number, amount):
        """
        預け入れ（振込受け取り）処理
        Returns: (success: bool, message: str)
        """
        if account_number not in self.accounts:
            # 振込先が存在しない場合でも、シミュレーターとしては
            # エラーにするか、架空の口座として許可するか。
            # 今回は厳密にチェックする。
            return False, "振込先口座が存在しません"

        self.accounts[account_number]["balance"] += amount
        self.save_data()
        return True, "振込完了"

    def transfer(self, source_account, target_account, amount):
        # 現金振込として実装（対象口座にお金を増やすだけ）
        return self.deposit(target_account, amount)
