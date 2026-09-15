import math
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget
from ui.state.assistant_state import AssistantState
from ui.theme.colors import ERROR

class AICore(QWidget):
    def __init__(self, engine, theme, bus, parent=None):
        super().__init__(parent)
        self.engine, self.theme = engine, theme
        self.state = AssistantState.IDLE
        self.state_started = 0.
        self.phase = self.audio = self.target_audio = 0.
        self.setMinimumSize(230, 230)
        engine.frame.connect(self.advance)
        theme.changed.connect(lambda _: self.update())
        bus.assistant_state_changed.connect(self.state_changed)
        bus.audio_level_changed.connect(self.audio_changed)
        self.setAccessibleName("Núcleo visual da Ikuromimy")

    def state_changed(self, state, detail):
        self.state = state
        self.state_started = self.phase
        self.update()
    def audio_changed(self, value): self.target_audio = value
    def advance(self, dt):
        if not self.isVisible(): return
        self.phase += dt * (.25 if self.state == AssistantState.OFFLINE else 1.)
        self.audio += (self.target_audio-self.audio)*(1-math.exp(-dt*12))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c = QPointF(self.width()/2, self.height()/2)
        radius = min(self.width(),self.height())*.28
        radius *= 1 + .025*math.sin(self.phase*1.5) + self.audio*.13
        age = self.phase-self.state_started
        if self.state == AssistantState.SUCCESS: radius *= 1 + .12*math.sin(min(1.,age)*math.pi)
        color = QColor(ERROR) if self.state == AssistantState.ERROR else QColor(self.theme.accent)
        glow = QColor(color)
        glow.setAlpha(12 if self.state == AssistantState.OFFLINE else 45)
        gradient = QRadialGradient(c, radius*1.9)
        gradient.setColorAt(0, glow)
        gradient.setColorAt(.5, glow)
        gradient.setColorAt(1, QColor(0,0,0,0))
        p.setPen(Qt.NoPen)
        p.setBrush(gradient)
        p.drawEllipse(c, radius*1.9, radius*1.9)
        p.setBrush(Qt.NoBrush)
        count = 8 if self.engine.quality in ("Baixo", "Desativado") else 15
        for j in range(count):
            path = QPainterPath()
            r = radius*(.20 + .80*j/count)
            for i in range(97):
                a = i*math.tau/96
                drift = self.phase*(.6 if self.state == AssistantState.THINKING else .14)
                rr = r*(1+.07*math.sin(a*3+drift+j*.20)+.04*math.cos(a*5-drift))
                point = QPointF(c.x()+math.cos(a)*rr, c.y()+math.sin(a)*rr)
                if not i: path.moveTo(point)
                else: path.lineTo(point)
            ink = QColor(color); ink.setAlpha(90 + j*7)
            p.setPen(QPen(ink, .9)); p.drawPath(path)
        for j in range(3):
            r = radius*(1.2+j*.13)
            ink = QColor(color); ink.setAlpha(130-j*30)
            p.setPen(QPen(ink, 1))
            rotation = self.phase*(42 if self.state == AssistantState.THINKING else 8)
            p.drawArc(QRectF(c.x()-r,c.y()-r,r*2,r*2), int((rotation+j*110)*16), 68*16)
        if self.state in (AssistantState.SPEAKING,AssistantState.EXECUTING,AssistantState.SUCCESS):
            wave = (age*.6)%1
            wave_color = QColor(color); wave_color.setAlpha(int((1-wave)*60))
            p.setPen(QPen(wave_color,1)); p.setBrush(Qt.NoBrush)
            wr = radius*(1+wave*.9); p.drawEllipse(c,wr,wr)
        dots = 6 if self.engine.quality in ("Baixo", "Desativado") else 18
        p.setPen(Qt.NoPen); p.setBrush(color)
        for j in range(dots):
            a = j*math.tau/dots + self.phase*.08
            r = radius*(1.45+.12*math.sin(j*2.1))
            p.drawEllipse(QPointF(c.x()+math.cos(a)*r,c.y()+math.sin(a)*r),1.4,1.4)
        p.end()
