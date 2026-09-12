"""
Guarda a "chave de acesso" (token) do controle remoto entre sessões,
usando o mesmo mecanismo (QSettings) que o theme_manager já usa pro
tema. Gera uma chave nova automaticamente na primeira vez.
"""

from __future__ import annotations

from PySide6.QtCore import QSettings

from ui.remote_server import gerar_token

_ORG = "Ikuromimy"
_APP = "AssistenteVirtual"
_CHAVE_TOKEN = "remoto/token"


def carregar_token() -> str:
    settings = QSettings(_ORG, _APP)
    token = settings.value(_CHAVE_TOKEN, "")
    if not token:
        token = gerar_token()
        salvar_token(token)
    return token


def salvar_token(token: str) -> None:
    settings = QSettings(_ORG, _APP)
    settings.setValue(_CHAVE_TOKEN, token)
