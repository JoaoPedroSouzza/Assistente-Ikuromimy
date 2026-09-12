import threading
from unittest.mock import MagicMock, call

import pytest
from PySide6.QtCore import Qt, QTimer, QThread, QPoint
from PySide6.QtWidgets import QApplication, QPushButton, QDialogButtonBox, QMenu

import escravo
from ui import command_history, modes_manager, modes_executor, ollama_manager, theme_manager
from ui.pages.home_page import HomePage
from ui.pages.modes_page import ModesPage
from ui.modes_dialog import CriarModoDialog

pytestmark = pytest.mark.integration


def botao(widget, texto):
    return next(b for b in widget.findChildren(QPushButton) if b.text() == texto)


@pytest.mark.parametrize("entrada", ["botao", "enter"])
def test_inicio_comando_acao_historico_e_sugestao(qtbot, monkeypatch, entrada):
    page = HomePage()
    qtbot.addWidget(page)
    keyboard = MagicMock()
    monkeypatch.setattr(escravo.pyautogui, "press", keyboard)
    page.comando.setText("play")
    if entrada == "botao":
        qtbot.mouseClick(botao(page, "▶ Executar"), Qt.LeftButton)
    else:
        qtbot.keyClick(page.comando, Qt.Key_Return)
    qtbot.waitUntil(lambda: page.btn_executar.isEnabled() and not page._worker.isRunning(), timeout=5000)
    keyboard.assert_called_once_with("playpause")
    assert command_history.carregar_historico() == ["play"]
    assert page._completer.model().stringList()[0] == "play"
    assert "Comando executado" in page.log.toPlainText()


def test_inicio_erro_visivel_sem_registrar_sucesso(qtbot, monkeypatch):
    page = HomePage()
    qtbot.addWidget(page)
    monkeypatch.setattr(escravo, "processar_comando", MagicMock(side_effect=OSError("app ausente")))
    page.comando.setText("abrir editor")
    qtbot.mouseClick(botao(page, "▶ Executar"), Qt.LeftButton)
    qtbot.waitUntil(lambda: page.btn_executar.isEnabled() and not page._worker.isRunning(), timeout=5000)
    assert "app ausente" in page.log.toPlainText()
    assert "Comando executado" not in page.log.toPlainText()
    assert command_history.carregar_historico() == []


def test_inicio_vazio_nao_despacha(qtbot, monkeypatch):
    page = HomePage()
    qtbot.addWidget(page)
    processar = MagicMock()
    monkeypatch.setattr(escravo, "processar_comando", processar)
    page.comando.setText("   ")
    qtbot.mouseClick(botao(page, "▶ Executar"), Qt.LeftButton)
    processar.assert_not_called()


def preencher_modal(dialog, nome, comandos):
    assert isinstance(dialog, CriarModoDialog)
    dialog.campo_nome.setText(nome)
    while len(dialog.campos_comando) < len(comandos):
        dialog.btn_adicionar.click()
    for campo, texto in zip(dialog.campos_comando, comandos):
        campo.setText(texto)
    dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.Save).click()


def test_criar_editar_executar_remover_modo_na_interface(qtbot, monkeypatch):
    page = ModesPage()
    qtbot.addWidget(page)
    original_exec = CriarModoDialog.exec
    respostas = iter([("Música", ["play", "próxima"]), ("Foco", ["play", "anterior"])])
    def interagir(dialog):
        nome, comandos = next(respostas)
        QTimer.singleShot(0, dialog, lambda: preencher_modal(dialog, nome, comandos))
        QTimer.singleShot(2000, dialog, dialog.reject)
        return original_exec(dialog)
    monkeypatch.setattr(CriarModoDialog, "exec", interagir)
    qtbot.mouseClick(botao(page, "+ Criar modo"), Qt.LeftButton)
    modo = modes_manager.listar_modos()[0]
    assert modo["nome"] == "Música"
    page._editar_modo(modo)
    assert modes_manager.listar_modos()[0]["id"] == modo["id"]
    keyboard = MagicMock()
    monkeypatch.setattr(escravo.pyautogui, "press", keyboard)
    monkeypatch.setattr(modes_executor, "PAUSA_ENTRE_COMANDOS", 0)
    try:
        qtbot.mouseClick(botao(page, "Foco"), Qt.LeftButton)
        qtbot.waitUntil(lambda: "concluído" in page.status.text(), timeout=5000)
        assert keyboard.call_args_list == [call("playpause"), call("prevtrack")]
    finally:
        if page._executor:
            assert page._executor.wait(5000)
    from ui.pages import modes_page
    menu = MagicMock()
    editar, remover = object(), object()
    menu.addAction.side_effect = [editar, remover]
    menu.exec.return_value = remover
    monkeypatch.setattr(modes_page, "QMenu", lambda *a: menu)
    page._menu_contexto(modes_manager.listar_modos()[0], botao(page, "Foco"), QPoint())
    assert modes_manager.listar_modos() == []
    assert "removido" in page.status.text()


def test_editar_modo_com_cinco_comandos(qtbot):
    dialog = CriarModoDialog(nome_inicial="Completo", comandos_iniciais=["play"] * 5)
    qtbot.addWidget(dialog)
    assert len(dialog.campos_comando) == 5
    assert not dialog.btn_adicionar.isEnabled()
    assert dialog.dados() == ("Completo", ["play"] * 5)


@pytest.mark.parametrize("frase,esperado", [
    ("Ikuro, play", "play"), ("  IKURO: próxima  ", "próxima"),
    ("ikurox play", None), ("olá ikuro", None), ("play", None),
])
def test_palavra_de_ativacao_respeita_nome_completo(qtbot, monkeypatch, desktop_simulado, frase, esperado):
    from ui.pages.ai_page import AIPage
    page = AIPage()
    qtbot.addWidget(page)
    page._nome_assistente = "Ikuro"
    executar = MagicMock()
    monkeypatch.setattr(page, "_processar_comando_de_voz", executar)
    page._ao_detectar_frase_continua(frase)
    if esperado is None:
        executar.assert_not_called()
    else:
        executar.assert_called_once_with(esperado)


def test_nome_sozinho_aguarda_proxima_frase(qtbot, monkeypatch, desktop_simulado):
    from ui.pages.ai_page import AIPage
    page = AIPage()
    qtbot.addWidget(page)
    page._nome_assistente = "Ikuro"
    executar = MagicMock()
    monkeypatch.setattr(page, "_processar_comando_de_voz", executar)
    page._ao_detectar_frase_continua("Ikuro")
    assert page._aguardando_comando_apos_wake
    executar.assert_not_called()
    page._ao_detectar_frase_continua("abrir editor")
    executar.assert_called_once_with("abrir editor")
    assert not page._aguardando_comando_apos_wake


@pytest.mark.parametrize("falha", [False, True])
def test_chat_reabilita_interface_apos_resposta_ou_erro(qtbot, monkeypatch, desktop_simulado, falha):
    from ui.pages.ai_page import AIPage
    page = AIPage()
    qtbot.addWidget(page)
    def enviar(modelo, mensagens, on_chunk):
        if falha:
            raise OSError("offline simulado")
        on_chunk("Olá!")
        return "Olá!"
    monkeypatch.setattr(ollama_manager, "enviar_mensagem", enviar)
    page.campo_mensagem.setText("como você está?")
    try:
        qtbot.mouseClick(page.btn_enviar, Qt.LeftButton)
        qtbot.waitUntil(lambda: page.btn_enviar.isEnabled(), timeout=5000)
        assert page.campo_mensagem.isEnabled()
        assert ("offline simulado" if falha else "Olá!") in page.historico_chat.toPlainText()
        if not falha:
            assert page._historico[-1] == {"role": "assistant", "content": "Olá!"}
    finally:
        if page._worker:
            assert page._worker.wait(5000)


def test_configuracao_aplica_e_persiste_tema(qtbot, qapp):
    from ui.pages.settings_page import SettingsPage
    anterior = qapp.styleSheet()
    page = SettingsPage()
    qtbot.addWidget(page)
    try:
        page.campo_hex.setText("#3366cc")
        qtbot.keyClick(page.campo_hex, Qt.Key_Return)
        qtbot.mouseClick(page.btn_aplicar, Qt.LeftButton)
        assert theme_manager.carregar_cor().name() == "#3366cc"
        assert qapp.styleSheet()
        page.campo_hex.setText("cor-invalida")
        qtbot.keyClick(page.campo_hex, Qt.Key_Return)
        assert "inválido" in page.status.text()
    finally:
        qapp.setStyleSheet(anterior)


def test_janela_real_navega_e_espera_threads_ao_fechar(qtbot, qapp, desktop_simulado):
    from ui.main_window import MainWindow
    liberar = threading.Event()
    class Tarefa(QThread):
        def run(self):
            liberar.wait(5)
    anterior = qapp.styleSheet()
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    worker = Tarefa()
    window.pagina_ia._worker = worker
    poller = window.pagina_musica._poller
    try:
        worker.start()
        qtbot.waitUntil(worker.isRunning)
        assert window.paginas.count() == 8
        for chave, pagina in window._mapa_paginas.items():
            window.sidebar.pagina_selecionada.emit(chave)
            assert window.paginas.currentWidget() is pagina
        window.close()
        assert window.isVisible(), "A janela não deve destruir uma thread em execução"
        liberar.set()
        qtbot.waitUntil(lambda: not window.isVisible(), timeout=5000)
        assert not worker.isRunning()
        assert not poller.isRunning()
    finally:
        liberar.set()
        worker.wait(5000)
        poller.parar()
        poller.wait(5000)
        qapp.setStyleSheet(anterior)
