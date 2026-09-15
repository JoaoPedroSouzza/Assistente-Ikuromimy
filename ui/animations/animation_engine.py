import time
from PySide6.QtCore import QObject, QTimer, Signal

QUALITY = {"Alto": (60, 22, 96), "Médio": (30, 16, 72), "Baixo": (20, 9, 40), "Desativado": (0, 9, 40)}

class AnimationEngine(QObject):
    frame = Signal(float)
    quality_changed = Signal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.quality = "Médio"
        self.elapsed = 0.
        self.paused = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self._last = time.perf_counter()
        self.set_quality(self.quality)

    def set_quality(self, quality):
        self.quality = quality if quality in QUALITY else "Médio"
        self.quality_changed.emit(self.quality)
        self.set_paused(self.paused)
        self.frame.emit(0.)

    def set_paused(self, paused):
        self.paused = paused
        self.timer.stop()
        fps = QUALITY[self.quality][0]
        self._last = time.perf_counter()
        if not paused and fps:
            self.timer.start(round(1000 / fps))

    def tick(self):
        now = time.perf_counter()
        dt = min(.05, now - self._last)
        self._last = now
        self.elapsed += dt
        self.frame.emit(dt)
