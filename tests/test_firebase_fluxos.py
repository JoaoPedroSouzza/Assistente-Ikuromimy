import io
import json
import urllib.error
from unittest.mock import MagicMock

import pytest
from ui import firebase_client as fb
from ui.friends_worker import ListaAmigosWorker, MensagensWorker


@pytest.fixture
def configuracao(monkeypatch):
    monkeypatch.setattr(fb, "FIREBASE_CONFIG", {"apiKey": "chave-teste", "databaseURL": "https://teste.invalid/"})
    monkeypatch.setattr(fb.time, "time", lambda: 1000)


@pytest.fixture
def sessao(configuracao):
    dados = {"localId": "eu", "idToken": "token-teste", "refreshToken": "r", "expiraEm": 5000}
    fb.salvar_sessao(dados)
    return dados


def test_login_http_ate_persistencia(configuracao, monkeypatch):
    rede = MagicMock(return_value=io.BytesIO(json.dumps({
        "idToken": "novo", "refreshToken": "r", "localId": "eu", "expiresIn": "3600",
    }).encode()))
    monkeypatch.setattr(fb.urllib.request, "urlopen", rede)
    resultado = fb.entrar("teste@example.invalid", "senha-simulada")
    req = rede.call_args.args[0]
    assert req.method == "POST"
    assert "accounts:signInWithPassword" in req.full_url
    assert json.loads(req.data) == {"email": "teste@example.invalid", "password": "senha-simulada", "returnSecureToken": True}
    assert fb.carregar_sessao() == resultado
    assert resultado["expiraEm"] == 4540
    fb.sair()
    assert fb.carregar_sessao() is None


@pytest.mark.parametrize("codigo,trecho", [("INVALID_LOGIN_CREDENTIALS", "incorretos"), ("EMAIL_EXISTS", "já tem"), ("TOO_MANY_ATTEMPTS_TRY_LATER", "Muitas tentativas")])
def test_erro_http_autenticacao_nao_salva_sessao(configuracao, monkeypatch, codigo, trecho):
    erro = urllib.error.HTTPError("https://teste.invalid", 400, "erro", {},
                                 io.BytesIO(json.dumps({"error": {"message": codigo}}).encode()))
    monkeypatch.setattr(fb.urllib.request, "urlopen", MagicMock(side_effect=erro))
    with pytest.raises(RuntimeError, match=trecho):
        fb.entrar("teste@example.invalid", "senha-simulada")
    assert fb.carregar_sessao() is None


def test_cadastro_salva_perfil_e_indice(configuracao, monkeypatch):
    buscar = MagicMock(return_value=None)
    monkeypatch.setattr(fb, "buscar_uid_por_nome_usuario", buscar)
    monkeypatch.setattr(fb, "_post", MagicMock(return_value={"idToken": "t", "refreshToken": "r", "localId": "eu", "expiresIn": "3600"}))
    escrever = MagicMock()
    monkeypatch.setattr(fb, "_escrever", escrever)
    resultado = fb.cadastrar("teste@example.invalid", "senha-simulada", "  Ikuro  ")
    buscar.assert_called_once_with("Ikuro")
    assert resultado == fb.carregar_sessao()
    assert escrever.call_args_list[0].args == ("/perfis/eu.json", {"nome_usuario": "Ikuro", "email": "teste@example.invalid"}, "t")
    assert escrever.call_args_list[1].args == ("/nomes_usuario/ikuro.json", "eu", "t")


def test_cadastro_nome_ocupado_nao_cria_conta(configuracao, monkeypatch):
    monkeypatch.setattr(fb, "buscar_uid_por_nome_usuario", lambda nome: "outro")
    post = MagicMock()
    monkeypatch.setattr(fb, "_post", post)
    with pytest.raises(RuntimeError, match="já está em uso"):
        fb.cadastrar("teste@example.invalid", "senha-simulada", "Ikuro")
    post.assert_not_called()


@pytest.mark.parametrize("uid,erro", [(None, "Não achei"), ("eu", "si mesmo")])
def test_pedido_invalido_nao_escreve(sessao, monkeypatch, uid, erro):
    monkeypatch.setattr(fb, "buscar_uid_por_nome_usuario", lambda nome: uid)
    escrever = MagicMock()
    monkeypatch.setattr(fb, "_escrever", escrever)
    with pytest.raises(RuntimeError, match=erro):
        fb.enviar_pedido_amizade("Amigo")
    escrever.assert_not_called()


def test_pedido_grava_os_dois_lados_atomicamente(sessao, monkeypatch):
    monkeypatch.setattr(fb, "buscar_uid_por_nome_usuario", lambda nome: "amigo")
    escrever = MagicMock()
    monkeypatch.setattr(fb, "_escrever", escrever)
    assert fb.enviar_pedido_amizade("Amigo") == "amigo"
    escrever.assert_called_once_with("/.json", {"amizades/eu/amigo": "pendente_enviado", "amizades/amigo/eu": "pendente_recebido"}, "token-teste", metodo="PATCH")


@pytest.mark.parametrize("funcao,estado", [("aceitar_pedido", "aceito"), ("recusar_pedido", None)])
def test_resposta_ao_pedido_atualiza_ambos(sessao, monkeypatch, funcao, estado):
    escrever = MagicMock()
    monkeypatch.setattr(fb, "_escrever", escrever)
    getattr(fb, funcao)("amigo")
    escrever.assert_called_once_with("/.json", {"amizades/eu/amigo": estado, "amizades/amigo/eu": estado}, "token-teste", metodo="PATCH")


@pytest.mark.parametrize("funcao", ["aceitar_pedido", "recusar_pedido", "enviar_pedido_amizade"])
def test_amizades_exigem_sessao(funcao):
    with pytest.raises(RuntimeError, match="logado"):
        getattr(fb, funcao)("amigo")


def test_mensagem_http_usa_destinatario_e_texto_limpo(sessao, monkeypatch):
    rede = MagicMock(return_value=io.BytesIO(b'{}'))
    monkeypatch.setattr(fb.urllib.request, "urlopen", rede)
    fb.enviar_mensagem_amigo("amigo", "  Olá  ")
    req = rede.call_args.args[0]
    assert req.method == "POST"
    assert "/mensagens/amigo_eu.json?auth=token-teste" in req.full_url
    assert json.loads(req.data) == {"remetente": "eu", "texto": "Olá", "timestamp": 1000}


def test_mensagem_vazia_nao_acessa_rede():
    fb.enviar_mensagem_amigo("amigo", "   ")


def test_mensagens_vem_em_ordem_cronologica(sessao, monkeypatch):
    monkeypatch.setattr(fb, "_ler", lambda *a: {"b": {"texto": "depois", "timestamp": 20}, "a": {"texto": "antes", "timestamp": 10}})
    assert [m["texto"] for m in fb.buscar_mensagens("amigo")] == ["antes", "depois"]


@pytest.mark.parametrize("corpo,esperado", [(b"null", None), (b"", None), (b'{"nome":"Ikuro"}', {"nome": "Ikuro"})])
def test_leitura_database(configuracao, monkeypatch, corpo, esperado):
    monkeypatch.setattr(fb.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(corpo))
    assert fb._ler("/perfis/eu.json", "token") == esperado


def test_leitura_database_json_invalido(configuracao, monkeypatch):
    monkeypatch.setattr(fb.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(b"pagina html"))
    with pytest.raises(RuntimeError, match="Resposta inesperada"):
        fb._ler("/perfis/eu.json", "token")


def test_lista_worker_presenca_expirada(qtbot, sessao, monkeypatch):
    monkeypatch.setattr(fb, "listar_amizades", lambda: ({"antigo": "aceito", "atual": "aceito", "removido": None}, sessao))
    monkeypatch.setattr(fb, "obter_perfil", lambda uid, s: {"nome_usuario": uid})
    monkeypatch.setattr(fb, "obter_presenca", lambda uid, s: {"online": True, "atualizado_em": 900 if uid == "antigo" else 999})
    worker = ListaAmigosWorker()
    try:
        with qtbot.waitSignal(worker.concluido, timeout=5000) as resultado:
            worker.start()
        assert [(a["uid"], a["online"]) for a in resultado.args[0]] == [("antigo", False), ("atual", True)]
    finally:
        assert worker.wait(5000)


def test_worker_mensagens_emite_erro(qtbot, monkeypatch):
    monkeypatch.setattr(fb, "buscar_mensagens", MagicMock(side_effect=OSError("offline")))
    worker = MensagensWorker("amigo")
    try:
        with qtbot.waitSignal(worker.erro, timeout=5000) as resultado:
            worker.start()
        assert resultado.args == ["offline"]
    finally:
        assert worker.wait(5000)
