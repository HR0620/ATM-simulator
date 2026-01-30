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
    GUIDANCE_EMPTY = "入力内容を確認してください"
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
        """入力確定操作の一元管理"""
        value = self.input_buffer.get_value()
        if len(value) >= self.MIN_INPUT_LENGTH:
            # 音声再生は _on_input_complete 内で条件に応じて行う
            self._on_input_complete(value)
        else:
            self.controller.ui.show_guidance(
                self.GUIDANCE_EMPTY, is_error=True
            )
            self.controller.play_beep_se()

    def _on_input_complete(self, value):
        """入力完了時の処理"""
        pass

    def update(self, frame, gesture, key_event=None, progress=0,
               current_direction=None, debug_info=None):

        guides = {"left": "進む", "right": "戻る"}

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
                "「進む」または「戻る」を選択してください"
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
                    self.controller.play_sound("push-enter")
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
        if hasattr(self.controller, 'face_checker'):
            result = self.controller.face_checker.process(frame)
            status, guide_box, face_rect = result

            self.controller.ui.render_frame(frame, {
                "mode": "face_align",
                "header": "顔検出",
                "face_result": (status, guide_box, face_rect),
                "debug_info": debug_info,
            })

            if key_event:
                self.controller.play_beep_se()  # 顔認識画面でのキーボード入力は一律beep

            if status == "confirmed":
                # 離席判定用の基準面積を初期化 (現在の顔面積をベースにする)
                # YOLOからの面積データが更新されるタイミングを待つため、
                # ここでは FaceChecker の結果から概算、または最新のYOLO結果を待つ
                latest_res = self.controller.async_detector.get_latest_result()
                if latest_res.get("detected"):
                    self.controller.normal_area = latest_res.get("primary_person_area")

                # 起動音 → いらっしゃいませの前
                self.controller.play_sound("open-window", force=True)
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
            self.controller.play_button_se()
            self.controller.shared_context = {"transaction": "transfer"}
            self.controller.change_state(TransferTargetInputState)
        elif zone == "center":
            self.controller.play_button_se()
            self.controller.shared_context = {"transaction": "withdraw"}
            self.controller.change_state(WithdrawAccountInputState)
        elif zone == "right":
            self.controller.play_button_se()
            self.controller.shared_context = {"transaction": "create_account"}
            self.controller.change_state(CreateAccountNameInputState)
        else:
            self.controller.play_beep_se()

    def update(self, frame, gesture, key_event=None, progress=0,
               current_direction=None, debug_info=None):
        if key_event:
            self.controller.play_beep_se()  # メニュー画面でのキーボード入力は一律beep

        self.controller.ui.render_frame(frame, {
            "mode": "menu",
            "header": "メインメニュー",
            "buttons": [
                {"zone": "left", "label": "お振り込み"},
                {"zone": "center", "label": "お引き出し"},
                {"zone": "right", "label": "口座作成"},
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
        is_account_created = self.controller.shared_context.get(
            "is_account_created", False
        )
        is_error = self.controller.shared_context.get("is_error", False)
        msg = self.controller.shared_context.get("result_message", "")

        if is_error:
            # 重大エラーは assert, それ以外は incorrect
            if any(x in msg for x in ["凍結", "存在しない", "エラー", "失敗"]):
                self.controller.play_sound("assert", force=True)
            else:
                self.controller.play_sound("incorrect", force=True)
        else:
            self.controller.play_sound("come-again", force=True)

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
    MIN_INPUT_LENGTH = 6
    ALIGN_RIGHT = False
    HEADER = "お振り込み"
    MESSAGE = "振込先の口座番号を入力してください"
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
            self.controller.shared_context["target_account"] = value
            self.controller.change_state(GenericAmountInputState)


class GenericAmountInputState(BaseInputState):
    """金額入力"""
    INPUT_MAX = 7
    MIN_INPUT_LENGTH = 1
    ALIGN_RIGHT = True
    HEADER = "金額入力"
    MESSAGE = "金額を入力してください"
    UNIT = "円"
    GUIDANCE_EMPTY = "金額を入力してください"

    def on_enter(self, prev_state=None):
        super().on_enter(prev_state)
        txn = self.controller.shared_context.get("transaction")
        if txn is None:
            self.controller.change_state(MenuState)
            return
        if txn == "withdraw":
            self.controller.play_sound("please-select")
            # 引出時は残高を表示
            acct = self.controller.shared_context.get("account_number")
            balance = self.controller.account_manager.get_balance(acct)
            self.MESSAGE = (
                f"金額を入力してください\n現在の貯蓄残高：{balance}円"
            )
        else:
            self.controller.play_sound("pay-money")
            self.MESSAGE = "振込金額を入力してください"

    def _on_input_complete(self, value):
        if len(value) >= 1:
            self.controller.play_button_se()
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
            self.controller.play_button_se()
            self._execute_transaction()
        elif zone == "right":
            self.controller.play_back_se()  # 「いいえ/戻る」は back.mp3
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
        txn = ctx.get("transaction")
        if txn is None:
            self.controller.change_state(MenuState)
            return

        am = self.controller.account_manager

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
            if success:
                # 引き出し後の残高を表示
                new_balance = am.get_balance(acct)
                msg = (
                    "お引き出しが完了しました。\n"
                    f"引き出し後残高：{new_balance}円"
                )
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
    MIN_INPUT_LENGTH = 6
    ALIGN_RIGHT = False
    HEADER = "お引き出し"
    MESSAGE = "口座番号を入力してください"
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
            self.controller.shared_context["account_number"] = value
            self.controller.change_state(PinInputState)


class PinInputState(BaseInputState):
    """暗証番号入力"""
    INPUT_MAX = 4
    MIN_INPUT_LENGTH = 4
    ALIGN_RIGHT = False
    HEADER = "暗証番号入力"
    GUIDANCE_EMPTY = "暗証番号を4桁で入力してください"

    def on_enter(self, prev_state=None):
        txn = self.controller.shared_context.get("transaction")
        if txn is None:
            self.controller.change_state(MenuState)
            return

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
                    self.controller.play_sound("push-enter")
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
        txn = self.controller.shared_context.get("transaction")
        ctx = self.controller.shared_context
        am = self.controller.account_manager

        if txn == "withdraw":
            acct = ctx.get("account_number")
            success, info = am.verify_pin(acct, pin)

            if success:
                self.controller.play_button_se()  # 成功時のみ button.mp3
                ctx["pin"] = pin
                self.controller.change_state(GenericAmountInputState)
            else:
                if info == -1:  # 凍結
                    self.controller.play_assert_se()  # 凍結は assert.mp3
                    ctx["is_error"] = True
                    ctx["result_message"] = (
                        "規定の回数を超えて暗証番号が入力されたため、\n"
                        "この口座はお取り扱いできません。"
                    )
                    self.controller.change_state(ResultState)
                elif info == -2:  # 存在しない（通常はここに来る前にチェック済み）
                    self.controller.play_assert_se()
                    ctx["is_error"] = True
                    ctx["result_message"] = (
                        "ご入力いただいた口座番号はお取り扱いできません。"
                    )
                    self.controller.change_state(ResultState)
                else:
                    self.controller.play_error_se()
                    self.input_buffer.clear()
                    self.controller.pin_pad.reset_random_mapping()
                    self._message = (
                        "暗証番号が正しくありません。\n"
                        f"（あと {info} 回入力できます）"
                    )

                    if info <= 0:
                        self.controller.play_assert_se()
                        ctx["is_error"] = True
                        ctx["result_message"] = (
                            "規定の回数を超えて暗証番号が入力されたため、\n"
                            "この口座はお取り扱いできません。"
                        )
                        self.controller.change_state(ResultState)

        elif txn == "create_account":
            step = ctx.get("pin_step", 1)

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
                ctx["first_pin"] = pin
                ctx["pin_step"] = 2
                self.input_buffer.clear()
                self.controller.pin_pad.reset_random_mapping()
                self._message = "確認のためもう一度入力してください"

            elif step == 2:
                first = ctx.get("first_pin")
                if first == pin:
                    self.controller.play_button_se()
                    ctx["pin"] = pin
                    self.controller.change_state(ConfirmationState)
                else:
                    ctx["pin_step"] = 1
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
        self.controller.shared_context["name"] = value
        self.controller.shared_context["pin_step"] = 1
        self.controller.change_state(PinInputState)


# =============================================================================
# 離席警告画面
# =============================================================================

class UserAbsentWarningState(State):
    """
    利用者が離席したことを検知した際の警告画面。
    5秒間無操作ならホーム画面へ戻り、ボタン押下で復帰する。
    """

    def on_enter(self, prev_state=None):
        # 警告音を一度だけ再生
        self.controller.play_assert_se()

        # 直前の状態を保存 (復帰用)
        self.previous_state = prev_state
        self.start_time = time.time()
        self.timeout_sec = 5

        # 離席判定をリセット
        self.controller.absence_frames = 0
        self.controller.det_history = []

        self.controller.ui.set_click_callback(self._on_click)

    def on_exit(self):
        self.controller.ui.set_click_callback(None)

    def _on_click(self, zone):
        if zone == "center":
            self._resume()

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
