"""Coordena ações do assistente sem depender de Qt."""
from threading import Lock
import logging
import time
import uuid
from core.visual_events import publish

_trava = Lock()
logger = logging.getLogger("ikuromimy.execucao")


class ExecucaoCancelada(RuntimeError):
    pass


def executar_acao(acao, cancelado=None, descricao="Ação do assistente"):
    """Uma automação por vez; permite cancelar uma tarefa ainda na fila."""
    inicio = time.monotonic()
    identificador = uuid.uuid4().hex[:12]
    while True:
        if cancelado is not None and cancelado():
            raise ExecucaoCancelada("Comando cancelado antes de iniciar")
        if _trava.acquire(timeout=0.05):
            break
    try:
        if cancelado is not None and cancelado():
            raise ExecucaoCancelada("Comando cancelado antes de iniciar")
        publish("command_started", descricao)
        resultado = acao()
        publish("command_finished", True)
        logger.info("acao_concluida id=%s duracao_ms=%.1f", identificador, (time.monotonic() - inicio) * 1000)
        return resultado
    except Exception as erro:
        publish("command_finished", False)
        logger.warning("acao_falhou id=%s tipo=%s", identificador, type(erro).__name__)
        raise
    finally:
        _trava.release()


def executar(comando: str, cancelado=None) -> bool:
    import escravo
    return executar_acao(lambda: escravo.processar_comando(comando), cancelado, comando)
