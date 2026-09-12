"""
Executa a lista de comandos de um modo, um atrás do outro, numa
thread separada — pra não travar a interface enquanto os comandos
rodam (alguns, como tocar música, têm esperas de vários segundos).
"""

from __future__ import annotations

import time

from PySide6.QtCore import QThread
from core import execucao

# pausa entre um comando e o próximo do mesmo modo, pra dar tempo do
# comando anterior (ex: abrir um app) se estabilizar antes do próximo
PAUSA_ENTRE_COMANDOS = 0.6


class ExecutorModo(QThread):

    def __init__(self, comandos: list[str], parent=None):
        super().__init__(parent)
        self.comandos = comandos

    def run(self) -> None:
        for comando in self.comandos:
            if self.isInterruptionRequested():
                break
            try:
                if not execucao.executar(comando, self.isInterruptionRequested):
                    break
            except Exception as erro:
                print(f"⚠️ Erro executando \"{comando}\" dentro do modo: {erro}")
            limite = time.monotonic() + PAUSA_ENTRE_COMANDOS
            while not self.isInterruptionRequested() and time.monotonic() < limite:
                time.sleep(min(0.05, max(0, limite - time.monotonic())))
