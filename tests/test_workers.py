from unittest.mock import MagicMock, call

import pytest
from PySide6.QtCore import QThread
import escravo
from ui import ai_worker, modes_executor, modes_manager, ollama_manager, updater, updater_worker

pytestmark = pytest.mark.integration


def executar_thread(qtbot, worker):
    # wait() no finally garante que os patches sobrevivam ao fim da thread.
    try:
        with qtbot.waitSignal(worker.finished, timeout=5000):
            worker.start()
    finally:
        assert worker.wait(5000), "A thread não encerrou no prazo"


def test_chat_em_thread_real_entrega_pedacos_e_resultado(qtbot, monkeypatch):
    thread_usada = []
    def enviar(modelo, mensagens, on_chunk):
        thread_usada.append(QThread.currentThread())
        assert modelo == "teste"
        assert mensagens == [{"role": "user", "content": "oi"}]
        on_chunk("Olá ")
        on_chunk("Ikuro")
        return "Olá Ikuro"
    monkeypatch.setattr(ollama_manager, "enviar_mensagem", enviar)
    worker = ai_worker.ChatWorker("teste", [{"role": "user", "content": "oi"}])
    partes, finais, erros = [], [], []
    worker.pedaco_recebido.connect(partes.append)
    worker.concluido.connect(finais.append)
    worker.erro.connect(erros.append)
    executar_thread(qtbot, worker)
    qtbot.waitUntil(lambda: len(finais) == 1)
    assert partes == ["Olá ", "Ikuro"]
    assert finais == ["Olá Ikuro"]
    assert erros == []
    assert thread_usada == [worker]


def test_chat_falha_emite_erro_sem_sucesso(qtbot, monkeypatch):
    monkeypatch.setattr(ollama_manager, "enviar_mensagem", MagicMock(side_effect=OSError("offline")))
    worker = ai_worker.ChatWorker("teste", [])
    erros, finais = [], []
    worker.erro.connect(erros.append)
    worker.concluido.connect(finais.append)
    executar_thread(qtbot, worker)
    qtbot.waitUntil(lambda: bool(erros))
    assert erros == ["offline"]
    assert finais == []


def test_modo_salvo_executa_comandos_reais_em_ordem(qtbot, monkeypatch):
    modes_manager.adicionar_modo("Música", ["play", "próxima"])
    teclado = MagicMock()
    monkeypatch.setattr(escravo.pyautogui, "press", teclado)
    monkeypatch.setattr(modes_executor, "PAUSA_ENTRE_COMANDOS", 0)
    worker = modes_executor.ExecutorModo(modes_manager.listar_modos()[0]["comandos"])
    executar_thread(qtbot, worker)
    assert teclado.call_args_list == [call("playpause"), call("nexttrack")]


def test_atualizador_nao_aplica_download_falho(qtbot, monkeypatch):
    monkeypatch.setattr(updater, "baixar_atualizacao", MagicMock(return_value=None))
    aplicar = MagicMock()
    monkeypatch.setattr(updater, "aplicar_atualizacao", aplicar)
    worker = updater_worker.UpdaterWorker("baixar", "https://example.invalid/app.exe")
    resultados = []
    worker.concluido.connect(lambda ok, mensagem: resultados.append((ok, mensagem)))
    executar_thread(qtbot, worker)
    qtbot.waitUntil(lambda: bool(resultados))
    assert resultados[0][0] is False
    aplicar.assert_not_called()
