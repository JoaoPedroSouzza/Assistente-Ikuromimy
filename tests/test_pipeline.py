import logging
import threading
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMessageBox

import escravo
from core import comandos, execucao
from core.logging_config import configurar_logging
from ui import remote_server, command_history
from ui.pages.home_page import HomePage


def test_interface_continua_responsiva_durante_comando(qtbot, monkeypatch):
    iniciou, liberar = threading.Event(), threading.Event()
    def lento(comando):
        iniciou.set()
        liberar.wait(5)
        return True
    processar = MagicMock(side_effect=lento)
    monkeypatch.setattr(escravo, "processar_comando", processar)
    page = HomePage()
    qtbot.addWidget(page)
    page.comando.setText("play")
    try:
        page.executar_comando()
        qtbot.waitUntil(iniciou.is_set)
        eventos = []
        QTimer.singleShot(0, lambda: eventos.append(True))
        qtbot.waitUntil(lambda: bool(eventos))
        assert page._worker.isRunning()
        page.executar_comando()
        processar.assert_called_once_with("play")
        liberar.set()
        qtbot.waitUntil(lambda: page.btn_executar.isEnabled())
        assert command_history.carregar_historico() == ["play"]
    finally:
        liberar.set()
        assert page._worker.wait(5000)


def test_gateway_nao_intercala_acoes():
    entrou, liberar, terminou = threading.Event(), threading.Event(), threading.Event()
    ordem = []
    def primeira():
        ordem.append(1)
        entrou.set()
        liberar.wait(5)
        ordem.append(2)
    def segunda():
        ordem.append(3)
        terminou.set()
    a = threading.Thread(target=lambda: execucao.executar_acao(primeira))
    b = threading.Thread(target=lambda: execucao.executar_acao(segunda))
    try:
        a.start()
        assert entrou.wait(2)
        b.start()
        assert not terminou.wait(0.05)
    finally:
        liberar.set()
        a.join(5)
        if b.ident:
            b.join(5)
    assert ordem == [1, 2, 3]


def test_gateway_cancelado_nao_executa():
    acao = MagicMock()
    with pytest.raises(execucao.ExecucaoCancelada):
        execucao.executar_acao(acao, cancelado=lambda: True)
    acao.assert_not_called()


@pytest.fixture
def cliente_seguro(monkeypatch):
    monkeypatch.setattr(remote_server, "make_server", MagicMock())
    servidor = remote_server.ServidorRemoto("chave-teste")
    return servidor._app.test_client()


@pytest.mark.parametrize("tamanho,status", [(4097, 400), (20000, 413)])
def test_remoto_limita_entrada(cliente_seguro, monkeypatch, tamanho, status):
    executar = MagicMock()
    monkeypatch.setattr(escravo, "processar_comando", executar)
    r = cliente_seguro.post("/comando", headers={"X-Token": "chave-teste"}, json={"texto": "x" * tamanho})
    assert r.status_code == status
    executar.assert_not_called()


def test_remoto_nao_vaza_detalhe_de_excecao(cliente_seguro, monkeypatch):
    monkeypatch.setattr(escravo, "processar_comando", MagicMock(side_effect=RuntimeError("token=segredo-local")))
    r = cliente_seguro.post("/comando", headers={"X-Token": "chave-teste"}, json={"texto": "play"})
    assert r.status_code == 500
    assert b"segredo-local" not in r.data


def test_remoto_recusa_token_unicode(cliente_seguro):
    assert cliente_seguro.get("/ping", headers={"X-Token": "é"}).status_code == 401


def test_remoto_recusa_token_vazio():
    with pytest.raises(ValueError):
        remote_server.ServidorRemoto("")


@pytest.mark.parametrize("uri", ["file:///C:/Windows/explorer.exe", "shell:AppsFolder", "ms-msdt:/id"])
def test_protocolos_nao_permitidos_nao_abrem(monkeypatch, uri):
    abrir = MagicMock()
    monkeypatch.setattr(escravo.os, "startfile", abrir)
    assert escravo.abrir_link_protocolo(uri) is False
    abrir.assert_not_called()


def test_texto_livre_nao_chega_ao_shell(monkeypatch):
    monkeypatch.setattr(escravo, "encontrar_executavel_generico", lambda _: None)
    monkeypatch.setattr(escravo.shutil, "which", lambda _: None)
    processo = MagicMock()
    monkeypatch.setattr(escravo.subprocess, "Popen", processo)
    escravo.acao_abrir("inexistente & calc")
    processo.assert_not_called()


@pytest.mark.parametrize("aceitar", [False, True])
def test_comando_da_ia_exige_confirmacao(qtbot, monkeypatch, desktop_simulado, aceitar):
    from ui.pages.ai_page import AIPage
    page = AIPage()
    qtbot.addWidget(page)
    executar = MagicMock()
    monkeypatch.setattr(page, "_executar_comando", executar)
    confirmar = MagicMock(return_value=QMessageBox.Yes if aceitar else QMessageBox.No)
    monkeypatch.setattr(QMessageBox, "question", confirmar)
    page._ao_concluir_resposta("<comando>abrir editor</comando>")
    confirmar.assert_called_once()
    if aceitar:
        executar.assert_called_once_with("abrir editor")
    else:
        executar.assert_not_called()


def test_logs_rotativos_redigem_credenciais(tmp_path):
    logger = logging.getLogger("ikuromimy")
    try:
        caminho = configurar_logging(tmp_path)
        configurar_logging(tmp_path)
        assert len(logger.handlers) == 1
        handler = logger.handlers[0]
        assert handler.maxBytes == 1_048_576 and handler.backupCount == 3
        logger.info("auth=segredo-a token=segredo-b Bearer segredo-c")
        handler.flush()
        texto = caminho.read_text(encoding="utf-8")
        assert "segredo-" not in texto
        assert texto.count("[REMOVIDO]") == 3
    finally:
        for handler in list(logger.handlers):
            handler.close()
            logger.removeHandler(handler)
        logger.propagate = True


def test_cache_de_autocorrecao_e_limitado():
    comandos._corrigir_palavra.cache_clear()
    for i in range(400):
        comandos._tentar_corrigir_comando(f"invalido{i} texto")
    assert comandos._corrigir_palavra.cache_info().currsize <= 256


def test_sugestoes_reutilizam_modelo(qtbot):
    page = HomePage()
    qtbot.addWidget(page)
    modelo = page._completer.model()
    for _ in range(10):
        page._atualizar_sugestoes(["play"])
    assert page._completer.model() is modelo


def test_historico_duplicado_nao_regrava(monkeypatch):
    command_history.adicionar_ao_historico("play")
    original = command_history.QSettings
    settings = MagicMock(wraps=original("Ikuromimy", "AssistenteVirtual"))
    monkeypatch.setattr(command_history, "QSettings", lambda *a: settings)
    assert command_history.adicionar_ao_historico("play") == ["play"]
    settings.setValue.assert_not_called()


def test_chat_cancela_stream_ao_encerrar(qtbot, monkeypatch):
    from ui import ollama_manager
    from ui.ai_worker import ChatWorker
    iniciou, liberar = threading.Event(), threading.Event()
    def stream(modelo, mensagens, on_chunk):
        iniciou.set()
        liberar.wait(5)
        on_chunk("trecho")
        return "trecho"
    monkeypatch.setattr(ollama_manager, "enviar_mensagem", stream)
    worker = ChatWorker("teste", [])
    try:
        worker.start()
        qtbot.waitUntil(iniciou.is_set)
        with qtbot.waitSignal(worker.erro, timeout=5000) as resultado:
            worker.requestInterruption()
            liberar.set()
        assert "cancelada" in resultado.args[0]
    finally:
        liberar.set()
        assert worker.wait(5000)


def test_reconhecimento_tem_timeout(monkeypatch):
    import numpy as np
    from ui import voice_input
    reconhecedor = MagicMock()
    reconhecedor.recognize_google.return_value = "play"
    monkeypatch.setattr(voice_input.sr, "Recognizer", lambda: reconhecedor)
    monkeypatch.setattr(voice_input.sd, "rec", lambda *a, **k: np.zeros((8, 1), dtype=np.int16))
    monkeypatch.setattr(voice_input.sd, "wait", lambda: None)
    assert voice_input.gravar_e_transcrever() == "play"
    assert reconhecedor.operation_timeout == 10


def test_self_test_nao_abre_janela(monkeypatch):
    import interface
    monkeypatch.setattr(interface.sys, "argv", ["assistente", "--self-test"])
    janela = MagicMock()
    monkeypatch.setattr(interface, "MainWindow", janela)
    with pytest.raises(SystemExit) as resultado:
        interface.main()
    assert resultado.value.code == 0
    janela.assert_not_called()


@pytest.mark.parametrize("codigo,regra", [
    ("def f(): return inexistente", "NOME"),
    ("eval('2+2')", "EXEC"),
    ("import subprocess\nsubprocess.run('algo', shell=True)", "SHELL"),
    ("import urllib.request\nurllib.request.urlopen('https://teste.invalid', timeout=None)", "TIMEOUT"),
])
def test_analise_estatica_detecta_regressoes(tmp_path, monkeypatch, codigo, regra):
    from scripts import analisar
    monkeypatch.setattr(analisar, "ROOT", tmp_path)
    arquivo = tmp_path / "exemplo.py"
    arquivo.write_text(codigo, encoding="utf-8")
    assert regra in {a["regra"] for a in analisar.analisar(arquivo)}
