from PySide6.QtCore import Property, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QPushButton, QStyleOptionButton, QStyle

class ReactiveButton(QPushButton):
    """Paint-only press feedback: no relayout, no widget recreation."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._scale = 1.
        self.animation = QPropertyAnimation(self,b"visualScale",self)
        self.animation.setDuration(130)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.pressed.connect(lambda: self.animate(.96))
        self.released.connect(lambda: self.animate(1.))

    def get_scale(self): return self._scale
    def set_scale(self,value): self._scale = value; self.update()
    visualScale = Property(float,get_scale,set_scale)

    def animate(self, value):
        engine = getattr(self.window(),"engine",None)
        if engine and engine.quality == "Desativado": return
        self.animation.stop(); self.animation.setStartValue(self._scale)
        self.animation.setEndValue(value); self.animation.start()

    def paintEvent(self,event):
        painter = QPainter(self)
        painter.translate(self.width()/2,self.height()/2)
        painter.scale(self._scale,self._scale)
        painter.translate(-self.width()/2,-self.height()/2)
        option = QStyleOptionButton(); self.initStyleOption(option)
        self.style().drawControl(QStyle.CE_PushButton,option,painter,self)
        painter.end()
