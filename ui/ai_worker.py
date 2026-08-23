"""
Threads separadas pra tudo que envolve rede/demora no Ollama: baixar
o instalador, baixar um modelo, e conversar — nenhuma dessas coisas
pode rodar no thread principal, senão a interface trava.
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from ui import ollama_manager


class DownloadInstaladorWorker(QThread):
    progresso = Signal(int, int)
    concluido = Signal(object)  # caminho (str) ou None

    def run(self) -> None:
        caminho = ollama_manager.baixar_instalador(
            progresso=lambda b, t: self.progresso.emit(b, t)
        )
        self.concluido.emit(caminho)


class BaixarModeloWorker(QThread):
    progresso = Signal(str, int, int)  # status, completado, total
    concluido = Signal(bool)

    def __init__(self, nome_modelo: str, parent=None):
        super().__init__(parent)
        self.nome_modelo = nome_modelo

    def run(self) -> None:
        ok = ollama_manager.baixar_modelo(
            self.nome_modelo,
            progresso=lambda status, c, t: self.progresso.emit(status, c, t),
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
            resposta = ollama_manager.enviar_mensagem(
                self.modelo,
                self.mensagens,
                on_chunk=lambda pedaco: self.pedaco_recebido.emit(pedaco),
            )
            self.concluido.emit(resposta)
        except Exception as erro:
            self.erro.emit(str(erro))
