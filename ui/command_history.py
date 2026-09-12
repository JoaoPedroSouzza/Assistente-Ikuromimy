"""
Histórico dos últimos comandos digitados, usado pra alimentar o
autocompletar do campo de comando. Guarda só os últimos N (mais
recente primeiro), persistido via QSettings.
"""

from __future__ import annotations

import json

from PySide6.QtCore import QSettings

_ORG = "Ikuromimy"
_APP = "AssistenteVirtual"
_CHAVE_HISTORICO = "comandos/historico"
_LIMITE = 50


def carregar_historico() -> list[str]:
    settings = QSettings(_ORG, _APP)
    bruto = settings.value(_CHAVE_HISTORICO, "")
    if not bruto:
        return []
    try:
        dados = json.loads(bruto)
        return dados if isinstance(dados, list) and all(isinstance(c, str) for c in dados) else []
    except (json.JSONDecodeError, TypeError):
        return []


def adicionar_ao_historico(comando: str) -> list[str]:
    comando = comando.strip()
    if not comando:
        return []

    historico = carregar_historico()
    if historico and historico[0] == comando:
        return historico

    # remove duplicata se já existir, pra subir pro topo de novo
    historico = [c for c in historico if c != comando]
    historico.insert(0, comando)
    historico = historico[:_LIMITE]

    settings = QSettings(_ORG, _APP)
    settings.setValue(_CHAVE_HISTORICO, json.dumps(historico))
    return historico
