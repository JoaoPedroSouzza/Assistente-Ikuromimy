"""
Modos: grupos de até 5 comandos que executam em sequência com um
clique só. Cada modo tem um 'id' interno estável, pra dar pra editar
o nome/comandos sem perder a referência de qual modo é qual.
"""

from __future__ import annotations

import json
import uuid

from PySide6.QtCore import QSettings

_ORG = "Ikuromimy"
_APP = "AssistenteVirtual"
_CHAVE_MODOS = "modos/personalizados"

LIMITE_COMANDOS_POR_MODO = 5


def _com_id(modo: dict) -> dict:
    if "id" not in modo:
        modo = {**modo, "id": uuid.uuid4().hex}
    return modo


def listar_modos() -> list[dict]:
    settings = QSettings(_ORG, _APP)
    bruto = settings.value(_CHAVE_MODOS, "")
    if not bruto:
        return []
    try:
        modos = json.loads(bruto)
    except (json.JSONDecodeError, TypeError):
        return []

    # compatibilidade com registros salvos antes de existir o 'id'
    atualizados = [_com_id(m) for m in modos]
    if atualizados != modos:
        _salvar_modos(atualizados)
    return atualizados


def _salvar_modos(modos: list[dict]) -> None:
    settings = QSettings(_ORG, _APP)
    settings.setValue(_CHAVE_MODOS, json.dumps(modos))


def adicionar_modo(nome: str, comandos: list[str]) -> None:
    comandos = [c.strip() for c in comandos if c.strip()][:LIMITE_COMANDOS_POR_MODO]
    if not nome.strip() or not comandos:
        return

    modos = listar_modos()
    modos.append({"id": uuid.uuid4().hex, "nome": nome.strip(), "comandos": comandos})
    _salvar_modos(modos)


def editar_modo(id_modo: str, novo_nome: str, novos_comandos: list[str]) -> None:
    novos_comandos = [c.strip() for c in novos_comandos if c.strip()][:LIMITE_COMANDOS_POR_MODO]
    if not novo_nome.strip() or not novos_comandos:
        return

    modos = listar_modos()
    for modo in modos:
        if modo["id"] == id_modo:
            modo["nome"] = novo_nome.strip()
            modo["comandos"] = novos_comandos
            break
    _salvar_modos(modos)


def remover_modo(id_modo: str) -> None:
    modos = listar_modos()
    modos = [m for m in modos if m["id"] != id_modo]
    _salvar_modos(modos)
