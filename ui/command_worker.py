"""Executa comandos fora da thread da interface."""
from PySide6.QtCore import QThread, Signal
from core import execucao


class CommandWorker(QThread):
    concluido = Signal(bool)
    erro = Signal(str)

    def __init__(self, comando: str, parent=None):
        super().__init__(parent)
        self.comando = comando

    def run(self):
        try:
            resultado = execucao.executar(self.comando, self.isInterruptionRequested)
            self.concluido.emit(resultado)
        except Exception as erro:
            self.erro.emit(str(erro))
