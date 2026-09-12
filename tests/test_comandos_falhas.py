from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import escravo


@pytest.mark.parametrize("funcao,pergunta", [("acao_abrir", "Abrir o quê?"), ("acao_fechar", "Fechar o quê?"), ("acao_pesquisar", "Pesquisar o quê?")])
def test_alvo_vazio_pede_complemento(monkeypatch, funcao, pergunta):
    falar = MagicMock()
    monkeypatch.setattr(escravo, "falar", falar)
    getattr(escravo, funcao)("")
    falar.assert_called_once_with(pergunta)


def test_app_inexistente_fallback_falho_informa_usuario(monkeypatch):
    monkeypatch.setattr(escravo, "encontrar_executavel_generico", lambda app: None)
    monkeypatch.setattr(escravo.subprocess, "Popen", MagicMock(side_effect=OSError("inexistente")))
    falar = MagicMock()
    monkeypatch.setattr(escravo, "falar", falar)
    escravo.processar_comando("abrir inexistente_xyz")
    assert "Não encontrei" in falar.call_args.args[0]


@pytest.mark.parametrize("falha", [False, True])
def test_abrir_app_indexado(monkeypatch, tmp_path, falha):
    exe = tmp_path / "editor.exe"
    exe.write_bytes(b"arquivo de teste, nao executavel")
    monkeypatch.setattr(escravo, "_CACHE_CARREGADO", True)
    monkeypatch.setattr(escravo, "_CACHE_APPS", {"editor": exe})
    abrir = MagicMock(side_effect=OSError("bloqueado") if falha else None)
    falar = MagicMock()
    monkeypatch.setattr(escravo.os, "startfile", abrir)
    monkeypatch.setattr(escravo, "falar", falar)
    escravo.processar_comando("abrir editor")
    abrir.assert_called_once_with(str(exe))
    assert ("Deu erro" in falar.call_args.args[0]) == falha


@pytest.mark.parametrize("encontrado", [False, True])
def test_fechar_app_retorna_mensagem_coerente(monkeypatch, encontrado):
    fechar = MagicMock(return_value=encontrado)
    falar = MagicMock()
    monkeypatch.setattr(escravo, "fechar_processo", fechar)
    monkeypatch.setattr(escravo, "falar", falar)
    escravo.processar_comando("fechar editor.exe")
    fechar.assert_called_once_with("editor.exe")
    assert ("Fechando" if encontrado else "não parece estar aberto") in falar.call_args.args[0]


def test_fechar_desconhecido_nao_procura_processos(monkeypatch):
    fechar = MagicMock()
    monkeypatch.setattr(escravo, "fechar_processo", fechar)
    escravo.processar_comando("fechar xyz_inexistente")
    fechar.assert_not_called()


def test_atualizar_apps_descarta_cache_antigo(monkeypatch, tmp_path):
    monkeypatch.setattr(escravo, "_CACHE_CARREGADO", True)
    monkeypatch.setattr(escravo, "_CACHE_APPS", {"velho": tmp_path / "velho.exe"})
    construir = MagicMock(return_value={"novo": tmp_path / "novo.exe"})
    monkeypatch.setattr(escravo, "_construir_indice_apps", construir)
    escravo.processar_comando("atualizar apps")
    assert escravo.listar_apps_conhecidos() == ["novo"]
    construir.assert_called_once()


def test_busca_parcial_prefere_nome_mais_curto(monkeypatch, tmp_path):
    monkeypatch.setattr(escravo, "_CACHE_CARREGADO", True)
    monkeypatch.setattr(escravo, "_CACHE_APPS", {"editor profissional": tmp_path / "pro.exe", "editor": tmp_path / "simples.exe"})
    assert escravo.encontrar_executavel_generico("edi") == tmp_path / "simples.exe"
    assert escravo.encontrar_executavel_generico("") is None


def test_indice_de_atalhos_ignora_alvos_invalidos(monkeypatch, tmp_path):
    exe = tmp_path / "editor.exe"
    exe.write_bytes(b"simulado")
    for nome in ("editor", "quebrado", "documento"):
        (tmp_path / f"{nome}.lnk").write_bytes(b"simulado")
    shell = MagicMock()
    def atalho(caminho):
        nome = Path(caminho).stem
        if nome == "quebrado":
            raise OSError("atalho corrompido")
        return SimpleNamespace(Targetpath=str(exe) if nome == "editor" else "documento.txt")
    shell.CreateShortcut.side_effect = atalho
    client = MagicMock()
    client.Dispatch.return_value = shell
    monkeypatch.setattr(escravo, "win32com", SimpleNamespace(client=client), raising=False)
    monkeypatch.setattr(escravo, "PYWIN32_DISPONIVEL", True)
    indice = {}
    escravo._indexar_atalhos(tmp_path, indice)
    assert indice == {"editor": exe}


@pytest.mark.parametrize("termo,url", [("no youtube gatos", "youtube.com/results?search_query=gatos"), ("no bing gatos", "bing.com/search?q=gatos"), ("na duck duck go gatos", "duckduckgo.com/?q=gatos")])
def test_comando_de_pesquisa_seleciona_motor(monkeypatch, termo, url):
    abrir = MagicMock()
    monkeypatch.setattr(escravo.webbrowser, "open", abrir)
    escravo.processar_comando("pesquisar " + termo)
    assert url in abrir.call_args.args[0]


@pytest.mark.parametrize("funcao", ["media_play_pause", "media_next", "media_prev"])
def test_falha_tecla_midia_nao_derruba_assistente(monkeypatch, capsys, funcao):
    monkeypatch.setattr(escravo.pyautogui, "press", MagicMock(side_effect=OSError("falha simulada")))
    getattr(escravo, funcao)()
    assert "falha simulada" in capsys.readouterr().out


def test_spotify_sem_foco_nao_digita(monkeypatch):
    monkeypatch.setattr(escravo, "focar_janela_spotify", lambda: False)
    teclado = MagicMock()
    monkeypatch.setattr(escravo.pyautogui, "hotkey", teclado)
    escravo.buscar_no_app_spotify("minha musica")
    teclado.assert_not_called()


def test_fala_limpa_audio_temporario_apos_falha(monkeypatch, tmp_path):
    monkeypatch.setattr(escravo, "VOZ_ATIVA", True)
    tts = MagicMock()
    tts.save.side_effect = lambda path: Path(path).write_bytes(b"audio-simulado")
    monkeypatch.setattr(escravo, "gTTS", MagicMock(return_value=tts))
    monkeypatch.setattr(escravo, "playsound", MagicMock(side_effect=OSError("sem player")))
    escravo.falar("teste")
    assert list(tmp_path.glob("*.mp3")) == []
