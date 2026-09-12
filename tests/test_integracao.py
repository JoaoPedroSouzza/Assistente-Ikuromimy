from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QSettings

import escravo
from ui import assistant_name, command_history, modes_manager, remote_server

pytestmark = pytest.mark.integration


@pytest.fixture
def cliente(monkeypatch):
    monkeypatch.setattr(remote_server, "make_server", MagicMock())
    servidor = remote_server.ServidorRemoto("segredo")
    servidor._app.config["TESTING"] = True
    yield servidor._app.test_client()


@pytest.mark.parametrize("texto,tecla", [
    ("  PLAY  ", "playpause"), ("próxima", "nexttrack"),
    ("anterior", "prevtrack"), ("aumentar volume", "volumeup"),
])
def test_http_interpreta_comando_e_chega_ao_teclado(cliente, monkeypatch, texto, tecla):
    teclado = MagicMock()
    monkeypatch.setattr(escravo.pyautogui, "press", teclado)
    resposta = cliente.post("/comando", headers={"X-Token": "segredo"}, json={"texto": texto})
    assert resposta.status_code == 200
    assert resposta.json == {"ok": True}
    teclado.assert_called_once_with(tecla)


@pytest.mark.parametrize("corpo", [None, [], [1], 123, True, "play", {},
    {"texto": 123}, {"texto": True}, {"texto": []}, {"texto": {}},
    {"texto": None}, {"texto": "   "}])
def test_http_rejeita_tipos_invalidos_sem_executar(cliente, monkeypatch, corpo):
    import json
    executar = MagicMock()
    monkeypatch.setattr(escravo, "processar_comando", executar)
    resposta = cliente.post("/comando", headers={"X-Token": "segredo"},
                            data=json.dumps(corpo), content_type="application/json")
    assert resposta.status_code == 400
    assert "erro" in resposta.json
    executar.assert_not_called()


@pytest.mark.parametrize("metodo,rota", [
    ("GET", "/ping"), ("GET", "/sistema"),
    ("POST", "/comando"), ("POST", "/midia/play_pause"),
])
@pytest.mark.parametrize("token", [None, "incorreto"])
def test_todas_as_rotas_barram_acesso(cliente, monkeypatch, metodo, rota, token):
    executar = MagicMock()
    teclado = MagicMock()
    resumo = MagicMock()
    monkeypatch.setattr(escravo, "processar_comando", executar)
    monkeypatch.setattr(escravo.pyautogui, "press", teclado)
    monkeypatch.setattr(remote_server.system_info, "obter_resumo_sistema", resumo)
    headers = {} if token is None else {"X-Token": token}
    assert cliente.open(rota, method=metodo, headers=headers,
                        json={"texto": "play"}).status_code == 401
    executar.assert_not_called()
    teclado.assert_not_called()
    resumo.assert_not_called()


def test_erro_de_execucao_vira_resposta_http(cliente, monkeypatch):
    monkeypatch.setattr(escravo, "processar_comando", MagicMock(side_effect=RuntimeError("falhou")))
    resposta = cliente.post("/comando", headers={"X-Token": "segredo"}, json={"texto": "play"})
    assert resposta.status_code == 500
    assert resposta.json == {"erro": "não foi possível executar o comando"}


def test_persistencia_usa_arquivo_real_temporario(tmp_path):
    assistant_name.salvar_nome("Ikuro")
    command_history.adicionar_ao_historico("play")
    settings = QSettings("Ikuromimy", "AssistenteVirtual")
    settings.sync()
    caminho = Path(settings.fileName()).resolve()
    assert caminho.is_relative_to(tmp_path.resolve())
    assert caminho.is_file()
    assert settings.status() == QSettings.NoError
    leitura = QSettings(str(caminho), QSettings.IniFormat)
    assert leitura.value("assistente/nome") == "Ikuro"
    assert leitura.value("comandos/historico") == '["play"]'


def test_modo_legado_mantem_id_e_pode_ser_editado():
    settings = QSettings("Ikuromimy", "AssistenteVirtual")
    settings.setValue("modos/personalizados", '[{"nome":"Antigo","comandos":["play"]}]')
    ident = modes_manager.listar_modos()[0]["id"]
    assert modes_manager.listar_modos()[0]["id"] == ident
    modes_manager.editar_modo(ident, "Novo", ["próxima"])
    assert modes_manager.listar_modos() == [{"id": ident, "nome": "Novo", "comandos": ["próxima"]}]
    modes_manager.remover_modo(ident)
    assert modes_manager.listar_modos() == []
