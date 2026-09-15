import math
from PySide6.QtCore import QObject, Signal, Slot, QTimer
from core import visual_events
from ui.state.assistant_state import AssistantState

class EventBus(QObject):
    assistant_state_changed = Signal(object, str)
    page_changed = Signal(str)
    audio_level_changed = Signal(float)
    command_started = Signal(str)
    command_finished = Signal(bool)
    theme_changed = Signal(object)
    hardware_updated = Signal(dict)
    activity = Signal(str)
    wake_detected = Signal()
    incoming = Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.state = AssistantState.IDLE
        self._resume = AssistantState.IDLE
        self.reset_timer = QTimer(self)
        self.reset_timer.setSingleShot(True)
        self.reset_timer.timeout.connect(lambda: self.set_state(AssistantState.IDLE))
        self.incoming.connect(self.receive)
        self._unsubscribe = visual_events.subscribe(self.incoming.emit)

    def close(self):
        self._unsubscribe()
        self.reset_timer.stop()

    def set_state(self, state, detail=""):
        self.reset_timer.stop()
        self.state = AssistantState(state)
        self.assistant_state_changed.emit(self.state, str(detail)[:100])
        if self.state in (AssistantState.SUCCESS, AssistantState.ERROR):
            self.reset_timer.start(2400)

    @Slot(str, object)
    def receive(self, event, value):
        if event == "audio":
            level = float(value)
            self.audio_level_changed.emit(max(0., min(1., level)) if math.isfinite(level) else 0.)
        elif event == "command_started":
            self.set_state(AssistantState.EXECUTING, str(value))
            self.command_started.emit(str(value))
            self.activity.emit("Ação iniciada")
        elif event == "command_finished":
            self.command_finished.emit(bool(value))
            self.set_state(AssistantState.SUCCESS if value else AssistantState.ERROR)
            self.activity.emit("Ação concluída" if value else "Falha na ação")
        elif event == "speaking":
            if value:
                self._resume = self.state
                self.set_state(AssistantState.SPEAKING)
            else:
                self.audio_level_changed.emit(0.)
                self.set_state(self._resume)
        elif event == "wake":
            self.wake_detected.emit()
            self.set_state(AssistantState.LISTENING)
        elif event == "state":
            self.set_state(value)
