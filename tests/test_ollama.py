import json
from unittest.mock import MagicMock

from ui import ollama_manager as om


class Resposta:
    def __init__(self, linhas): self.linhas = linhas
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def __iter__(self): return iter(self.linhas)
    def read(self): return b"".join(self.linhas)


def test_detecta_ollama_no_path(monkeypatch):
    monkeypatch.setattr(om.shutil, "which", lambda nome: "C:/ollama.exe")
    assert om.ollama_esta_instalado()


def test_rodando_false_em_erro(monkeypatch):
    monkeypatch.setattr(om.urllib.request, "urlopen", MagicMock(side_effect=OSError()))
    assert not om.ollama_esta_rodando()


def test_lista_modelos(monkeypatch):
    data = json.dumps({"models": [{"name":"llama3.2:1b"}, {"name":"phi"}]}).encode()
    monkeypatch.setattr(om.urllib.request, "urlopen", lambda *a, **k: Resposta([data]))
    assert om.listar_modelos_instalados() == ["llama3.2:1b", "phi"]


def test_chat_streaming(monkeypatch):
    linhas = [b'{"message":{"content":"Ola "}}\n', b'{"message":{"content":"mundo"},"done":true}\n']
    monkeypatch.setattr(om.urllib.request, "urlopen", lambda *a, **k: Resposta(linhas))
    partes = []
    assert om.enviar_mensagem("modelo", [{"role":"user","content":"oi"}], partes.append) == "Ola mundo"
    assert partes == ["Ola ", "mundo"]


def test_download_modelo_reporta_progresso(monkeypatch):
    linhas = [b'{"status":"pulling","completed":5,"total":10}\n', b'{"status":"success"}\n']
    monkeypatch.setattr(om.urllib.request, "urlopen", lambda *a, **k: Resposta(linhas))
    progresso = MagicMock()
    assert om.baixar_modelo("modelo", progresso)
    assert progresso.call_args_list[0].args == ("pulling", 5, 10)


def test_download_modelo_erro_do_servidor(monkeypatch):
    monkeypatch.setattr(om.urllib.request, "urlopen", lambda *a, **k: Resposta([b'{"error":"falhou"}\n']))
    assert not om.baixar_modelo("modelo")
