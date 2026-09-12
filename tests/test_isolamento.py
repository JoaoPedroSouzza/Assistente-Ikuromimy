import os
import socket
import subprocess
import urllib.request
import webbrowser

import pytest
import escravo
from conftest import EfeitoExternoBloqueado


@pytest.mark.parametrize("acao", [
    lambda: subprocess.Popen(["nao-executar"]),
    lambda: webbrowser.open("https://example.invalid"),
    lambda: urllib.request.urlopen("https://example.invalid"),
    lambda: os.system("nao-executar"),
    lambda: escravo.pyautogui.press("playpause"),
])
def test_fronteiras_exigem_simulacao_explicita(acao):
    with pytest.raises(EfeitoExternoBloqueado):
        acao()


def test_socket_nao_abre_servidor():
    with socket.socket() as cliente:
        with pytest.raises(EfeitoExternoBloqueado):
            cliente.bind(("127.0.0.1", 0))
