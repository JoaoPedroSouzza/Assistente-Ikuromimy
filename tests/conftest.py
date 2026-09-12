"""Qt e persistência reais; efeitos externos substituídos nas fronteiras."""
import os
import socket
import subprocess
import sys
import tempfile
import types
import urllib.request
import webbrowser
from unittest.mock import MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import psutil
import pytest
from PySide6.QtCore import QSettings
from PySide6 import QtCore


class EfeitoExternoBloqueado(BaseException):
    """Não é engolido pelos except Exception do aplicativo."""


def bloquear(*args, **kwargs):
    raise EfeitoExternoBloqueado("Efeito externo não simulado pelo teste")


class SettingsTemporarios(QSettings):
    """Força INI também no construtor (organização, aplicativo) do Windows."""

    raiz = None

    def __init__(self, *args, **kwargs):
        if self.raiz is None:
            raise EfeitoExternoBloqueado("QSettings fora da fixture de isolamento")
        if len(args) == 2 and all(isinstance(arg, str) for arg in args):
            super().__init__(QSettings.IniFormat, QSettings.UserScope, *args, **kwargs)
        else:
            super().__init__(*args, **kwargs)


# O construtor de duas strings usa NativeFormat no Windows, mesmo quando
# setDefaultFormat é INI. O adaptador mantém leitura/escrita e sync reais.
QtCore.QSettings = SettingsTemporarios


# Substituição explícita antes de importar o assistente. Qt NÃO é simulado.
for nome, atributos in {
    "pyautogui": ("press", "hotkey", "write"),
    "gtts": ("gTTS",),
    "playsound": ("playsound",),
    "sounddevice": ("rec", "wait", "play", "playrec", "InputStream", "OutputStream", "RawInputStream"),
}.items():
    modulo = types.ModuleType(nome)
    for atributo in atributos:
        setattr(modulo, atributo, MagicMock(side_effect=bloquear))
    sys.modules[nome] = modulo


@pytest.fixture(autouse=True)
def ambiente_isolado(monkeypatch, tmp_path):
    """Defesa contra acidentes; não equivale a uma sandbox de segurança.

    Cada teste recebe arquivos próprios. Uma fronteira exercitada precisa
    ser substituída explicitamente pelo teste que verifica seu contrato.
    """
    formato_anterior = QSettings.defaultFormat()
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path / "user"))
    QSettings.setPath(QSettings.IniFormat, QSettings.SystemScope, str(tmp_path / "system"))
    monkeypatch.setattr(SettingsTemporarios, "raiz", tmp_path)
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    for nome in ("APPDATA", "LOCALAPPDATA", "TEMP", "TMP", "HOME", "USERPROFILE"):
        monkeypatch.setenv(nome, str(tmp_path))
    for objeto, nomes in (
        (socket.socket, ("connect", "connect_ex", "bind", "sendto")),
        (urllib.request, ("urlopen", "urlretrieve")),
        (subprocess, ("Popen",)),
        (webbrowser, ("open", "open_new", "open_new_tab")),
        (os, ("system", "startfile", "kill")),
        (psutil, ("process_iter",)),
        (psutil.Process, ("terminate", "kill", "send_signal")),
    ):
        for nome in nomes:
            if hasattr(objeto, nome):
                monkeypatch.setattr(objeto, nome, bloquear)
    for nome in ("pyautogui", "gtts", "playsound", "sounddevice"):
        for valor in vars(sys.modules[nome]).values():
            if isinstance(valor, MagicMock):
                valor.reset_mock(return_value=True, side_effect=True)
                valor.side_effect = bloquear
    import escravo
    import sounddevice
    import speech_recognition
    from ui import media_info, system_info, startup_manager
    for nome in ("rec", "play", "playrec", "InputStream", "OutputStream", "RawInputStream"):
        monkeypatch.setattr(sounddevice, nome, bloquear)
    monkeypatch.setattr(speech_recognition.Recognizer, "recognize_google", bloquear)
    if sys.platform == "win32":
        import comtypes
        monkeypatch.setattr(comtypes, "CoCreateInstance", bloquear)
    monkeypatch.setattr(media_info, "PYWIN32_DISPONIVEL", False)
    monkeypatch.setattr(media_info, "_cache_capa", {})
    monkeypatch.setattr(system_info, "PYWIN32_DISPONIVEL", False)
    monkeypatch.setattr(startup_manager, "PYWIN32_DISPONIVEL", False)
    monkeypatch.setattr(escravo, "VOZ_ATIVA", False)
    monkeypatch.setattr(escravo, "PYWIN32_DISPONIVEL", False)
    monkeypatch.setattr(escravo, "WINREG_DISPONIVEL", False)
    monkeypatch.setattr(escravo, "TEMP_DIR", tmp_path)
    monkeypatch.setattr(escravo, "_CACHE_CARREGADO", False)
    monkeypatch.setattr(escravo, "_CACHE_APPS", {})
    try:
        yield
    finally:
        QSettings.setDefaultFormat(formato_anterior)


@pytest.fixture
def desktop_simulado(monkeypatch):
    """Interface real; fontes de dados e hardware previsíveis."""
    import escravo
    from ui import ollama_manager, system_info, audio_control, media_info
    from ui.pages import remote_page
    monkeypatch.setattr(escravo, "listar_apps_conhecidos", lambda: ["editor"])
    monkeypatch.setattr(ollama_manager, "ollama_esta_instalado", lambda: True)
    monkeypatch.setattr(ollama_manager, "ollama_esta_rodando", lambda: True)
    monkeypatch.setattr(ollama_manager, "listar_modelos_instalados", lambda: ["modelo-teste"])
    monkeypatch.setattr(remote_page, "obter_ip_local", lambda: "127.0.0.1")
    monkeypatch.setattr(remote_page, "obter_mac_local", lambda: None)
    monkeypatch.setattr(audio_control, "_obter_interface_volume", lambda: MagicMock())
    monkeypatch.setattr(media_info, "obter_info_musica_atual", lambda: None)
    monkeypatch.setattr(system_info, "obter_resumo_sistema", lambda: {
        "processador": "CPU de teste", "nucleos": "4 núcleos",
        "ram": {"total": "8 GB", "uso": "50%"}, "placas_de_video": [],
        "armazenamento": [], "sistema_operacional": "Windows de teste",
    })
