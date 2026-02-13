"""
StateMachine - ATM state transition manager.

Responsibilities:
  - Manage current state and modal stack
  - Provide prev_state to on_enter for context propagation
  - Restore click callbacks after modal pop (central restoration)
  - Trigger audio policy after each update cycle
"""


class State:
    """
    ATM state base class.

    All concrete states inherit from this class.
    The base __init__ provides convenience aliases to core subsystems
    so that subclasses never need to reach through controller chains.
    """

    def __init__(self, controller):
        self.controller = controller
        # Default header key (subclasses override as needed)
        self._header_key = "ui.main_menu"
        self._message = ""
        self._message_params = {}

    @property
    def session(self):
        """Lazy access to controller.session"""
        return self.controller.session

    @property
    def state_machine(self):
        """Lazy access to controller.state_machine"""
        return self.controller.state_machine

    @property
    def audio(self):
        """Lazy access to controller.audio"""
        return self.controller.audio

    @property
    def shared_context(self):
        """Lazy access to controller.shared_context"""
        return self.controller.shared_context

    def on_enter(self, prev_state=None):
        """Called when entering this state."""
        pass

    def on_exit(self):
        """Called when leaving this state."""
        pass

    def update(self, frame, gesture, key_event=None, progress=0,
               current_direction=None, debug_info=None):
        """
        Per-frame update.

        Args:
            frame: Camera frame (already flipped).
            gesture: Confirmed gesture (None, "left", "center", "right").
            key_event: Keyboard event if any.
            progress: Gesture recognition progress (0.0-1.0).
            current_direction: Currently recognized direction.
            debug_info: Debug info dict (AI predictions, etc.).
        """
        pass


class StateMachine:
    """
    Manages state transitions and modal stack.

    Design invariants:
      - Only one current_state at a time.
      - modal_stack is LIFO; topmost modal receives updates.
      - push_modal passes prev_state for context propagation.
      - pop_modal restores click callback centrally (Bug #4 fix).
    """

    def __init__(self, controller, initial_state_cls):
        self.controller = controller
        self.current_state = initial_state_cls(self.controller)
        self.current_state_name = initial_state_cls.__name__
        self.last_audio_key = None
        self.modal_stack = []

    def start(self):
        """Start the initial state."""
        self.current_state.on_enter()

    def change_state(self, next_state_cls):
        """
        Transition to a new state.

        All modals are closed first. The previous state is passed
        to the new state's on_enter for context propagation.
        """
        # Close all modals first
        while self.modal_stack:
            self.pop_modal()

        if self.current_state:
            self.current_state.on_exit()

        prev_state = self.current_state
        self.current_state = next_state_cls(self.controller)
        self.current_state_name = next_state_cls.__name__

        print(
            f"State Transition: "
            f"{prev_state.__class__.__name__} -> "
            f"{self.current_state_name}"
        )
        self.current_state.on_enter(prev_state=prev_state)

    def push_modal(self, modal_state_cls):
        """
        Push a modal state onto the stack.

        The previous active state (modal or current) is passed
        to the modal's on_enter for context propagation (Bug #2 fix).
        """
        prev = (
            self.modal_stack[-1]
            if self.modal_stack
            else self.current_state
        )
        print(f"Push Modal: {modal_state_cls.__name__}")
        modal = modal_state_cls(self.controller)
        self.modal_stack.append(modal)
        modal.on_enter(prev_state=prev)

    def pop_modal(self):
        """
        Pop the topmost modal and restore the parent's click callback.

        Central callback restoration (Bug #4 fix): after popping,
        the now-active state's _on_click is re-bound so that the
        parent state does not lose mouse interaction.
        """
        if not self.modal_stack:
            return

        modal = self.modal_stack.pop()
        print(f"Pop Modal: {modal.__class__.__name__}")
        modal.on_exit()

        # Restore click callback for the now-active state
        active = (
            self.modal_stack[-1]
            if self.modal_stack
            else self.current_state
        )
        if active and hasattr(active, "_on_click"):
            self.controller.ui.set_click_callback(active._on_click)
        else:
            self.controller.ui.set_click_callback(None)

    def update(self, frame, gesture, key_event=None, progress=0,
               current_direction=None, debug_info=None):
        """
        Dispatch update to the topmost active state,
        then run audio policy check.
        """
        active_state = (
            self.modal_stack[-1]
            if self.modal_stack
            else self.current_state
        )

        if active_state:
            active_state.update(
                frame, gesture, key_event, progress,
                current_direction, debug_info
            )

        # Audio policy (edge-triggered by key change)
        from src.core.audio_policy import AudioPolicy

        target_key = AudioPolicy.get_audio_key(
            active_state,
            self.controller.shared_context
        )

        if target_key:
            if target_key != self.last_audio_key:
                print(
                    f"AudioPolicy Trigger: "
                    f"{self.last_audio_key} -> {target_key}"
                )
                self.controller.audio.play_voice(target_key)
                self.last_audio_key = target_key
        else:
            self.last_audio_key = None
