from pathlib import Path
from unittest.mock import MagicMock

import pytest
import escravo


@pytest.mark.parametrize("texto,palavras,esperado", [
    ("abrir chrome", ("abrir",), True),
    ("parabéns", ("para",), False),
    ("voltar para casa", ("voltar",), True),
    ("ABRIR chrome", ("abrir",), False),
])
def test_contem_palavra(texto, palavras, esperado):
    assert escravo.contem_palavra(texto, *palavras) is esperado


def test_extrair_alvo_remove_gatilhos_inteiros():
    assert escravo.extrair_alvo("por favor abrir chrome", "abrir") == "por favor  chrome"


@pytest.mark.parametrize("entrada,saida", [
    ("abrri chrome", "abrir chrome"),
    ("pesqusiar gatos", "pesquisar gatos"),
    ("abracadabra", None),
    ("abrir chrome", None),
    ("", None),
])
def test_autocorrecao(entrada, saida):
    assert escravo._tentar_corrigir_comando(entrada) == saida


@pytest.mark.parametrize("comando", [
    "abrir chrome", "fechar chrome", "tocar 505", "pesquisar pytest",
    "play", "próxima", "aumentar volume", "repetir", "sair", "abrri chrome",
])
def test_comandos_conhecidos(comando):
    assert escravo.eh_comando_conhecido(comando)


@pytest.mark.parametrize("comando", ["", "banana", "parabéns", "uma conversa normal"])
def test_comandos_desconhecidos(comando):
    assert not escravo.eh_comando_conhecido(comando)


def test_processar_tocar(monkeypatch):
    acao = MagicMock(); monkeypatch.setattr(escravo, "acao_tocar_musica", acao)
    assert escravo.processar_comando("  TOCAR 505 ") is True
    acao.assert_called_once_with("505")


@pytest.mark.parametrize("verbo", ["pesquisar", "pesquisa", "buscar"])
def test_processar_pesquisa(verbo, monkeypatch):
    acao = MagicMock(); monkeypatch.setattr(escravo, "acao_pesquisar", acao)
    assert escravo.processar_comando(f"{verbo} testes python") is True
    acao.assert_called_once_with("testes python")


@pytest.mark.parametrize("comando,funcao", [
    ("abrir chrome", "acao_abrir"), ("fechar spotify", "acao_fechar"),
    ("play", "media_play_pause"), ("próxima", "media_next"), ("anterior", "media_prev"),
])
def test_despacho_de_comandos(comando, funcao, monkeypatch):
    alvo = MagicMock(); monkeypatch.setattr(escravo, funcao, alvo)
    monkeypatch.setattr(escravo, "falar", MagicMock())
    assert escravo.processar_comando(comando) is True
    alvo.assert_called_once()


def test_sair_retorna_false(monkeypatch):
    monkeypatch.setattr(escravo, "falar", MagicMock())
    assert escravo.processar_comando("sair") is False


def test_vazio_nao_executa(monkeypatch):
    falar = MagicMock(); monkeypatch.setattr(escravo, "falar", falar)
    assert escravo.processar_comando("   ") is True
    falar.assert_not_called()


def test_corrige_e_despacha(monkeypatch):
    abrir = MagicMock(); monkeypatch.setattr(escravo, "acao_abrir", abrir)
    monkeypatch.setattr(escravo, "falar", MagicMock())
    assert escravo.processar_comando("abrri chrome") is True
    abrir.assert_called_once_with("chrome")


def test_cache_reconstroi_uma_vez(monkeypatch):
    monkeypatch.setattr(escravo, "_CACHE_CARREGADO", False)
    monkeypatch.setattr(escravo, "_CACHE_APPS", {})
    construir = MagicMock(return_value={"chrome": Path("chrome.exe")})
    monkeypatch.setattr(escravo, "_construir_indice_apps", construir)
    assert "chrome" in escravo._carregar_cache_apps()
    escravo._carregar_cache_apps()
    construir.assert_called_once()


def test_busca_executavel_exata_e_parcial(monkeypatch):
    indice = {"google chrome": Path("C:/Chrome.exe"), "spotify": Path("C:/Spotify.exe")}
    monkeypatch.setattr(escravo, "_carregar_cache_apps", lambda: indice)
    assert escravo.encontrar_executavel_generico("spotify") == Path("C:/Spotify.exe")
    assert escravo.encontrar_executavel_generico("chrome") == Path("C:/Chrome.exe")
    assert escravo.encontrar_executavel_generico("inexistente") is None


@pytest.mark.parametrize("nome,esperado", [
    ("cs2", "steam://rungameid/730"),
    ("counter strike", "steam://rungameid/730"),
    ("desconhecido", None),
])
def test_resolver_link_de_jogo(nome, esperado):
    assert escravo.resolver_link_de_jogo(nome) == esperado


def test_fechar_processo_ignora_erros(monkeypatch):
    ok = MagicMock(); ok.info = {"name": "Chrome.exe"}
    negado = MagicMock(); negado.info.__getitem__.side_effect = escravo.psutil.AccessDenied()
    monkeypatch.setattr(escravo.psutil, "process_iter", lambda attrs: [ok, negado])
    assert escravo.fechar_processo("chrome.exe") is True
    ok.terminate.assert_called_once()


def test_busca_google_codifica_termo(monkeypatch):
    abrir = MagicMock(return_value=True); monkeypatch.setattr(escravo.webbrowser, "open", abrir)
    monkeypatch.setattr(escravo, "falar", MagicMock())
    escravo.acao_pesquisar("café com leite", "google")
    assert "caf%C3%A9+com+leite" in abrir.call_args.args[0]

