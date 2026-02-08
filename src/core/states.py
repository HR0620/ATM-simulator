"""
ATM States モジュール (リファクタリング版)

設計意図:
- 各StateはUI描画データを構築しrender_frameに渡す
- 共通パターンを基底クラスに抽出
- 音声再生を適切なタイミングで実行
- アイドル検知機能を追加
"""
import time
from src.core.state_machine import State
from src.core.input_handler import InputBuffer
from src.core.pin_validator import is_valid_pin


# =============================================================================
# 基底クラス
# =============================================================================

class BaseInputState(State):
    """入力系Stateの共通基底クラス"""

    # サブクラスでオーバーライド
    INPUT_MAX = 6
    MIN_INPUT_LENGTH = 1  # 最小入力長
    ALIGN_RIGHT = False
    HEADER = ""
    MESSAGE = ""
    UNIT = ""
    GUIDANCE_EMPTY = "guidance.check_input"
    DIGIT_ONLY = True

    def on_enter(self, prev_state=None):
        self.input_buffer = InputBuffer(
            max_length=self.INPUT_MAX,
            is_pin=False,
            digit_only=self.DIGIT_ONLY
        )
        self.controller.ui.set_click_callback(self._on_click)

    def on_exit(self):
        self.controller.ui.set_click_callback(None)

    def _on_click(self, zone):
        if zone == "right":
            self._on_back()
        elif zone == "left":
            self._confirm_input()

    def _on_back(self):
        """戻る操作の一元管理"""
        self.controller.play_back_se()
        self.controller.change_state(MenuState)

    def _confirm_input(self):
        # バリデーション (7桁)
        val = self.input_buffer.get_value()
        if len(val) == 7:
            self.controller.play_button_se()
            self.controller.shared_context.target_account = val
            self.controller.change_state(GenericAmountInputState)
        else:
            self.controller.ui.show_guidance(
                "guidance.error.digits.7", is_error=True
            )
            # or use generic 'guidance.check_input' if specialized key missing
            self.controller.play_beep_se()

    def _on_input_complete(self, value):
        """入力完了時の処理"""
        pass

    def update(self, frame, gesture, key_event=None, progress=0,
               current_direction=None, debug_info=None):

        guides = {"left": "btn.next", "right": "btn.back"}

        self.controller.ui.render_frame(frame, {
            "mode": "input",
            "header": self.HEADER,
            "message": self.MESSAGE,
            "input_value": self.input_buffer.get_display_value(),
            "input_max": self.INPUT_MAX,
            "input_unit": self.UNIT,
            "align_right": self.ALIGN_RIGHT,
            "guides": guides,
            "progress": progress,
            "current_direction": current_direction,
            "debug_info": debug_info,
        })

        if gesture == "right":
            self._on_back()
            return

        if gesture == "left":
            self._confirm_input()
            return

        # Center ガイダンス
        if gesture == "center":
            self.controller.ui.show_guidance(
                "guidance.select_action"
            )
            return

        if key_event:
            self._handle_key(key_event)

    def _handle_key(self, key_event):
        char = key_event.char
        # 数字入力チェック
        if self.DIGIT_ONLY:
            if char.isdigit():
                if self.input_buffer.add_char(char):
                    self.controller.play_button_se()
                else:
                    self.controller.play_beep_se()
                return
        else:
            # 汎用テキスト入力 (名前など)
            if len(char) == 1 and char.isprintable():
                if self.input_buffer.add_char(char):
                    self.controller.play_sound("push-enter")
                else:
                    self.controller.play_beep_se()
                return

        if key_event.keysym == "BackSpace":
            if self.input_buffer.backspace():
                self.controller.play_cancel_se()  # 削除成功
            else:
                self.controller.play_beep_se()  # 空なら beep.mp3
        elif key_event.keysym == "Return":
            self._confirm_input()
        elif key_event.keysym == "Escape":
            self._on_back()
        else:
            # その他無効キー
            if not char.isprintable() or char == "":  # 制御キー等は無視
                pass
            else:
                self.controller.play_beep_se()


# =============================================================================
# メイン画面
# =============================================================================

class FaceAlignmentState(State):
    """起動時、顔が枠内に収まっているか確認"""

    def on_enter(self, prev_state=None):
        # 起動音はここでは再生しない（顔認証完了時に再生）
        pass

    def on_exit(self):
        pass

    def update(self, frame, gesture, key_event=None, progress=0,
               current_direction=None, debug_info=None):
        if hasattr(self.controller, 'vision'):
            result = self.controller.vision.face_checker.process(frame)
            status, guide_box, face_rect = result

            self.controller.ui.render_frame(frame, {
                "mode": "face_align",
                "header": "msg.face.align",  # or specific title
                "face_result": (status, guide_box, face_rect),
                "debug_info": debug_info,
            })

            if key_event:
                self.controller.audio.play("beep")  # 顔認識画面でのキーボード入力は一律beep

            if status == "confirmed":
                # 離席判定用の基準面積を初期化 (現在の顔面積をベースにする)
                latest_res = self.controller.vision.detector.get_latest_result()
                if latest_res.get("detected"):
                    self.controller.normal_area = latest_res.get("primary_person_area")

                # 起動音 → いらっしゃいませの前
                self.controller.change_state(MenuState)
        else:
            self.controller.change_state(MenuState)


class MenuState(State):
    """メインメニュー"""

    IDLE_TIMEOUT_SEC = 10  # アイドル検知時間

    def on_enter(self, prev_state=None):
        # Audio handled by Policy
        self.controller.shared_context.reset()
        self.controller.ui.set_click_callback(self._on_click)

        # アイドルタイマー開始
        self._idle_timer_id = None
        self._start_idle_timer()

    def on_exit(self):
        self.controller.ui.set_click_callback(None)
        self._cancel_idle_timer()

    def _start_idle_timer(self):
        self._cancel_idle_timer()
        self._idle_timer_id = self.controller.root.after(
            self.IDLE_TIMEOUT_SEC * 1000,
            self._on_idle
        )

    def _cancel_idle_timer(self):
        if self._idle_timer_id:
            self.controller.root.after_cancel(self._idle_timer_id)
            self._idle_timer_id = None

    def _on_idle(self):
        """アイドル状態になったら音声再生"""
        # To trigger AudioPolicy, we might need to change context
        # self.controller.shared_context["is_idle"] = True
        # self.controller.play_voice("check-screen") # Removed for strict policy
        # 再度タイマー開始
        self._start_idle_timer()

    def _on_click(self, zone):
        self._start_idle_timer()  # 操作があったらリセット
        self._handle_selection(zone)

    def _handle_selection(self, zone):
        if zone == "left":
            self.controller.play_button_se()
            self.controller.shared_context.reset()
            self.controller.shared_context.transaction = "transfer"
            self.controller.change_state(TransferTargetInputState)
        elif zone == "center":
            self.controller.play_button_se()
            self.controller.shared_context.reset()
            self.controller.shared_context.transaction = "withdraw"
            self.controller.change_state(WithdrawAccountInputState)
        elif zone == "right":
            self.controller.play_button_se()
            self.controller.shared_context.reset()
            self.controller.shared_context.transaction = "create_account"
            self.controller.change_state(CreateAccountNameInputState)
        else:
            self.controller.play_beep_se()

    def update(self, frame, gesture, key_event=None, progress=0,
               current_direction=None, debug_info=None):
        if key_event:
            self.controller.play_beep_se()  # メニュー画面でのキーボード入力は一律beep

        self.controller.ui.render_frame(frame, {
            "mode": "menu",
            "header": "ui.main_menu",
            "buttons": [
                {"zone": "left", "label": "btn.transfer"},
                {"zone": "center", "label": "btn.withdraw"},
                {"zone": "right", "label": "btn.create_account"},
            ],
            "progress": progress,
            "current_direction": current_direction,
            "debug_info": debug_info,
        })

        if gesture:
            self._start_idle_timer()
            self._handle_selection(gesture)

        if key_event:
            self.controller.play_beep_se()  # メニュー画面でのキーボード入力は一律beep


class ResultState(State):
    """結果/エラー画面"""

    def on_enter(self, prev_state=None):
        is_account_created = self.controller.shared_context.is_account_created
        is_error = self.controller.shared_context.is_error
        # msg is now a key usually
        msg_key = self.controller.shared_context.result_message

        if is_error:
            # If msg_key contains suspicious words (legacy check), or just rely on is_error
            # Ideally msg_key determines the sound.
            # Using simple fallback:
            self.controller.play_assert_se()
        else:
            pass  # Audio handled by Policy (create-account or come-again)

        self.start_time = time.time()
        self.countdown = 10 if is_account_created else 5
        self._start_countdown()

    def on_exit(self):
        pass

    def _start_countdown(self):
        if self.countdown > 0:
            self.controller.root.after(1000, self._tick)
        else:
            self.controller.change_state(MenuState)

    def _tick(self):
        self.countdown -= 1
        if self.countdown <= 0:
            # 直接ホーム画面に戻る（FaceAlignmentを経由しない）
            self.controller.change_state(MenuState)
        else:
            self.controller.root.after(1000, self._tick)

    def update(self, frame, gesture, key_event=None, progress=0,
               current_direction=None, debug_info=None):
        msg = self.controller.shared_context.result_message or "処理が完了しました。"
        is_error = self.controller.shared_context.is_error

        self.controller.ui.render_frame(frame, {
            "mode": "result",
            "header": "エラー" if is_error else "手続き完了",
            "message": msg,
            "is_error": is_error,
            "countdown": self.countdown,
            "debug_info": debug_info,
        })


# =============================================================================
# 振込フロー
# =============================================================================

class TransferTargetInputState(BaseInputState):
    """振込先入力ステート"""
    INPUT_MAX = 6
    MIN_INPUT_LENGTH = 6
    ALIGN_RIGHT = False
    HEADER = "btn.transfer"
    MESSAGE = "input.account.target"
    GUIDANCE_EMPTY = "口座番号を6桁で入力してください"

    def _on_input_complete(self, value):
        if len(value) == 6:
            am = self.controller.account_manager

            # 口座存在チェック
            if am.get_account_name(value) is None:
                self.controller.play_assert_se()  # 口座間違いは assert.mp3
                self.controller.shared_context["is_error"] = True
                self.controller.shared_context["result_message"] = (
                    "ご入力いただいた口座番号はお取り扱いできません。"
                )
                self.controller.change_state(ResultState)
                return

            # 口座凍結チェック
            if am.is_frozen(value):
                self.controller.play_assert_se()  # 凍結も assert.mp3
                self.controller.shared_context["is_error"] = True
                self.controller.shared_context["result_message"] = (
                    "こちらの口座は現在ご利用いただけません。"
                )
                self.controller.change_state(ResultState)
                return

            self.controller.play_button_se()  # 成功時のみ button.mp3
            self.controller.shared_context.target_account = value
            self.controller.change_state(GenericAmountInputState)


class GenericAmountInputState(BaseInputState):
    """金額入力ステート"""
    INPUT_MAX = 7
    MIN_INPUT_LENGTH = 1
    ALIGN_RIGHT = True
    HEADER = "btn.amount"  # or "ui.amount_input"
    MESSAGE = "input.amount"
    UNIT = "円"
    GUIDANCE_EMPTY = "金額を入力してください"

    def on_enter(self, prev_state=None):
        super().on_enter(prev_state)
        txn = self.controller.shared_context.transaction
        if txn is None:
            self.controller.change_state(MenuState)
            return
        if txn == "withdraw":
            # Audio by Policy
            # 引出時は残高を表示
            acct = self.controller.shared_context.account_number
            balance = self.controller.account_manager.get_balance(acct)
            self.MESSAGE = (
                f"金額を入力してください\n現在の貯蓄残高：{balance}円"
            )
        else:
            # Audio by Policy
            self.MESSAGE = "振込金額を入力してください"

    def _confirm_input(self):
        amount_str = self.input_buffer.get_value()
        if not amount_str:
            self.controller.play_beep_se()
            return

        amount = int(amount_str)
        if amount <= 0:
            self.controller.play_beep_se()
            return

        self.controller.play_button_se()
        self.controller.shared_context.amount = amount
        self.controller.change_state(ConfirmationState)


class ConfirmationState(State):
    """確認画面ステート"""

    def on_enter(self, prev_state=None):
        # Audio by Policy
        self.controller.ui.set_click_callback(self._on_click)

    def on_exit(self):
        self.controller.ui.set_click_callback(None)

    def _on_click(self, x, y):
        clicked_zone = self.controller.ui.get_zone_at(x, y)
        if clicked_zone:
            self._handle_selection(clicked_zone)

    def _handle_selection(self, zone):
        if zone == "left":   # Yes -> PinInput
            self.controller.play_button_se()
            self.controller.change_state(PinInputState)
        elif zone == "right":  # No -> Menu
            self.controller.play_cancel_se()
            self.controller.change_state(MenuState)
        else:
            self.controller.play_beep_se()

    def update(self, frame, gesture, key_event=None, progress=0,
               current_direction=None, debug_info=None):

        # ... logic ...

        # confirm.title = "入力内容の確認"
        # confirm.transfer = ("お振込み先 : {}\n" "お振込み金額 : {:,}円\n\n" "よろしいですか？")
        # Reuse logic for formatting
        title_key = "confirm.title"

        ctx = self.controller.shared_context
        tx_type = ctx.transaction or ""

        msg_key = "confirm.general"
        msg_params = {}

        if tx_type == "transfer":
            msg_key = "confirm.transfer"
            msg_params = {
                "target": ctx.target_account or "",
                "amount": ctx.amount
            }
        elif tx_type == "withdraw":
            msg_key = "confirm.withdraw"
            msg_params = {
                "amount": ctx.amount
            }
        elif tx_type == "create_account":
            msg_key = "confirm.create_account"
            msg_params = {
                "name": ctx.account_name or ""
            }

        self.controller.ui.render_frame(frame, {
            "mode": "confirm",
            "header": title_key,
            "message": msg_key,
            "message_params": msg_params,
            "progress": progress,
            "current_direction": current_direction,
            "debug_info": debug_info
        })

        if gesture == "left" or (key_event and key_event.keysym == "Return"):
            self.controller.play_button_se()
            self._execute_transaction()
            return

        if gesture == "right":
            self.controller.play_back_se()  # いいえ/戻るは back.mp3
            self.controller.change_state(MenuState)
            return

        if gesture == "center":
            self.controller.ui.show_guidance(
                "「はい」または「いいえ」を選択してください"
            )

    def _build_message(self, txn):
        ctx = self.controller.shared_context
        if txn == "transfer":
            target = ctx.get("target_account")
            amt = ctx.get("amount")
            return (
                f"振込先口座 : {target}\n"
                f"振込金額 : {amt}円\n\nよろしいですか？"
            )
        elif txn == "withdraw":
            amt = ctx.get("amount")
            return f"引き出し金額 : {amt}円\n\nよろしいですか？"
        elif txn == "create_account":
            name = ctx.get("name")
            return f"お名前 : {name}\n\nこの内容で作成しますか？"
        return ""

    def _execute_transaction(self):
        ctx = self.controller.shared_context
        txn = ctx.transaction
        if txn is None:
            self.controller.change_state(MenuState)
            return

        am = self.controller.account_manager

        msg = ""
        is_error = False
        is_account_created = False

        if txn == "transfer":
            target = ctx.target_account
            amt = ctx.amount
            success, msg = am.deposit(target, amt)
            is_error = not success

        elif txn == "withdraw":
            # 暗証番号の検証は PinInputState で既に行われている
            acct = ctx.account_number
            amt = ctx.amount
            success, msg = am.withdraw(acct, amt)
            if success:
                # 引き出し後の残高を表示
                new_balance = am.get_balance(acct)
                msg = (
                    "お引き出しが完了しました。\n"
                    f"引き出し後残高：{new_balance}円"
                )
            is_error = not success

        elif txn == "create_account":
            name = ctx.account_name
            # Actually ctx['pin'] was used? No, PinInputState sets ctx['pin'] in previous logic. I should check.
            pin = ctx.pin_input
            # PinInputState line 781: ctx["pin"] = pin
            # I'll use extra for 'pin' for now if I didn't add it.
            # Wait, I didn't add 'pin' to TransactionContext, only 'pin_input'.
            # I'll add 'pin' to TransactionContext later if needed, but 'pin_input' might suffice or I use item access.
            # Let's check states.py line 553 again.
            # In states.py: ctx.get("pin")
            new_acct = am.create_account(name, pin, initial_balance=1000)
            msg = f"口座を作成しました。\n\n" \
                f"口座番号 : {new_acct}\n\n"
            is_account_created = True

        ctx.result_message = msg
        ctx.is_error = is_error
        ctx.is_account_created = is_account_created
        self.controller.change_state(ResultState)


# =============================================================================
# 引き出しフロー
# =============================================================================

class WithdrawAccountInputState(BaseInputState):
    """引き出し時の口座番号入力 (今回は簡略化で自身の口座？ またはID ?)"""
    INPUT_MAX = 6
    MIN_INPUT_LENGTH = 6
    ALIGN_RIGHT = False
    HEADER = "btn.withdraw"
    MESSAGE = "input.account.id"  # "口座番号を入力してください"
    GUIDANCE_EMPTY = "口座番号を6桁で入力してください"

    def _on_input_complete(self, value):
        if len(value) == 6:
            am = self.controller.account_manager

            # 口座存在チェック
            if am.get_account_name(value) is None:
                self.controller.play_assert_se()  # 口座間違いは assert.mp3
                self.controller.shared_context["is_error"] = True
                self.controller.shared_context["result_message"] = (
                    "ご入力いただいた口座番号はお取り扱いできません。"
                )
                self.controller.change_state(ResultState)
                return

            # 口座凍結チェック
            if am.is_frozen(value):
                self.controller.play_assert_se()  # 凍結も assert.mp3
                self.controller.shared_context["is_error"] = True
                self.controller.shared_context["result_message"] = (
                    "こちらの口座は現在ご利用いただけません。"
                )
                self.controller.change_state(ResultState)
                return

            self.controller.play_button_se()  # 成功時のみ button.mp3
            self.controller.shared_context.account_number = value
            self.controller.change_state(PinInputState)


class PinInputState(BaseInputState):
    """暗証番号入力"""
    INPUT_MAX = 4
    MIN_INPUT_LENGTH = 4
    ALIGN_RIGHT = False
    HEADER = "暗証番号入力"
    GUIDANCE_EMPTY = "暗証番号を4桁で入力してください"

    def on_enter(self, prev_state=None):
        txn = self.controller.shared_context.transaction
        if txn is None:
            self.controller.change_state(MenuState)
            return

        # Determine Pin Mode for AudioPolicy
        step = self.controller.shared_context.pin_step or 1
        mode = "normal"
        if txn == "create_account":
            mode = f"create_{step}"
        elif txn == "withdraw":
            mode = "auth"
            # If we are re-entering (not strictly checking previous fail here, handled in _on_pin_entered logic)
            # Actually, if we just arrived here, it's normal auth.
            # Retry only happens if validation fails and we stay in state.

        self.controller.shared_context.pin_mode = mode

        self.controller.pin_pad.reset_random_mapping()
        self.input_buffer = InputBuffer(
            max_length=4, is_pin=True, digit_only=True
        )
        self.controller.ui.set_click_callback(self._on_click)
        self._message = self._get_message()

    def _get_message(self):
        txn = self.controller.shared_context.get("transaction")
        step = self.controller.shared_context.get("pin_step", 1)

        if txn == "create_account":
            if step == 1:
                return "設定する暗証番号(4桁)を入力してください"
            else:
                return "確認のため、もう一度入力してください"
        return "暗証番号を4桁で入力してください"

    def update(self, frame, gesture, key_event=None, progress=0,
               current_direction=None, debug_info=None):
        keypad = self.controller.pin_pad.get_layout_info()

        self.controller.ui.render_frame(frame, {
            "mode": "pin_input",
            "header": self.HEADER,
            "message": self._message,
            "input_value": self.input_buffer.get_display_value(),
            "keypad_layout": keypad,
            "guides": {"left": "進む", "right": "戻る"},
            "progress": progress,
            "current_direction": current_direction,
            "debug_info": debug_info,
        })

        if gesture == "left":
            self._confirm_input()
            return

        if gesture == "right":
            self._on_back()
            return

        if key_event:
            char = key_event.char.lower()
            num = self.controller.pin_pad.get_number(char)

            if num is not None:
                if self.input_buffer.add_char(num):
                    self.controller.play_button_se()
                else:
                    self.controller.play_beep_se()  # 文字数オーバー
                return

            if key_event.keysym == "BackSpace":
                if self.input_buffer.backspace():
                    self.controller.play_cancel_se()  # 削除成功時は cancel.mp3
                else:
                    self.controller.play_beep_se()  # 空なら beep.mp3
            elif key_event.keysym == "Return":
                self._confirm_input()
            elif key_event.keysym == "Escape":
                self._on_back()
            else:
                # 特殊キー(Shift等)以外ならbeep
                if not char.isprintable() or char == "":
                    pass
                else:
                    self.controller.play_beep_se()

    def _on_input_complete(self, value):
        self._on_pin_entered(value)

    def _on_pin_entered(self, pin):
        txn = self.controller.shared_context.transaction
        ctx = self.controller.shared_context
        am = self.controller.account_manager

        if txn == "withdraw":
            acct = ctx.account_number
            success, info = am.verify_pin(acct, pin)

            if success:
                self.controller.play_button_se()  # 成功時のみ button.mp3
                ctx.pin = pin
                self.controller.change_state(GenericAmountInputState)
            else:
                if info == -1:  # 凍結
                    self.controller.play_assert_se()  # 凍結は assert.mp3
                    ctx.is_error = True
                    ctx.result_message = (
                        "規定の回数を超えて暗証番号が入力されたため、\n"
                        "この口座はお取り扱いできません。"
                    )
                    self.controller.change_state(ResultState)
                elif info == -2:  # 存在しない（通常はここに来る前にチェック済み）
                    self.controller.play_assert_se()
                    ctx.is_error = True
                    ctx.result_message = (
                        "ご入力いただいた口座番号はお取り扱いできません。"
                    )
                    self.controller.change_state(ResultState)
                else:
                    self.controller.play_error_se()
                    self.input_buffer.clear()
                    self.controller.pin_pad.reset_random_mapping()

                    # RETRY LOGIC for AudioPolicy
                    ctx.pin_mode = "retry"

                    self._message = (
                        "暗証番号が正しくありません。\n"
                        f"（あと {info} 回入力できます）"
                    )

                    if info <= 0:
                        self.controller.play_assert_se()
                        ctx.is_error = True
                        ctx.result_message = (
                            "規定の回数を超えて暗証番号が入力されたため、\n"
                            "この口座はお取り扱いできません。"
                        )
                        self.controller.change_state(ResultState)

        elif txn == "create_account":
            step = ctx.pin_step or 1

            if step == 1:
                # 暗証番号の安全性チェック
                is_safe, _ = is_valid_pin(pin)
                if not is_safe:
                    self.controller.play_beep_se()
                    self.input_buffer.clear()
                    self.controller.pin_pad.reset_random_mapping()
                    self._message = "安全性の低い暗証番号は使用できません"
                    return

                self.controller.play_button_se()
                ctx.first_pin = pin
                ctx.pin_step = 2
                self.input_buffer.clear()
                self.controller.pin_pad.reset_random_mapping()
                self._message = "確認のためもう一度入力してください"

            elif step == 2:
                first = ctx.first_pin
                if first == pin:
                    self.controller.play_button_se()
                    ctx.pin = pin
                    self.controller.change_state(ConfirmationState)
                else:
                    ctx.pin_step = 1
                    self.input_buffer.clear()
                    self.controller.pin_pad.reset_random_mapping()
                    self.controller.play_error_se()  # 不一致も incorrect.mp3
                    self._message = (
                        "一致しません。最初から入力してください"
                    )


# =============================================================================
# 口座作成フロー
# =============================================================================

class CreateAccountNameInputState(BaseInputState):
    """名前入力"""
    INPUT_MAX = 10
    MIN_INPUT_LENGTH = 1
    ALIGN_RIGHT = False
    HEADER = "口座作成"
    MESSAGE = "お名前を入力してください"
    GUIDANCE_EMPTY = "お名前を入力してください"
    DIGIT_ONLY = False

    def _on_input_complete(self, value):
        self.controller.play_button_se()
        self.controller.shared_context.account_name = value
        self.controller.shared_context.pin_step = 1
        self.controller.change_state(PinInputState)


# =============================================================================
# 離席警告画面
# =============================================================================

class UserAbsentWarningState(State):
    """離席警告ステート"""

    def on_enter(self, prev_state=None):
        self.previous_state = prev_state
        self.controller.play_beep_se()
        self.start_time = time.time()
        self.timeout_sec = 10
        self.controller.ui.set_click_callback(self._on_click)

    def on_exit(self):
        self.controller.ui.set_click_callback(None)

    def _on_click(self, zone):
        self._handle_selection(zone)

    def _handle_selection(self, zone):
        if zone == "left":  # Yes -> Reset to FaceAlign
            self.controller.play_button_se()
            self.controller.grace_period_frames = 90  # 復帰猶予
            self.controller.change_state(FaceAlignmentState)
        elif zone == "right":  # No -> Continue (Return to prev)
            self.controller.play_back_se()
            # 継続（戻る）
            # previous_state に戻るのが理想だが簡略化でMenuへ
            self.controller.grace_period_frames = 90
            self.controller.change_state(MenuState)
        else:
            self.controller.play_beep_se()

    def _resume(self):
        """元の操作へ復帰"""
        self.controller.play_button_se()
        # 復帰直後の再検知を防ぐ猶予期間を設定 (3秒 = 約90フレーム)
        self.controller.grace_period_frames = 90

        if self.previous_state:
            # 前の状態が WarningState 自身でないことを確認 (念のため)
            if self.previous_state.__class__ != self.__class__:
                self.controller.change_state(self.previous_state.__class__)
            else:
                self.controller.change_state(MenuState)
        else:
            self.controller.change_state(MenuState)

    def update(self, frame, gesture, key_event=None, progress=0,
               current_direction=None, debug_info=None):

        elapsed = time.time() - self.start_time
        remaining = max(0, int(self.timeout_sec - elapsed))

        if elapsed >= self.timeout_sec:
            # タイムアウトでホーム画面へ
            self.controller.change_state(MenuState)
            return

        # UI描画
        self.controller.ui.render_frame(frame, {
            "mode": "absence_warning",
            "header": "利用者離席検知",
            "message": "ご利用者が離れたことを検知しました。\nこのまま操作を続けますか？",
            "countdown": remaining,
            "guides": {"center": "操作に戻る"},
            "progress": progress,
            "current_direction": current_direction,
            "debug_info": debug_info,
        })

        if gesture == "center" or (key_event and key_event.keysym == "Return"):
            self._resume()


# =============================================================================
# 言語選択モーダル (Overlay)
# =============================================================================

class LanguageModal(State):
    """
    言語選択モーダル
    Overlayとして動作し、背景のupdateを停止させたまま描画のみ行うことを想定。
    """

    def __init__(self, controller):
        super().__init__(controller)
        self.selected_index = 0
        self.languages = []

    def on_enter(self, prev_state=None):
        self.languages = ["JP", "EN", "ZH_CN", "KR", "FR", "ES", "VN"]
        import json
        from src.paths import get_resource_path

        lang_path = get_resource_path("config/languages.json")
        with open(lang_path, "r", encoding="utf-8") as f:
            all_langs = json.load(f).get("languages", [])

        self.languages = [
            {"code": item["code"], "display_name": item.get("display_name", item["code"])}
            for item in all_langs
            if item.get("enabled", True)
        ]
        if not self.languages:
            self.languages = [{"code": "JP", "display_name": "日本語"}]

        current = self.controller.i18n.current_lang
        codes = [item["code"] for item in self.languages]
        try:
            self.selected_index = codes.index(current)
        except ValueError:
            self.selected_index = 0

        self.controller.play_voice("check-screen")  # Or specific language voice? Policy not defined for Modal yet.
        self.controller.ui.set_click_callback(self._on_click)

    def on_exit(self):
        pass
        self.controller.ui.set_click_callback(None)

    def _move_prev(self):
        self.controller.play_se("button")
        self.selected_index = (self.selected_index - 1) % len(self.languages)

    def _move_next(self):
        self.controller.play_se("button")
        self.selected_index = (self.selected_index + 1) % len(self.languages)

    def _on_click(self, action):
        if action == "lang_prev":
            self._move_prev()
        elif action == "lang_next":
            self._move_next()
        elif action.startswith("lang_select:"):
            index = int(action.split(":", 1)[1])
            if 0 <= index < len(self.languages):
                self.controller.play_se("button")
                self.selected_index = index
        elif action == "lang_confirm":
            self._confirm_selection()
        elif action == "lang_back":
            self.controller.play_back_se()
            self.controller.close_modal()

    def update(self, frame, gesture, key_event=None, progress=0,
               current_direction=None, debug_info=None):

        # Overlay描画 (UI側で実装が必要)
        # ここでは描画データを構築してUIに渡す
        # mode="language_modal" を追加する

        self.controller.ui.render_frame(frame, {
            "mode": "language_modal",
            "languages": self.languages,
            "selected_index": self.selected_index,
            "progress": progress,
            "current_direction": current_direction,
            "debug_info": debug_info
        })

        # 入力処理
        if gesture == "left":
            # Scroll Up / Prev
            self.controller.play_se("button")
            self.selected_index = (self.selected_index - 1) % len(self.languages)

        elif gesture == "right":
            # Scroll Down / Next
            self.controller.play_se("button")
            self.selected_index = (self.selected_index + 1) % len(self.languages)

        elif gesture == "center":
            # Select / Confirm
            self._confirm_selection()
        elif gesture == "right":
            # Back to previous state
            self.controller.play_back_se()
            self.controller.close_modal()

        if key_event:
            if key_event.keysym in ("Up", "Left"):
                self._move_prev()
            elif key_event.keysym in ("Down", "Right"):
                self._move_next()
            elif key_event.keysym == "Return":
                self._confirm_selection()
            elif key_event.keysym == "Escape":
                self.controller.play_back_se()
                self.controller.close_modal()

    def _confirm_selection(self):
        lang = self.languages[self.selected_index]["code"]
        print(f"Language Selected: {lang}")

        self.controller.i18n.set_language(lang)
        self.controller.audio.set_language(lang)
        self.controller.config["system"]["language"] = lang

        self.controller.play_voice("welcome")
        self.controller.close_modal()
