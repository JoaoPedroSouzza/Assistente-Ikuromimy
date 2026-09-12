"""
Gerencia se o app abre sozinho junto com o Windows. A forma mais
simples e sem precisar mexer no Registro: colocar um atalho na pasta
de Inicialização do usuário — o Windows abre automaticamente tudo que
está lá quando você faz login.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    import win32com.client
    PYWIN32_DISPONIVEL = True
except ImportError:
    PYWIN32_DISPONIVEL = False

NOME_ATALHO = "Assistente Virtual Ikuromimy.lnk"


def pasta_inicializacao() -> Path:
    return (
        Path(os.environ["APPDATA"])
        / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    )


def caminho_atalho() -> Path:
    return pasta_inicializacao() / NOME_ATALHO


def executavel_atual() -> str | None:
    """Só faz sentido ativar isso quando o app já está rodando como o
    .exe empacotado (sys.frozen é True nesse caso). Rodando via
    'python interface.py' não tem o que apontar o atalho, então
    devolve None."""
    if getattr(sys, "frozen", False):
        return sys.executable
    return None


def esta_ativado() -> bool:
    return caminho_atalho().exists()


def ativar() -> bool:
    """Cria o atalho na pasta de Inicialização. Devolve False se não
    for possível (rodando via 'python interface.py', ou sem pywin32)."""
    exe = executavel_atual()
    if not exe or not PYWIN32_DISPONIVEL:
        return False

    shell = win32com.client.Dispatch("WScript.Shell")
    atalho = shell.CreateShortcut(str(caminho_atalho()))
    atalho.TargetPath = exe
    atalho.WorkingDirectory = os.path.dirname(exe)
    atalho.Description = "Assistente Virtual Ikuromimy"
    atalho.save()
    return True


def desativar() -> None:
    caminho = caminho_atalho()
    if caminho.exists():
        caminho.unlink()
