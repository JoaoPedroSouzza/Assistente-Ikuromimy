import io
import json
from unittest.mock import MagicMock

import pytest
from ui import updater


@pytest.mark.parametrize("versao,esperado", [("v1.2.3", (1,2,3)), ("V2.0-beta", (2,0)), (" 3.4 ", (3,4))])
def test_versao_para_tupla(versao, esperado):
    assert updater._versao_para_tupla(versao) == esperado


class Resposta(io.BytesIO):
    def __init__(self, dados):
        super().__init__(dados)
        self.headers = {}


def test_verificar_atualizacao_disponivel(monkeypatch):
    monkeypatch.setattr(updater, "VERSAO", "1.0.0")
    dados = {"tag_name": "v99.0", "body": "notas", "assets": [{"name":"app.exe", "browser_download_url":"https://x/app.exe"}]}
    monkeypatch.setattr(updater.urllib.request, "urlopen", lambda *a, **k: Resposta(json.dumps(dados).encode()))
    r = updater.verificar_atualizacao()
    assert r["ok"] and r["atualizacao"]["tag"] == "v99.0"


def test_verificar_sem_exe(monkeypatch):
    monkeypatch.setattr(updater, "VERSAO", "1.0.0")
    dados = {"tag_name": "v99.0", "assets": []}
    monkeypatch.setattr(updater.urllib.request, "urlopen", lambda *a, **k: Resposta(json.dumps(dados).encode()))
    r = updater.verificar_atualizacao()
    assert not r["ok"] and ".exe" in r["erro"]


def test_verificar_falha_de_rede(monkeypatch):
    monkeypatch.setattr(updater.urllib.request, "urlopen", MagicMock(side_effect=OSError("offline")))
    r = updater.verificar_atualizacao()
    assert not r["ok"] and r["atualizacao"] is None


def test_executavel_atual_somente_empacotado(monkeypatch):
    monkeypatch.delattr(updater.sys, "frozen", raising=False)
    assert updater.executavel_atual() is None
    monkeypatch.setattr(updater.sys, "frozen", True, raising=False)
    monkeypatch.setattr(updater.sys, "executable", "C:/app.exe")
    assert updater.executavel_atual() == "C:/app.exe"


def test_aplicar_recusa_quando_nao_empacotado(monkeypatch):
    monkeypatch.setattr(updater, "executavel_atual", lambda: None)
    assert updater.aplicar_atualizacao("novo.exe") is False


@pytest.mark.parametrize("tag", ["v1.0.0", "v0.9.0"])
def test_versao_igual_ou_antiga_nao_oferece_download(monkeypatch, tag):
    monkeypatch.setattr(updater, "VERSAO", "1.0.0")
    monkeypatch.setattr(updater.urllib.request, "urlopen",
                        lambda *a, **k: Resposta(json.dumps({"tag_name": tag}).encode()))
    assert updater.verificar_atualizacao() == {"ok": True, "atualizacao": None, "erro": None}
