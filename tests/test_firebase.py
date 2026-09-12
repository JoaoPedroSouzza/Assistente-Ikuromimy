from unittest.mock import MagicMock

import pytest
from ui import firebase_client as fb


@pytest.mark.parametrize("codigo,texto", [
    ("EMAIL_EXISTS", "já tem"), ("INVALID_PASSWORD", "incorreta"),
    ("INVALID_EMAIL", "inválido"), ("ERRO_NOVO", "ERRO_NOVO"),
])
def test_traduzir_erros(codigo, texto):
    assert texto in fb._traduzir_erro(codigo)


def test_sessao_salvar_carregar_sair():
    sessao = {"idToken":"x", "expiraEm":99999999999}
    fb.salvar_sessao(sessao)
    assert fb.carregar_sessao() == sessao
    fb.sair()
    assert fb.carregar_sessao() is None


def test_sessao_valida_nao_expirada(monkeypatch):
    sessao = {"idToken":"x", "expiraEm":99999999999}
    monkeypatch.setattr(fb, "carregar_sessao", lambda: sessao)
    renovar = MagicMock(); monkeypatch.setattr(fb, "_renovar_token", renovar)
    assert fb.sessao_valida() is sessao
    renovar.assert_not_called()


def test_sessao_expirada_renova(monkeypatch):
    velha = {"refreshToken":"r", "expiraEm":0}; nova = {"idToken":"novo"}
    monkeypatch.setattr(fb, "carregar_sessao", lambda: velha)
    monkeypatch.setattr(fb, "_renovar_token", lambda s: nova)
    assert fb.sessao_valida() == nova


def test_cadastro_exige_usuario(monkeypatch):
    with pytest.raises(RuntimeError, match="nome de usuário"):
        fb.cadastrar("a@b.com", "123456", "   ")


def test_id_conversa_e_estavel():
    assert fb._id_conversa("uid-b", "uid-a") == fb._id_conversa("uid-a", "uid-b")



def test_renovacao_falha_retorna_sem_sessao(monkeypatch):
    fb.salvar_sessao({"idToken": "velho", "refreshToken": "r", "expiraEm": 0})
    monkeypatch.setattr(fb, "_renovar_token", MagicMock(side_effect=OSError("offline")))
    assert fb.sessao_valida() is None


def test_renovacao_real_atualiza_persistencia(monkeypatch):
    monkeypatch.setattr(fb, "FIREBASE_CONFIG", {"apiKey": "teste"})
    monkeypatch.setattr(fb.time, "time", lambda: 1000)
    post = MagicMock(return_value={"id_token": "novo", "refresh_token": "r2",
                                  "user_id": "uid", "expires_in": "3600"})
    monkeypatch.setattr(fb, "_post", post)
    fb.salvar_sessao({"idToken": "velho", "refreshToken": "r1", "expiraEm": 0})
    sessao = fb.sessao_valida()
    assert sessao == {"idToken": "novo", "refreshToken": "r2", "localId": "uid", "expiraEm": 4540}
    assert fb.carregar_sessao() == sessao
    assert post.call_args.args[1] == {"grant_type": "refresh_token", "refresh_token": "r1"}


def test_sessao_json_corrompido():
    fb.QSettings("Ikuromimy", "AssistenteVirtual").setValue("firebase/sessao", "{")
    assert fb.carregar_sessao() is None
