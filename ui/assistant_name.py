"""
Nome do assistente, usado como palavra de ativação na escuta contínua
(ex: dizer "Jarvis, abrir spotify" em vez de "assistente, abrir
spotify"). Editável na aba Configurações, persistido entre sessões.
"""

from __future__ import annotations

from PySide6.QtCore import QSettings

_ORG = "Ikuromimy"
_APP = "AssistenteVirtual"
_CHAVE_NOME = "assistente/nome"

NOME_PADRAO = "Assistente"


def carregar_nome() -> str:
    settings = QSettings(_ORG, _APP)
    nome = settings.value(_CHAVE_NOME, NOME_PADRAO)
    return nome.strip() if nome and nome.strip() else NOME_PADRAO


def salvar_nome(nome: str) -> str:
    """Salva o nome (limpo) e devolve o valor que foi efetivamente
    salvo (cai pro padrão se vier vazio)."""
    nome = nome.strip()
    if not nome:
        nome = NOME_PADRAO
    settings = QSettings(_ORG, _APP)
    settings.setValue(_CHAVE_NOME, nome)
    return nome
