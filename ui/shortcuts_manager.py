"""
Atalhos: botões que executam um comando pronto com um clique só.
Existe uma lista padrão que já vem pronta na primeira vez que o app
abre, mas a partir daí TUDO (padrão ou criado por você) vira um
registro igual — editável e removível, sem distinção especial.

Cada atalho tem um 'id' interno estável, pra dar pra editar o nome
sem perder a referência de qual atalho é qual.
"""

from __future__ import annotations

import json
import uuid

from PySide6.QtCore import QSettings

_ORG = "Ikuromimy"
_APP = "AssistenteVirtual"
_CHAVE_ATALHOS = "atalhos/lista"

_ATALHOS_PADRAO_INICIAIS = [
    {"label": "🎵 Abrir Spotify", "comando": "abrir spotify"},
    {"label": "🌐 Abrir Chrome", "comando": "abrir chrome"},
    {"label": "🔍 Pesquisar", "comando": "pesquisar "},
    {"label": "⏯ Play / Pause", "comando": "play"},
    {"label": "⏭ Próxima faixa", "comando": "próxima"},
]


def _com_id(atalho: dict) -> dict:
    if "id" not in atalho:
        atalho = {**atalho, "id": uuid.uuid4().hex}
    return atalho


def listar_atalhos() -> list[dict]:
    settings = QSettings(_ORG, _APP)
    bruto = settings.value(_CHAVE_ATALHOS, "")

    if not bruto:
        # primeira vez que o app abre: semeia com os padrões, já como
        # registros normais (editáveis/removíveis igual qualquer outro)
        atalhos = [_com_id(a) for a in _ATALHOS_PADRAO_INICIAIS]
        _salvar(atalhos)
        return atalhos

    try:
        atalhos = json.loads(bruto)
    except (json.JSONDecodeError, TypeError):
        atalhos = []

    # compatibilidade com registros salvos antes de existir o 'id'
    atalhos = [_com_id(a) for a in atalhos]
    return atalhos


def _salvar(atalhos: list[dict]) -> None:
    settings = QSettings(_ORG, _APP)
    settings.setValue(_CHAVE_ATALHOS, json.dumps(atalhos))


def adicionar_atalho(label: str, comando: str) -> None:
    if not label.strip() or not comando.strip():
        return
    atalhos = listar_atalhos()
    atalhos.append({"id": uuid.uuid4().hex, "label": label.strip(), "comando": comando.strip()})
    _salvar(atalhos)


def editar_atalho(id_atalho: str, novo_label: str, novo_comando: str) -> None:
    if not novo_label.strip() or not novo_comando.strip():
        return
    atalhos = listar_atalhos()
    for atalho in atalhos:
        if atalho["id"] == id_atalho:
            atalho["label"] = novo_label.strip()
            atalho["comando"] = novo_comando.strip()
            break
    _salvar(atalhos)


def remover_atalho(id_atalho: str) -> None:
    atalhos = listar_atalhos()
    atalhos = [a for a in atalhos if a["id"] != id_atalho]
    _salvar(atalhos)
