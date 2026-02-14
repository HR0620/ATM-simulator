from src.core.state_machine import State


class FaceAlignmentState(State):
    """起動時、顔が枠内に収まっているか確認"""

    def __init__(self, controller):
        super().__init__(controller)
        self._header_key = "msg.face.align"
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
                "header": "msg.face.align",
                "face_result": (status, guide_box, face_rect),
                "debug_info": debug_info,
            })

            if key_event:
                self.controller.audio.play("beep")

            if status == "confirmed":
                latest_res = self.controller.vision.detector.get_latest_result()
                if latest_res.get("detected"):
                    self.controller.normal_area = latest_res.get("primary_person_area")

                self.controller.play_button_se()

                # Import MenuState here to avoid circular dependencies
                from src.core.states.menu import MenuState
                self.controller.change_state(MenuState)
        else:
            from src.core.states.menu import MenuState
            self.controller.change_state(MenuState)
