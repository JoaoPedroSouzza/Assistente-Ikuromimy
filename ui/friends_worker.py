"""
Duas threads separadas:
  - PresencaWorker: manda "estou online" pro Firebase periodicamente
    enquanto o app estiver aberto (com o que está tocando, se tiver).
  - ListaAmigosWorker: busca a lista de amizades + perfil + presença
    de cada amigo, uma vez por chamada (a página chama de novo a cada
    intervalo, via QTimer).
"""

from __future__ import annotations

import time

from PySide6.QtCore import QThread, Signal

from ui import firebase_client

SEGUNDOS_PARA_CONSIDERAR_OFFLINE = 90


class PresencaWorker(QThread):

    def __init__(self, intervalo: float = 20.0, parent=None):
        super().__init__(parent)
        self.intervalo = intervalo
        self._rodando = True

    def run(self) -> None:
        while self._rodando:
            try:
                status = self._status_atual()
                firebase_client.atualizar_presenca(True, status)
            except Exception:
                pass

            restante = self.intervalo
            while restante > 0 and self._rodando:
                passo = min(0.5, restante)
                time.sleep(passo)
                restante -= passo

    def _status_atual(self) -> str:
        try:
            from ui import media_info
            info = media_info.obter_info_musica_atual()
            if info and info.get("tocando") and info.get("titulo"):
                artista = info.get("artista", "")
                return f"🎵 {info['titulo']} - {artista}" if artista else f"🎵 {info['titulo']}"
        except Exception:
            pass

        try:
            from ui import command_history
            historico = command_history.carregar_historico()
            if historico:
                return f"⚙ {historico[0]}"
        except Exception:
            pass

        return "Usando o Assistente Ikuromimy"

    def parar(self) -> None:
        self.solicitar_parada()
        self.wait(2000)

    def solicitar_parada(self) -> None:
        self.requestInterruption()
        self._rodando = False


class ListaAmigosWorker(QThread):

    concluido = Signal(list)  # cada item: {uid, nome_usuario, status_amizade, online, status_texto}
    erro = Signal(str)

    def run(self) -> None:
        try:
            amizades, sessao = firebase_client.listar_amizades()
            if not sessao:
                self.concluido.emit([])
                return

            resultado = []
            for uid_amigo, status_amizade in amizades.items():
                if not status_amizade:
                    continue

                perfil = firebase_client.obter_perfil(uid_amigo, sessao) or {}
                presenca = firebase_client.obter_presenca(uid_amigo, sessao) or {}

                online = bool(presenca.get("online", False))
                atualizado_em = presenca.get("atualizado_em", 0)
                if time.time() - atualizado_em > SEGUNDOS_PARA_CONSIDERAR_OFFLINE:
                    online = False

                resultado.append({
                    "uid": uid_amigo,
                    "nome_usuario": perfil.get("nome_usuario", "?"),
                    "status_amizade": status_amizade,
                    "online": online,
                    "status_texto": presenca.get("status_texto", ""),
                })

            self.concluido.emit(resultado)
        except Exception as erro:
            self.erro.emit(str(erro))


class MensagensWorker(QThread):
    """Busca a conversa com um amigo específico. A página de chat cria
    uma instância nova a cada atualização (padrão simples de polling,
    igual o resto do app já usa)."""

    concluido = Signal(list)  # lista de {remetente, texto, timestamp}
    erro = Signal(str)

    def __init__(self, uid_amigo: str, parent=None):
        super().__init__(parent)
        self.uid_amigo = uid_amigo

    def run(self) -> None:
        try:
            mensagens = firebase_client.buscar_mensagens(self.uid_amigo)
            self.concluido.emit(mensagens)
        except Exception as erro:
            self.erro.emit(str(erro))
