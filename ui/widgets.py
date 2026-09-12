"""
Widgets reutilizáveis do app.
"""

from __future__ import annotations

import math

from PySide6.QtCore import Qt, QPointF, Signal
from PySide6.QtGui import QColor, QConicalGradient, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget


class ColorWheel(QWidget):
    """Roda de cores estilo HSV: matiz (hue) percorre a circunferência,
    saturação vai do centro (branco) até a borda (cor pura). O brilho
    (value) é controlado por fora, com um slider — assim a roda continua
    legível em qualquer brilho escolhido."""

    corSelecionada = Signal(QColor)

    def __init__(self, tamanho: int = 200, parent=None):
        super().__init__(parent)
        self.setFixedSize(tamanho, tamanho)
        self.setCursor(Qt.PointingHandCursor)

        self._hue = 0.62   # ~223°, um azul-arroxeado como padrão
        self._sat = 0.55
        self._val = 0.85
        self._arrastando = False

    # ------------------------------------------------------------------
    # cor atual / definir cor de fora (ex: vindo de um campo hex)
    # ------------------------------------------------------------------

    def cor_atual(self) -> QColor:
        cor = QColor()
        cor.setHsvF(self._hue, self._sat, self._val)
        return cor

    def definir_cor(self, cor: QColor) -> None:
        h, s, v, _ = cor.getHsvF()
        self._hue = h if h >= 0 else 0.0
        self._sat = s
        self._val = max(v, 0.35)
        self.update()

    def definir_brilho(self, valor: float) -> None:
        self._val = max(0.15, min(1.0, valor))
        self.update()
        self.corSelecionada.emit(self.cor_atual())

    # ------------------------------------------------------------------
    # geometria auxiliar
    # ------------------------------------------------------------------

    def _raio(self) -> float:
        return min(self.width(), self.height()) / 2 - 4

    def _centro(self) -> QPointF:
        return QPointF(self.width() / 2, self.height() / 2)

    # ------------------------------------------------------------------
    # desenho
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        centro = self._centro()
        raio = self._raio()

        # camada 1: matiz ao redor (gradiente cônico)
        gradiente_hue = QConicalGradient(centro, 0)
        for i in range(0, 361, 10):
            cor = QColor()
            cor.setHsvF(i / 360, 1.0, self._val)
            gradiente_hue.setColorAt(i / 360, cor)

        painter.setPen(Qt.NoPen)
        painter.setBrush(gradiente_hue)
        painter.drawEllipse(centro, raio, raio)

        # camada 2: saturação (branco no centro, transparente na borda)
        gradiente_sat = QRadialGradient(centro, raio)
        gradiente_sat.setColorAt(0.0, QColor(255, 255, 255, 255))
        gradiente_sat.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(gradiente_sat)
        painter.drawEllipse(centro, raio, raio)

        # marcador da cor selecionada
        angulo = math.radians(self._hue * 360)
        dist = self._sat * raio
        x = centro.x() + dist * math.cos(angulo)
        y = centro.y() - dist * math.sin(angulo)

        painter.setPen(QPen(QColor("#ffffff"), 2))
        painter.setBrush(self.cor_atual())
        painter.drawEllipse(QPointF(x, y), 7, 7)

    # ------------------------------------------------------------------
    # interação do mouse
    # ------------------------------------------------------------------

    def _atualizar_por_posicao(self, pos: QPointF) -> None:
        centro = self._centro()
        raio = self._raio()

        dx = pos.x() - centro.x()
        dy = centro.y() - pos.y()
        dist = min(math.hypot(dx, dy), raio)

        angulo = math.degrees(math.atan2(dy, dx))
        if angulo < 0:
            angulo += 360

        self._hue = angulo / 360
        self._sat = dist / raio if raio else 0.0

        self.update()
        self.corSelecionada.emit(self.cor_atual())

    def mousePressEvent(self, event) -> None:
        self._arrastando = True
        self._atualizar_por_posicao(event.position())

    def mouseMoveEvent(self, event) -> None:
        if self._arrastando:
            self._atualizar_por_posicao(event.position())

    def mouseReleaseEvent(self, event) -> None:
        self._arrastando = False
