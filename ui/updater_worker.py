"""
Roda a verificação e o download da atualização numa QThread — consulta
ao GitHub e download do .exe não podem travar a interface.
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from ui import updater


class UpdaterWorker(QThread):

    progresso = Signal(int, int)     # bytes baixados, total
    verificado = Signal(object)        # dict {ok, atualizacao, erro} — ver updater.py
    concluido = Signal(bool, str)      # sucesso, mensagem

    def __init__(self, modo: str, url_download: str = "", parent=None):
        super().__init__(parent)
        self.modo = modo  # "verificar" ou "baixar"
        self.url_download = url_download

    def run(self) -> None:
        if self.modo == "verificar":
            resultado = updater.verificar_atualizacao()
            self.verificado.emit(resultado)
            return

        if self.modo == "baixar":
            caminho = updater.baixar_atualizacao(
                self.url_download,
                progresso=lambda baixado, total: self.progresso.emit(baixado, total),
            )
            if not caminho:
                self.concluido.emit(False, "❌ Falha ao baixar a atualização.")
                return

            try:
                ok = updater.aplicar_atualizacao(caminho)
            except Exception as erro:
                self.concluido.emit(False, f"❌ Não consegui iniciar a atualização: {erro}")
                return
            if ok:
                self.concluido.emit(True, "✓ Atualizando... o app vai fechar e abrir de novo.")
            else:
                self.concluido.emit(
                    False,
                    "❌ Só dá pra atualizar sozinho no app já empacotado (.exe).",
                )
