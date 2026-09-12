import io
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from ui import updater, ollama_manager


class Resposta(io.BytesIO):
    def __init__(self, dados, total=None):
        super().__init__(dados)
        self.headers = {} if total is None else {"Content-Length": str(total)}


def test_download_atualizacao_salva_bytes_e_progresso(monkeypatch, tmp_path):
    dados = b"MZ" + b"x" * 1_000_000
    rede = MagicMock(return_value=Resposta(dados, len(dados)))
    monkeypatch.setattr(updater.urllib.request, "urlopen", rede)
    progresso = MagicMock()
    caminho = updater.baixar_atualizacao("https://example.invalid/app.exe", progresso)
    assert Path(caminho).parent == tmp_path
    assert Path(caminho).read_bytes() == dados
    assert progresso.call_args.args == (len(dados), len(dados))
    rede.assert_called_once()


def test_download_incompleto_tenta_novamente(monkeypatch):
    dados = b"x" * 1_000_001
    rede = MagicMock(side_effect=[Resposta(b"curto", len(dados)), Resposta(dados, len(dados))])
    monkeypatch.setattr(updater.urllib.request, "urlopen", rede)
    caminho = updater.baixar_atualizacao("https://example.invalid/app.exe")
    assert Path(caminho).read_bytes() == dados
    assert rede.call_count == 2


@pytest.mark.parametrize("falha", ["rede", "tamanho", "sem_cabecalho"])
def test_download_esgota_tentativas_e_remove_arquivo(monkeypatch, tmp_path, falha):
    def resposta(*args, **kwargs):
        if falha == "rede":
            raise OSError("offline")
        return Resposta(b"curto", 2_000_000 if falha == "tamanho" else None)
    rede = MagicMock(side_effect=resposta)
    monkeypatch.setattr(updater.urllib.request, "urlopen", rede)
    assert updater.baixar_atualizacao("https://example.invalid/app.exe", tentativas=2) is None
    assert rede.call_count == 2
    assert not (tmp_path / "AssistenteIkuromimy_novo.exe").exists()


def test_download_instalador_ollama_termina_no_fim_do_stream(monkeypatch, tmp_path):
    dados = b"instalador simulado"
    monkeypatch.setattr(ollama_manager.urllib.request, "urlopen", lambda *a, **k: Resposta(dados, len(dados)))
    progresso = MagicMock()
    caminho = ollama_manager.baixar_instalador(progresso)
    assert Path(caminho).parent == tmp_path
    assert Path(caminho).read_bytes() == dados
    progresso.assert_called_once_with(len(dados), len(dados))
