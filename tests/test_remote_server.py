from unittest.mock import MagicMock

from ui import remote_server


def criar_servidor_sem_socket(monkeypatch):
    fake = MagicMock(); monkeypatch.setattr(remote_server, "make_server", lambda *a, **k: fake)
    return remote_server.ServidorRemoto("token-ok")


def test_token_tem_128_bits():
    token = remote_server.gerar_token()
    assert len(token) == 32 and all(c in "0123456789abcdef" for c in token)


def test_ping_exige_token(monkeypatch):
    servidor = criar_servidor_sem_socket(monkeypatch); cliente = servidor._app.test_client()
    assert cliente.get("/ping").status_code == 401
    assert cliente.get("/ping", headers={"X-Token":"errado"}).status_code == 401
    assert cliente.get("/ping", headers={"X-Token":"token-ok"}).status_code == 200


def test_comando_valida_corpo(monkeypatch):
    servidor = criar_servidor_sem_socket(monkeypatch); cliente = servidor._app.test_client()
    h = {"X-Token":"token-ok"}
    assert cliente.post("/comando", headers=h, json={}).status_code == 400
    assert cliente.post("/comando", headers=h, data="não-json").status_code == 400


def test_comando_despacha(monkeypatch):
    processar = MagicMock(); monkeypatch.setattr(remote_server.escravo, "processar_comando", processar)
    servidor = criar_servidor_sem_socket(monkeypatch); cliente = servidor._app.test_client()
    r = cliente.post("/comando", headers={"X-Token":"token-ok"}, json={"texto":" play "})
    assert r.status_code == 200
    processar.assert_called_once_with("play")


def test_acao_de_midia_permitida_e_desconhecida(monkeypatch):
    play = MagicMock(); monkeypatch.setattr(remote_server.escravo, "media_play_pause", play)
    servidor = criar_servidor_sem_socket(monkeypatch); cliente = servidor._app.test_client(); h={"X-Token":"token-ok"}
    assert cliente.post("/midia/play_pause", headers=h).status_code == 200
    play.assert_called_once()
    assert cliente.post("/midia/apagar", headers=h).status_code == 400


def test_sistema_retorna_resumo(monkeypatch):
    monkeypatch.setattr(remote_server.system_info, "obter_resumo_sistema", lambda: {"cpu":"Teste"})
    servidor = criar_servidor_sem_socket(monkeypatch); cliente = servidor._app.test_client()
    assert cliente.get("/sistema", headers={"X-Token":"token-ok"}).json == {"cpu":"Teste"}


def test_parar_desliga_servidor(monkeypatch):
    servidor = criar_servidor_sem_socket(monkeypatch)
    servidor.parar()
    servidor._server.server_close.assert_called_once()
