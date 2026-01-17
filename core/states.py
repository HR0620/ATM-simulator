from core.state_machine import State
from core.input_handler import NumericInputBuffer


class FaceAlignmentState(State):
    """
    起動時、顔が枠内に収まっているか確認するステート
    """

    def on_enter(self, prev_state=None):
        self.controller.ui.clear_content()
        self.controller.ui.set_header("本人確認")
        # ガイドなどは update_background で描画される

    def update(self, frame, gesture, key_event=None):
        # 顔位置判定
        if hasattr(self.controller, 'face_checker'):
            status, guide_box, face_rect = self.controller.face_checker.process(frame)

            # UI更新 (Guide overlay)
            self.controller.ui.update_background(frame, face_result=(status, guide_box, face_rect))

            if status == "confirmed":
                self.controller.play_sound("open-window")  # 成功音
                self.controller.trigger_cooldown()
                self.controller.change_state(MenuState)

        else:
            # face_checkerがない場合（テスト時など）はスキップ
            self.controller.ui.update_background(frame)
            self.controller.change_state(MenuState)

    def on_exit(self):
        pass


class MenuState(State):
    """
    メインメニュー状態
    左：振込、中：引出、右：口座作成
    """

    def on_enter(self, prev_state=None):
        # 専用のメインメニューレイアウトを表示
        self.controller.ui.show_main_menu()

        # 音声再生
        self.controller.play_sound("irassyaimase")
        # コンテキストクリア
        self.controller.shared_context = {}

    def update(self, frame, gesture, key_event=None):
        self.controller.ui.update_background(frame)

        if gesture == "left":
            # 振込フローへ (認証なし、単純な入金扱い)
            self.controller.shared_context = {"transaction": "transfer"}
            self.controller.change_state(TransferTargetInputState)

        elif gesture == "center":
            # 引き出しフローへ
            self.controller.shared_context = {"transaction": "withdraw"}
            self.controller.change_state(WithdrawAccountInputState)

        elif gesture == "right":
            # 口座作成フローへ
            self.controller.shared_context = {"transaction": "create_account"}
            self.controller.change_state(CreateAccountNameInputState)

# --- 共通部品: 完了画面 ---


class ResultState(State):
    def on_enter(self, prev_state=None):
        self.controller.ui.clear_content()  # 前の画面を消去
        self.controller.ui.set_header("手続き完了")
        msg = "お手続きが完了しました。"
        if "result_message" in self.controller.shared_context:
            msg += "\n" + self.controller.shared_context["result_message"]

        self.controller.ui.show_message(msg, visible=True)
        self.controller.ui.show_selection_guides(left_text=None, right_text=None)

        self.controller.play_sound("come-again")

        # 3.5秒後にメニューへ
        self.controller.root.after(3500, lambda: self.controller.change_state(MenuState))

    def update(self, frame, gesture, key_event=None):
        self.controller.ui.update_background(frame)
        # 入力無視

# --- 振込フロー (Account -> Amount -> Check -> Done) ---
# ※ 左ボタン仕様: "振込先口座番号(10桁)を入力" -> "金額を入力" -> ...
# 認証がないため、NumericInputState をつなげて実装する


class TransferTargetInputState(State):
    def on_enter(self, prev_state=None):
        self.controller.ui.clear_content()
        self.controller.ui.set_header("振込先指定")
        self.controller.ui.show_message("振込先の口座番号を入力してください(キーボード)", visible=True)
        self.input_buffer = NumericInputBuffer(max_length=10, is_pin=False)
        self.controller.ui.show_input_field(self.input_buffer.get_display_value(), visible=True)
        self.controller.ui.show_selection_guides(right_text="戻る")  # 右手＝キャンセル的に使う

    def update(self, frame, gesture, key_event=None):
        self.controller.ui.update_background(frame)

        if gesture == "right":
            self.controller.change_state(MenuState)
            return

        if key_event:
            char = key_event.char
            if char.isdigit():
                if len(self.input_buffer.get_value()) < 7:
                    if self.input_buffer.add_char(char):
                        self.controller.play_sound("pushenter")
            elif key_event.keysym == "BackSpace":
                self.input_buffer.backspace()
                self.controller.play_sound("pushenter")
            elif key_event.keysym == "Return":
                # エンターキーで確定
                if len(self.input_buffer.get_value()) > 0:
                    self.controller.shared_context["target_account"] = self.input_buffer.get_value()
                    self.controller.play_sound("pushenter")
                    self.controller.trigger_cooldown()
                    self.controller.change_state(GenericAmountInputState)

        self.controller.ui.show_fixed_input_field(self.input_buffer.get_display_value(), max_digits=7)


class GenericAmountInputState(State):
    """汎用金額入力画面"""

    def on_enter(self, prev_state=None):
        self.controller.ui.clear_content()
        self.controller.ui.set_header("金額入力")
        self.controller.ui.show_message("金額を入力してください(キーボード)", visible=True)
        self.input_buffer = NumericInputBuffer(max_length=8, is_pin=False)  # 1億円未満
        self.controller.ui.show_input_field(self.input_buffer.get_display_value() + " 円", visible=True)
        self.controller.ui.show_selection_guides(right_text="戻る")

    def update(self, frame, gesture, key_event=None):
        self.controller.ui.update_background(frame)

        if gesture == "right":
            # 戻るロジック（簡易的にメニューへ）
            self.controller.change_state(MenuState)
            return

        if key_event:
            char = key_event.char
            if char.isdigit():
                if self.input_buffer.add_char(char):
                    self.controller.play_sound("pushenter")
            elif key_event.keysym == "BackSpace":
                self.input_buffer.backspace()
                self.controller.play_sound("pushenter")
            elif key_event.keysym == "Return":
                if len(self.input_buffer.get_value()) > 0:
                    self.controller.shared_context["amount"] = int(self.input_buffer.get_value())
                    self.controller.play_sound("pushenter")
                    self.controller.change_state(ConfirmationState)

        self.controller.ui.show_input_field(self.input_buffer.get_display_value() + " 円", visible=True)


class ConfirmationState(State):
    """汎用確認画面"""

    def on_enter(self, prev_state=None):
        self.controller.ui.clear_content()
        self.controller.ui.set_header("確認")

        # コンテキストに応じてメッセージを変える
        txn = self.controller.shared_context.get("transaction")
        msg = ""
        if txn == "transfer":
            target = self.controller.shared_context.get("target_account")
            amt = self.controller.shared_context.get("amount")
            msg = f"口座番号: {target}\n振込金額: {amt}円\n\nよろしいですか？"
        elif txn == "withdraw":
            amt = self.controller.shared_context.get("amount")
            msg = f"引出金額: {amt}円\n\nよろしいですか？"
        elif txn == "create_account":
            name = self.controller.shared_context.get("name")
            msg = f"お名前: {name}\n\nこの内容で作成しますか？"

        self.controller.ui.show_message(msg, visible=True)
        self.controller.ui.show_input_field("", visible=False)
        self.controller.ui.show_keypad([], visible=False)
        self.controller.ui.show_selection_guides(left_text="はい", right_text="いいえ")

        self.controller.play_sound("check-money")

    def update(self, frame, gesture, key_event=None):
        self.controller.ui.update_background(frame)

        if gesture == "left":  # はい
            self._execute_transaction()

        elif gesture == "right":  # いいえ
            # ひとつ戻る（簡易実装としてメニューに戻す）
            self.controller.change_state(MenuState)

    def _execute_transaction(self):
        txn = self.controller.shared_context.get("transaction")
        am = self.controller.account_manager

        success = True
        msg = ""

        if txn == "transfer":
            target = self.controller.shared_context.get("target_account")
            amt = self.controller.shared_context.get("amount")
            success, msg = am.deposit(target, amt)

        elif txn == "withdraw":
            acct = self.controller.shared_context.get("account_number")
            amt = self.controller.shared_context.get("amount")
            success, msg = am.withdraw(acct, amt)

        elif txn == "create_account":
            name = self.controller.shared_context.get("name")
            pin = self.controller.shared_context.get("pin")
            # 新規作成は残高1000円あげるサービス
            new_acct = am.create_account(name, pin, initial_balance=1000)
            msg = f"口座を作成しました。\n口座番号: {new_acct}"

        self.controller.shared_context["result_message"] = msg
        self.controller.change_state(ResultState)


# --- 引き出しフロー (Acct -> PIN -> Amount -> Check -> Done) ---
class WithdrawAccountInputState(State):
    def on_enter(self, prev_state=None):
        self.controller.ui.clear_content()
        self.controller.ui.set_header("お引き出し")
        self.controller.ui.show_message("ご自身の口座番号を入力してください(キーボード)", visible=True)
        self.input_buffer = NumericInputBuffer(max_length=10)
        self.controller.ui.show_input_field(self.input_buffer.get_display_value(), visible=True)
        self.controller.ui.show_selection_guides(right_text="戻る")

    def update(self, frame, gesture, key_event=None):
        self.controller.ui.update_background(frame)
        if gesture == "right":
            self.controller.change_state(MenuState)
            return

        if key_event:
            # 共通のキー入力ロジック本当はInputHandlerに持たせたいがここで
            char = key_event.char
            if char.isdigit():
                if self.input_buffer.add_char(char):
                    self.controller.play_sound("pushenter")
            elif key_event.keysym == "BackSpace":
                self.input_buffer.backspace()
                self.controller.play_sound("pushenter")
            elif key_event.keysym == "Return":
                if len(self.input_buffer.get_value()) > 0:
                    self.controller.shared_context["account_number"] = self.input_buffer.get_value()
                    self.controller.play_sound("pushenter")
                    # 次はPIN入力
                    self.controller.change_state(PinInputState)

        self.controller.ui.show_input_field(self.input_buffer.get_display_value(), visible=True)


class PinInputState(State):
    """
    ランダム配置キーパッドによるPIN入力
    withdraw または create_account の一部として機能する
    """

    def on_enter(self, prev_state=None):
        self.controller.ui.clear_content()
        self.controller.ui.set_header("暗証番号入力")
        self.controller.ui.show_message("キーボード(tyughjvbnm)で入力してください", visible=True)

        # ピンパッドのリセット
        self.controller.pin_pad.reset_random_mapping()
        self.controller.ui.show_keypad(self.controller.pin_pad.get_layout_info(), visible=True)

        self.input_buffer = NumericInputBuffer(max_length=4, is_pin=True)
        self.controller.ui.show_input_field(self.input_buffer.get_display_value(), visible=True)
        self.controller.ui.show_selection_guides(right_text="戻る")

    def on_exit(self):
        self.controller.ui.show_keypad([], visible=False)

    def update(self, frame, gesture, key_event=None):
        self.controller.ui.update_background(frame)
        if gesture == "right":
            self.controller.change_state(MenuState)
            return

        if key_event:
            # key_event.char が 't', 'y', ... に対応
            char = key_event.char.lower()

            # ランダムマップから数字を取得
            num = self.controller.pin_pad.get_number(char)
            if num is not None:
                if self.input_buffer.add_char(num):
                    self.controller.play_sound("pushenter")
            elif key_event.keysym == "BackSpace":
                self.input_buffer.backspace()
                self.controller.play_sound("pushenter")
            elif key_event.keysym == "Return":
                # 4桁入力完了
                if len(self.input_buffer.get_value()) == 4:
                    self._on_pin_entered(self.input_buffer.get_value())

        self.controller.ui.show_input_field(self.input_buffer.get_display_value(), visible=True)

    def _on_pin_entered(self, pin):
        txn = self.controller.shared_context.get("transaction")

        if txn == "withdraw":
            # 認証
            acct = self.controller.shared_context.get("account_number")
            am = self.controller.account_manager
            if am.verify_pin(acct, pin):
                self.controller.play_sound("pushenter")
                print("Auth Success")
                self.controller.change_state(GenericAmountInputState)
            else:
                print("Auth Failed")
                self.controller.ui.show_message("暗証番号が違います！", visible=True)
                self.input_buffer.clear()
                # ユーザーに失敗を通知してリトライさせるフローが必要だが、簡易的にクリアだけ

        elif txn == "create_account":
            # 初回入力 -> 確認入力フローが必要だが、仕様では「暗証番号をもう一度入力させる」
            # ここでは state 内で flag を持つか、 Context に `pin_step` を持つ
            step = self.controller.shared_context.get("pin_step", 1)

            if step == 1:
                self.controller.shared_context["first_pin"] = pin
                self.controller.shared_context["pin_step"] = 2
                self.input_buffer.clear()
                self.controller.ui.show_message("確認のためもう一度入力してください", visible=True)
                # キー配置を変えるかどうかは仕様次第だが、セキュリティ的には変えたほうがいい
                self.controller.pin_pad.reset_random_mapping()
                self.controller.ui.show_keypad(self.controller.pin_pad.get_layout_info(), visible=True)

            elif step == 2:
                first = self.controller.shared_context.get("first_pin")
                if first == pin:
                    self.controller.shared_context["pin"] = pin
                    self.controller.play_sound("pushenter")
                    self.controller.change_state(ConfirmationState)
                else:
                    self.controller.ui.show_message("一致しません。最初からやり直してください。", visible=True)
                    self.controller.shared_context["pin_step"] = 1
                    self.input_buffer.clear()

# --- 口座作成フロー (Name -> PIN x2 -> Check -> Done) ---


class CreateAccountNameInputState(State):
    def on_enter(self, prev_state=None):
        self.controller.ui.clear_content()
        self.controller.ui.set_header("新規口座作成")
        self.controller.ui.show_message("お名前を入力してください(コンソールで入力)", visible=True)
        # 実装簡易化のためキーボード(英語)入力を受け付ける。
        self.name_buffer = ""
        self.controller.ui.show_input_field("", visible=True)
        self.controller.ui.show_selection_guides(right_text="戻る")

    def update(self, frame, gesture, key_event=None):
        self.controller.ui.update_background(frame)
        if gesture == "right":
            self.controller.change_state(MenuState)
            return

        if key_event:
            # 簡易文字入力
            if len(key_event.char) == 1 and key_event.char.isprintable():
                self.name_buffer += key_event.char
            elif key_event.keysym == "BackSpace":
                self.name_buffer = self.name_buffer[:-1]
            elif key_event.keysym == "Return":
                if len(self.name_buffer) > 0:
                    self.controller.shared_context["name"] = self.name_buffer
                    self.controller.play_sound("pushenter")
                    # 次はPIN設定
                    self.controller.shared_context["pin_step"] = 1
                    self.controller.change_state(PinInputState)

        self.controller.ui.show_input_field(self.name_buffer, visible=True)
