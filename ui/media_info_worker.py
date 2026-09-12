"""
Consulta periodicamente qual música está tocando, numa QThread
separada — a consulta via Windows Media Control tem uma latência
pequena, e fazer isso no thread principal travaria a interface a cada
atualização.
"""

from __future__ import annotations

import time

from PySide6.QtCore import QThread, Signal

from ui import media_info


class MediaInfoPoller(QThread):

    atualizado = Signal(object)  # dict (ver media_info) ou None

    def __init__(self, intervalo: float = 3.0, parent=None):
        super().__init__(parent)
        self.intervalo = intervalo
        self._rodando = True

    def run(self) -> None:
        while self._rodando:
            info = media_info.obter_info_musica_atual()
            self.atualizado.emit(info)

            # dorme em pedacinhos pra reagir rápido ao parar(), em vez
            # de ficar travado num sleep() longo
            restante = self.intervalo
            while restante > 0 and self._rodando:
                passo = min(0.2, restante)
                time.sleep(passo)
                restante -= passo

    def parar(self) -> None:
        self._rodando = False

    def solicitar_parada(self) -> None:
        self.requestInterruption()
        self.parar()
