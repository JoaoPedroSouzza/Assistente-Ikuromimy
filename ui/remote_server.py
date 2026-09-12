"""
Servidor HTTP local (rede Wi-Fi da casa, não é exposto pra internet).
Recebe comandos vindos do app Android e repassa pro escravo.py — a
mesma lógica que o campo de texto da aba Início já usa.

Roda dentro de uma QThread pra não travar a interface enquanto está
escutando. Usa werkzeug.serving.make_server (em vez de app.run direto)
porque isso dá um jeito limpo de LIGAR e DESLIGAR o servidor sob
demanda — o app.run() padrão do Flask não tem um "parar" de fora.
"""

from __future__ import annotations

import secrets
import socket
import logging
from threading import Thread
from core import execucao

from flask import Flask, jsonify, request
from PySide6.QtCore import QThread
from werkzeug.serving import make_server

import escravo
from ui import system_info

PORTA_PADRAO = 5678
logger = logging.getLogger("ikuromimy.remoto")


def obter_ip_local() -> str:
    """Descobre o IP da máquina na rede local (não o 127.0.0.1), pra
    mostrar pro usuário digitar no celular. Não manda nem recebe nada
    de verdade pro 8.8.8.8 — só usa a tentativa de conexão UDP pra
    perguntar ao sistema operacional qual interface de rede seria
    usada, que é um jeito confiável de achar o IP local mesmo com
    várias placas de rede."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def obter_mac_local() -> str | None:
    """Descobre o endereço MAC da mesma placa de rede usada pelo
    obter_ip_local() — é esse endereço que o app Android precisa pra
    montar o 'pacote mágico' do Wake-on-LAN. Devolve None se não
    conseguir identificar (ex: alguma configuração de rede incomum)."""
    import psutil

    ip_local = obter_ip_local()

    for enderecos in psutil.net_if_addrs().values():
        tem_o_ip = any(
            e.family == socket.AF_INET and e.address == ip_local
            for e in enderecos
        )
        if not tem_o_ip:
            continue

        for e in enderecos:
            # AF_LINK/AF_PACKET é a "família" do endereço MAC — o
            # valor exato do enum varia por sistema, checar pelo nome
            # evita depender do número específico.
            if e.family.name in ("AF_LINK", "AF_PACKET"):
                return e.address.upper().replace("-", ":")

    return None


def gerar_token() -> str:
    return secrets.token_hex(16)  # 128 bits; chaves já salvas continuam válidas


class ServidorRemoto(QThread):
    """Uma instância = um servidor rodando. Chame start() pra ligar e
    parar() pra desligar (espera terminar com wait())."""

    def __init__(self, token: str, porta: int = PORTA_PADRAO, parent=None):
        super().__init__(parent)
        if not token:
            raise ValueError("A chave de acesso não pode ser vazia")
        self.token = token
        self.porta = porta
        self._app = self._criar_app()
        self._server = make_server("0.0.0.0", self.porta, self._app, threaded=True)

    def _checar_token(self):
        # todas as rotas exigem o token, inclusive /ping — se não exigisse
        # aqui, a tela de "Conectar" do celular sempre daria "sucesso"
        # mesmo com a chave errada, e o erro só apareceria depois, ao
        # tentar executar um comando de verdade.
        if not secrets.compare_digest(request.headers.get("X-Token", "").encode(), self.token.encode()):
            logger.warning("autenticacao_recusada")
            return jsonify({"erro": "token inválido"}), 401
        return None

    def _criar_app(self) -> Flask:
        app = Flask(__name__)
        app.config["MAX_CONTENT_LENGTH"] = 16 * 1024
        app.before_request(self._checar_token)

        @app.errorhandler(413)
        def corpo_grande(erro):
            return jsonify({"erro": "requisição muito grande"}), 413

        @app.route("/ping", methods=["GET"])
        def ping():
            return jsonify({"status": "ok", "app": "Assistente Virtual Ikuromimy"})

        @app.route("/comando", methods=["POST"])
        def comando():
            dados = request.get_json(silent=True)
            if not isinstance(dados, dict) or not isinstance(dados.get("texto"), str):
                return jsonify({"erro": "envie um objeto JSON com texto do tipo string"}), 400
            texto = dados["texto"].strip()
            if not texto:
                return jsonify({"erro": "comando vazio"}), 400
            if len(texto) > 4096:
                return jsonify({"erro": "comando muito longo"}), 400
            try:
                execucao.executar(texto)
                return jsonify({"ok": True})
            except Exception as erro:
                logger.warning("comando_falhou tipo=%s", type(erro).__name__)
                return jsonify({"erro": "não foi possível executar o comando"}), 500

        @app.route("/midia/<acao>", methods=["POST"])
        def midia(acao):
            acoes = {
                "play_pause": escravo.media_play_pause,
                "proxima": escravo.media_next,
                "anterior": escravo.media_prev,
            }
            funcao = acoes.get(acao)
            if not funcao:
                return jsonify({"erro": "ação desconhecida"}), 400
            try:
                execucao.executar_acao(funcao)
            except Exception as erro:
                logger.warning("midia_falhou tipo=%s", type(erro).__name__)
                return jsonify({"erro": "não foi possível executar a ação"}), 500
            return jsonify({"ok": True})

        @app.route("/sistema", methods=["GET"])
        def sistema():
            return jsonify(system_info.obter_resumo_sistema())

        return app

    def run(self) -> None:
        try:
            self._server.serve_forever()
        finally:
            self._server.server_close()

    def parar(self) -> None:
        if self.isRunning():
            self._server.shutdown()
        else:
            self._server.server_close()

    def solicitar_parada(self) -> None:
        self.requestInterruption()
        Thread(target=self.parar, daemon=True).start()
