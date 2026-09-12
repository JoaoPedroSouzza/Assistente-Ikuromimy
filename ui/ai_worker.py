"""
Threads separadas pra tudo que envolve rede/demora no Ollama: baixar
o instalador, baixar um modelo, e conversar — nenhuma dessas coisas
pode rodar no thread principal, senão a interface trava.
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from ui import ollama_manager
from core.execucao import ExecucaoCancelada


class DownloadInstaladorWorker(QThread):
    progresso = Signal(int, int)
    concluido = Signal(object)  # caminho (str) ou None

    def run(self) -> None:
        def progresso(b, t):
            if self.isInterruptionRequested():
                raise ExecucaoCancelada("Download cancelado")
            self.progresso.emit(b, t)
        caminho = ollama_manager.baixar_instalador(
            progresso=progresso
        )
        self.concluido.emit(caminho)


class BaixarModeloWorker(QThread):
    progresso = Signal(str, int, int)  # status, completado, total
    concluido = Signal(bool)

    def __init__(self, nome_modelo: str, parent=None):
        super().__init__(parent)
        self.nome_modelo = nome_modelo

    def run(self) -> None:
        def progresso(status, c, t):
            if self.isInterruptionRequested():
                raise ExecucaoCancelada("Download cancelado")
            self.progresso.emit(status, c, t)
        ok = ollama_manager.baixar_modelo(
            self.nome_modelo,
            progresso=progresso,
        )
        self.concluido.emit(ok)


class ChatWorker(QThread):
    pedaco_recebido = Signal(str)
    concluido = Signal(str)   # resposta completa
    erro = Signal(str)

    def __init__(self, modelo: str, mensagens: list[dict], parent=None):
        super().__init__(parent)
        self.modelo = modelo
        self.mensagens = mensagens

    def run(self) -> None:
        try:
            def receber(pedaco):
                if self.isInterruptionRequested():
                    raise ExecucaoCancelada("Conversa cancelada")
                self.pedaco_recebido.emit(pedaco)
            resposta = ollama_manager.enviar_mensagem(
                self.modelo,
                self.mensagens,
                on_chunk=receber,
            )
            self.concluido.emit(resposta)
        except Exception as erro:
            self.erro.emit(str(erro))
