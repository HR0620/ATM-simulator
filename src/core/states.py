"""
ATM States モジュール (リファクタリング版)

設計意図:
- 各StateはUI描画データを構築しrender_frameに渡す
- 共通パターンを基底クラスに抽出
- 音声再生を適切なタイミングで実行
- アイドル検知機能を追加
"""
from src.core.state_machine import State
from src.core.input_handler import NumericInputBuffer


# =============================================================================
# 基底クラス
# =============================================================================

class BaseInputState(State):
    """入力系Stateの共通基底クラス"""

    # サブクラスでオーバーライド
    INPUT_MAX = 6
    ALIGN_RIGHT = False
    HEADER = ""
    MESSAGE = ""
    UNIT = ""

    def on_enter(self, prev_state=None):
        self.input_buffer = NumericInputBuffer(
            max_length=self.INPUT_MAX,
            is_pin=False
        )
        self.controller.ui.set_click_callback(self._on_click)

    def on_exit(self):
        self.controller.ui.set_click_callback(None)

    def _on_click(self, zone):
        if zone == "right":
            self.controller.change_state(MenuState)

    def _on_input_complete(self, value):
        """入力完了時の処理 - サブクラスでオーバーライド"""
        pass

    def update(self, frame, gesture, key_event=None, progress=0,
               current_direction=None, debug_info=None):
        self.controller.ui.render_frame(frame, {
            "mode": "input",
            "header": self.HEADER,
            "message": self.MESSAGE,
            "input_value": self.input_buffer.get_display_value(),
            "input_max": self.INPUT_MAX,
            "input_unit": self.UNIT,
            "align_right": self.ALIGN_RIGHT,
            "guides": {"right": "戻る"},
            "progress": progress,
            "current_direction": current_direction,
            "debug_info": debug_info,
        })

        if gesture == "right":
            self.controller.change_state(MenuState)
            return

        if key_event:
            self._handle_key(key_event)

    def _handle_key(self, key_event):
        char = key_event.char
        if char.isdigit():
            if self.input_buffer.add_char(char):
                self.controller.play_sound("push-enter")
        elif key_event.keysym == "BackSpace":
            self.input_buffer.backspace()
            self.controller.play_sound("push-enter")
        elif key_event.keysym == "Return":
            value = self.input_buffer.get_value()
            if len(value) >= 1:
                self.controller.play_sound("push-enter")
                self._on_input_complete(value)


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
        if hasattr(self.controller, 'face_checker'):
            result = self.controller.face_checker.process(frame)
            status, guide_box, face_rect = result

            self.controller.ui.render_frame(frame, {
                "mode": "face_align",
                "header": "顔検出",
                "face_result": (status, guide_box, face_rect),
                "debug_info": debug_info,
            })

            if status == "confirmed":
                # 起動音 → いらっしゃいませの前
                self.controller.play_sound("open-window")
                self.controller.change_state(MenuState)
        else:
            self.controller.change_state(MenuState)


class MenuState(State):
    """メインメニュー"""

    IDLE_TIMEOUT_SEC = 10  # アイドル検知時間

    def on_enter(self, prev_state=None):
        self.controller.play_sound("irassyaimase")
        self.controller.shared_context = {}
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
        self.controller.play_sound("touch-button")
        # 再度タイマー開始
        self._start_idle_timer()

    def _on_click(self, zone):
        self._start_idle_timer()  # 操作があったらリセット
        self._handle_selection(zone)

    def _handle_selection(self, zone):
        if zone == "left":
            self.controller.shared_context = {"transaction": "transfer"}
            self.controller.change_state(TransferTargetInputState)
        elif zone == "center":
            self.controller.shared_context = {"transaction": "withdraw"}
            self.controller.change_state(WithdrawAccountInputState)
        elif zone == "right":
            self.controller.shared_context = {"transaction": "create_account"}
            self.controller.change_state(CreateAccountNameInputState)

    def update(self, frame, gesture, key_event=None, progress=0,
               current_direction=None, debug_info=None):
        self.controller.ui.render_frame(frame, {
            "mode": "menu",
            "header": "メインメニュー",
            "buttons": [
                {"zone": "left", "label": "振り込み"},
                {"zone": "center", "label": "引き出し"},
                {"zone": "right", "label": "口座作成"},
            ],
            "progress": progress,
            "current_direction": current_direction,
            "debug_info": debug_info,
        })

        if gesture:
            self._start_idle_timer()  # 操作があったらリセット
            self._handle_selection(gesture)


class ResultState(State):
    """結果/エラー画面"""

    def on_enter(self, prev_state=None):
        is_account_created = self.controller.shared_context.get(
            "is_account_created", False
        )

        self.controller.play_sound("come-again")

        self.countdown = 10 if is_account_created else 3
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
            self.controller.change_state(MenuState)
        else:
            self.controller.root.after(1000, self._tick)

    def update(self, frame, gesture, key_event=None, progress=0,
               current_direction=None, debug_info=None):
        msg = self.controller.shared_context.get(
            "result_message", "処理が完了しました。"
        )
        is_error = self.controller.shared_context.get("is_error", False)

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
    """振込先口座番号入力"""
    INPUT_MAX = 6
    ALIGN_RIGHT = False
    HEADER = "振込先口座番号"
    MESSAGE = "振込先の口座番号を入力してください"

    def _on_input_complete(self, value):
        if len(value) == 6:
            am = self.controller.account_manager

            # 口座存在チェック
            if am.get_account_name(value) is None:
                self.controller.shared_context["is_error"] = True
                self.controller.shared_context["result_message"] = "口座が存在しません"
                self.controller.change_state(ResultState)
                return

            # 口座凍結チェック
            if am.is_frozen(value):
                self.controller.shared_context["is_error"] = True
                self.controller.shared_context["result_message"] = "該当口座は凍結されています"
                self.controller.change_state(ResultState)
                return

            self.controller.shared_context["target_account"] = value
            self.controller.change_state(GenericAmountInputState)


class GenericAmountInputState(BaseInputState):
    """金額入力"""
    INPUT_MAX = 7
    ALIGN_RIGHT = True
    HEADER = "金額入力"
    MESSAGE = "金額を入力してください"
    UNIT = "円"

    def on_enter(self, prev_state=None):
        super().on_enter(prev_state)
        txn = self.controller.shared_context.get("transaction")
        if txn == "withdraw":
            self.controller.play_sound("please-select")
        else:
            self.controller.play_sound("pay-money")

    def _on_input_complete(self, value):
        if len(value) >= 1:
            amt = int(value)
            self.controller.shared_context["amount"] = amt
            self.controller.change_state(ConfirmationState)


class ConfirmationState(State):
    """確認画面"""

    def on_enter(self, prev_state=None):
        txn = self.controller.shared_context.get("transaction")
        # 金額確認音または保存確認音
        if txn == "create_account":
            self.controller.play_sound("save-data_q")
        else:
            self.controller.play_sound("check-money")

        self.controller.ui.set_click_callback(self._on_click)

    def on_exit(self):
        self.controller.ui.set_click_callback(None)

    def _on_click(self, zone):
        if zone == "left":
            self._execute_transaction()
        elif zone == "right":
            self.controller.change_state(MenuState)

    def update(self, frame, gesture, key_event=None, progress=0,
               current_direction=None, debug_info=None):
        txn = self.controller.shared_context.get("transaction")
        msg = self._build_message(txn)

        self.controller.ui.render_frame(frame, {
            "mode": "confirm",
            "header": "確認",
            "message": msg,
            "progress": progress,
            "current_direction": current_direction,
            "guides": {"left": "はい", "right": "いいえ"},
            "debug_info": debug_info,
        })

        if gesture == "left":
            self._execute_transaction()
        elif gesture == "right":
            self.controller.change_state(MenuState)

    def _build_message(self, txn):
        ctx = self.controller.shared_context
        if txn == "transfer":
            target = ctx.get("target_account")
            amt = ctx.get("amount")
            return f"口座番号 : {target}\n振込金額: {amt}円\n\nよろしいですか？"
        elif txn == "withdraw":
            amt = ctx.get("amount")
            return f"引出金額 : {amt}円\n\nよろしいですか？"
        elif txn == "create_account":
            name = ctx.get("name")
            return f"お名前 : {name}\n\nこの内容で作成しますか？"
        return ""

    def _execute_transaction(self):
        txn = self.controller.shared_context.get("transaction")
        am = self.controller.account_manager
        ctx = self.controller.shared_context

        msg = ""
        is_error = False
        is_account_created = False

        if txn == "transfer":
            target = ctx.get("target_account")
            amt = ctx.get("amount")
            success, msg = am.deposit(target, amt)
            is_error = not success

        elif txn == "withdraw":
            # 暗証番号の検証は PinInputState で既に行われている
            acct = ctx.get("account_number")
            amt = ctx.get("amount")
            success, msg = am.withdraw(acct, amt)
            is_error = not success

        elif txn == "create_account":
            name = ctx.get("name")
            pin = ctx.get("pin")
            new_acct = am.create_account(name, pin, initial_balance=1000)
            msg = f"口座を作成しました。\n\n" \
                  f"口座番号 : {new_acct}\n\n"
            is_account_created = True

        ctx["result_message"] = msg
        ctx["is_error"] = is_error
        ctx["is_account_created"] = is_account_created
        self.controller.change_state(ResultState)


# =============================================================================
# 引き出しフロー
# =============================================================================

class WithdrawAccountInputState(BaseInputState):
    """口座番号入力"""
    INPUT_MAX = 6
    ALIGN_RIGHT = False
    HEADER = "お引き出し"
    MESSAGE = "口座番号を入力してください"

    def _on_input_complete(self, value):
        if len(value) == 6:
            am = self.controller.account_manager

            # 口座存在チェック
            if am.get_account_name(value) is None:
                self.controller.shared_context["is_error"] = True
                self.controller.shared_context["result_message"] = "口座が存在しません"
                self.controller.change_state(ResultState)
                return

            # 口座凍結チェック
            if am.is_frozen(value):
                self.controller.shared_context["is_error"] = True
                self.controller.shared_context["result_message"] = "該当口座は凍結されています"
                self.controller.change_state(ResultState)
                return

            self.controller.shared_context["account_number"] = value
            self.controller.change_state(PinInputState)


class PinInputState(State):
    """暗証番号入力"""

    def on_enter(self, prev_state=None):
        self.controller.pin_pad.reset_random_mapping()
        self.input_buffer = NumericInputBuffer(max_length=4, is_pin=True)
        self.controller.ui.set_click_callback(self._on_click)
        self._message = self._get_message()

    def on_exit(self):
        self.controller.ui.set_click_callback(None)

    def _get_message(self):
        txn = self.controller.shared_context.get("transaction")
        step = self.controller.shared_context.get("pin_step", 1)

        if txn == "create_account":
            if step == 1:
                return "暗証番号を入力してください"
            else:
                return "確認のためもう一度入力してください"
        return "暗証番号を入力してください"

    def _on_click(self, zone):
        if zone == "right":
            self.controller.change_state(MenuState)

    def update(self, frame, gesture, key_event=None, progress=0,
               current_direction=None, debug_info=None):
        keypad = self.controller.pin_pad.get_layout_info()

        self.controller.ui.render_frame(frame, {
            "mode": "pin_input",
            "header": "暗証番号入力",
            "message": self._message,
            "input_value": self.input_buffer.get_display_value(),
            "keypad_layout": keypad,
            "guides": {"right": "戻る"},
            "progress": progress,
            "current_direction": current_direction,
            "debug_info": debug_info,
        })

        if gesture == "right":
            self.controller.change_state(MenuState)
            return

        if key_event:
            self._handle_key(key_event)

    def _handle_key(self, key_event):
        char = key_event.char.lower()
        num = self.controller.pin_pad.get_number(char)

        if num is not None:
            if self.input_buffer.add_char(num):
                self.controller.play_sound("push-enter")
        elif key_event.keysym == "BackSpace":
            self.input_buffer.backspace()
            self.controller.play_sound("push-enter")
        elif key_event.keysym == "Return":
            if len(self.input_buffer.get_value()) == 4:
                self.controller.play_sound("push-enter")
                self._on_pin_entered(self.input_buffer.get_value())

    def _on_pin_entered(self, pin):
        txn = self.controller.shared_context.get("transaction")
        ctx = self.controller.shared_context
        am = self.controller.account_manager

        if txn == "withdraw":
            acct = ctx.get("account_number")
            success, info = am.verify_pin(acct, pin)

            if success:
                ctx["pin"] = pin
                self.controller.change_state(GenericAmountInputState)
            else:
                if info == -1:  # 凍結
                    ctx["is_error"] = True
                    ctx["result_message"] = "試行回数を超えたため\n口座を凍結しました。"
                    self.controller.play_sound("come-again")
                    self.controller.change_state(ResultState)
                elif info == -2:  # 存在しない（通常はここに来る前にチェック済み）
                    ctx["is_error"] = True
                    ctx["result_message"] = "口座が存在しません"
                    self.controller.change_state(ResultState)
                else:
                    self.controller.play_sound("cancel")
                    self.input_buffer.clear()
                    self.controller.pin_pad.reset_random_mapping()
                    self._message = f"暗証番号が違います\n(残り {info} 回)"

                    if info <= 0:
                        ctx["is_error"] = True
                        ctx["result_message"] = "試行回数を超えたため\n口座を凍結しました。"
                        self.controller.play_sound("come-again")
                        self.controller.change_state(ResultState)

        elif txn == "create_account":
            step = ctx.get("pin_step", 1)

            if step == 1:
                ctx["first_pin"] = pin
                ctx["pin_step"] = 2
                self.input_buffer.clear()
                self.controller.pin_pad.reset_random_mapping()
                self._message = "確認のためもう一度入力してください"

            elif step == 2:
                first = ctx.get("first_pin")
                if first == pin:
                    ctx["pin"] = pin
                    self.controller.change_state(ConfirmationState)
                else:
                    ctx["pin_step"] = 1
                    self.input_buffer.clear()
                    self.controller.pin_pad.reset_random_mapping()
                    self.controller.play_sound("cancel")
                    self._message = "一致しません。最初から入力してください"


# =============================================================================
# 口座作成フロー
# =============================================================================

class CreateAccountNameInputState(State):
    """名前入力"""

    def on_enter(self, prev_state=None):
        self.name_buffer = ""
        self.controller.ui.set_click_callback(self._on_click)

    def on_exit(self):
        self.controller.ui.set_click_callback(None)

    def _on_click(self, zone):
        if zone == "right":
            self.controller.change_state(MenuState)

    def update(self, frame, gesture, key_event=None, progress=0,
               current_direction=None, debug_info=None):
        self.controller.ui.render_frame(frame, {
            "mode": "input",
            "header": "新規口座作成",
            "message": "お名前を入力してください",
            "input_value": self.name_buffer,
            "input_max": 10,
            "align_right": False,
            "guides": {"right": "戻る"},
            "progress": progress,
            "current_direction": current_direction,
            "debug_info": debug_info,
        })

        if gesture == "right":
            self.controller.change_state(MenuState)
            return

        if key_event:
            self._handle_key(key_event)

    def _handle_key(self, key_event):
        char = key_event.char
        if len(char) == 1 and char.isprintable():
            self.name_buffer += char
            self.controller.play_sound("push-enter")
        elif key_event.keysym == "BackSpace":
            self.name_buffer = self.name_buffer[:-1]
            self.controller.play_sound("push-enter")
        elif key_event.keysym == "Return":
            if len(self.name_buffer) > 0:
                self.controller.play_sound("push-enter")
                self.controller.shared_context["name"] = self.name_buffer
                self.controller.shared_context["pin_step"] = 1
                self.controller.change_state(PinInputState)
