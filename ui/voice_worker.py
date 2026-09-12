"""
Roda a gravação + transcrição numa thread separada — gravar 6 segundos
e depois esperar a resposta do reconhecedor não pode travar a UI.
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from ui import voice_input


class VoiceWorker(QThread):

    concluido = Signal(str)   # texto reconhecido
    erro = Signal(str)

    def __init__(self, duracao_segundos: float = 6.0, parent=None):
        super().__init__(parent)
        self.duracao_segundos = duracao_segundos

    def run(self) -> None:
        try:
            texto = voice_input.gravar_e_transcrever(self.duracao_segundos)
            self.concluido.emit(texto)
        except Exception as erro:
            self.erro.emit(str(erro))
