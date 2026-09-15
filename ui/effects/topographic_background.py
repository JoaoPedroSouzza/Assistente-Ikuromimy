"""Parametric contour field inspired by organic topographic maps; no bitmap."""
import math
import numpy as np
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPolygonF, QPen
from PySide6.QtWidgets import QWidget
from ui.animations.animation_engine import QUALITY
from ui.state.assistant_state import AssistantState
from ui.theme.colors import BACKGROUND, ERROR

class TopographicBackground(QWidget):
    def __init__(self, engine, theme, bus, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.engine, self.theme = engine, theme
        self.state = AssistantState.IDLE
        self.audio = self.target_audio = 0.
        self.mouse = self.target_mouse = QPointF()
        self.pulse = 1.
        self.phase = 0.
        self.center = QPointF(.5, .5)
        self._angles = {}
        self._geometry_key = None
        self._geometry = []
        engine.frame.connect(self.advance)
        theme.changed.connect(lambda _: self.update())
        bus.assistant_state_changed.connect(self.state_changed)
        bus.audio_level_changed.connect(self.audio_changed)

    def state_changed(self, state, detail):
        self.state = state
        if state in (AssistantState.EXECUTING, AssistantState.SUCCESS, AssistantState.ERROR):
            self.pulse = 0.
        self.update()

    def audio_changed(self, level):
        self.target_audio = level

    def advance(self, dt):
        if not self.isVisible():
            return
        self.phase += dt * (.25 if self.state == AssistantState.OFFLINE else 1.)
        a = 1 - math.exp(-dt * 6)
        self.audio += (self.target_audio - self.audio) * a
        self.mouse += (self.target_mouse - self.mouse) * a
        self.pulse = min(1., self.pulse + dt * .55)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(BACKGROUND))
        painter.setRenderHint(QPainter.Antialiasing)
        _, lines, samples = QUALITY[self.engine.quality]
        w, h = self.width(), self.height()
        # Geometry has its own bounded update rate; color still interpolates every frame.
        geometry_hz = 30 if self.engine.quality == "Alto" else (20 if self.engine.quality == "Médio" else 12)
        key = (w,h,lines,samples,int(self.phase*geometry_hz),self.state,
               round(self.audio,2),round(self.mouse.x(),2),round(self.mouse.y(),2),round(self.pulse,2))
        if key != self._geometry_key:
            self._geometry_key = key
            self._geometry = []
            if samples not in self._angles:
                angles = np.linspace(0,math.tau,samples+1)
                self._angles[samples] = (angles,np.cos(angles),np.sin(angles))
            angles, cosine, sine = self._angles[samples]
            for cluster,(cx,cy,scale) in enumerate(((.06,.19,.95),(.87,.08,.78),(.92,.92,1.15),(.14,.94,.68))):
                x0 = w*cx + self.mouse.x()*(8+cluster*3)
                y0 = h*cy + self.mouse.y()*(8+cluster*3)
                base = 1 + .14*np.sin(3*angles+cluster+self.phase*.10) + .09*np.cos(5*angles-self.phase*.07)
                for line in range(lines):
                    radius = (22+line*13)*scale
                    r = radius*(base+.06*np.sin(angles*2+line*.10))
                    x = x0 + cosine*r*1.45; y = y0 + sine*r
                    dx = x-w*self.center.x(); dy = y-h*self.center.y()
                    dist = np.maximum(1,np.hypot(dx,dy))
                    effect = np.zeros_like(dist)
                    if self.state == AssistantState.THINKING:
                        effect -= 9*np.exp(-dist/250)*(.6+.4*math.sin(self.phase*2))
                    elif self.state in (AssistantState.LISTENING,AssistantState.SPEAKING):
                        effect += self.audio*14*np.sin(dist*.024-self.phase*4)*np.exp(-dist/600)
                    if self.pulse < 1:
                        effect += 12*np.exp(-((dist-self.pulse*max(w,h))/65)**2)*(1-self.pulse)
                    if self.state == AssistantState.ERROR:
                        effect += 2*np.sin(angles*21+self.phase*9)*np.exp(-dist/400)
                    x += dx/dist*effect; y += dy/dist*effect
                    polygon = QPolygonF([QPointF(float(xx),float(yy)) for xx,yy in zip(x,y)])
                    self._geometry.append((line,polygon))
        for line, polygon in self._geometry:
            color = self.theme.line_color(line/max(1,lines-1))
            if self.state == AssistantState.ERROR: color = QColor(ERROR)
            color.setAlpha(22 if self.state == AssistantState.OFFLINE else (82 if line%5 == 0 else 37))
            painter.setPen(QPen(color,1.1 if line%5 == 0 else .7))
            painter.drawPolyline(polygon)
        painter.end()
