"""
Roda a EscutaContinua numa QThread — precisa rodar continuamente em
segundo plano, sem travar a interface.
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from ui.wake_word_listener import EscutaContinua


class WakeWordWorker(QThread):

    frase_detectada = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._escuta: EscutaContinua | None = None

    def run(self) -> None:
        self._escuta = EscutaContinua(
            ao_detectar_frase=lambda texto: self.frase_detectada.emit(texto)
        )
        if not self.isInterruptionRequested():
            self._escuta.iniciar()  # bloqueia até parar() ser chamado

    def parar(self) -> None:
        self.solicitar_parada()
        self.wait(2000)

    def solicitar_parada(self) -> None:
        self.requestInterruption()
        if self._escuta:
            self._escuta.solicitar_parada()
