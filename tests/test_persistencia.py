import json

from ui import assistant_name, command_history, modes_manager, remote_config, shortcuts_manager


def test_nome_padrao_e_salvar():
    assert assistant_name.carregar_nome() == "Assistente"
    assert assistant_name.salvar_nome("  Ikuro  ") == "Ikuro"
    assert assistant_name.carregar_nome() == "Ikuro"
    assert assistant_name.salvar_nome("   ") == "Assistente"


def test_historico_ordena_remove_duplicata_e_limita():
    command_history.adicionar_ao_historico(" abrir chrome ")
    command_history.adicionar_ao_historico("abrir spotify")
    command_history.adicionar_ao_historico("abrir chrome")
    assert command_history.carregar_historico() == ["abrir chrome", "abrir spotify"]
    for i in range(60): command_history.adicionar_ao_historico(f"cmd {i}")
    assert len(command_history.carregar_historico()) == 50


def test_historico_corrompido_retorna_vazio():
    command_history.QSettings("Ikuromimy", "AssistenteVirtual").setValue("comandos/historico", "{")
    assert command_history.carregar_historico() == []


def test_crud_modos_e_limite():
    modes_manager.adicionar_modo("  Estudo  ", [" abrir chrome ", "", "play", "a", "b", "c", "ignorado"])
    modos = modes_manager.listar_modos()
    assert len(modos) == 1 and len(modos[0]["comandos"]) == 5
    ident = modos[0]["id"]
    modes_manager.editar_modo(ident, "Foco", ["fechar chrome"])
    assert modes_manager.listar_modos()[0]["nome"] == "Foco"
    modes_manager.remover_modo(ident)
    assert modes_manager.listar_modos() == []


def test_modo_invalido_nao_salva():
    modes_manager.adicionar_modo("", ["play"])
    modes_manager.adicionar_modo("nome", [])
    assert modes_manager.listar_modos() == []


def test_modos_legados_ganham_id():
    s = modes_manager.QSettings("Ikuromimy", "AssistenteVirtual")
    s.setValue("modos/personalizados", json.dumps([{"nome": "x", "comandos": ["play"]}]))
    assert len(modes_manager.listar_modos()[0]["id"]) == 32


def test_crud_atalhos():
    iniciais = shortcuts_manager.listar_atalhos()
    assert len(iniciais) == 5
    shortcuts_manager.adicionar_atalho("  Notas  ", " abrir bloco ")
    novo = shortcuts_manager.listar_atalhos()[-1]
    assert novo["label"] == "Notas"
    shortcuts_manager.editar_atalho(novo["id"], "Bloco", "abrir notas")
    assert shortcuts_manager.listar_atalhos()[-1]["label"] == "Bloco"
    shortcuts_manager.remover_atalho(novo["id"])
    assert len(shortcuts_manager.listar_atalhos()) == 5


def test_atalho_invalido_nao_salva():
    antes = shortcuts_manager.listar_atalhos()
    shortcuts_manager.adicionar_atalho("", "play")
    shortcuts_manager.adicionar_atalho("Play", "")
    assert shortcuts_manager.listar_atalhos() == antes


def test_token_gerado_uma_vez(monkeypatch):
    monkeypatch.setattr(remote_config, "gerar_token", lambda: "1234abcd")
    assert remote_config.carregar_token() == "1234abcd"
    monkeypatch.setattr(remote_config, "gerar_token", lambda: "outro")
    assert remote_config.carregar_token() == "1234abcd"

