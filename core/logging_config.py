"""Logs locais limitados em tamanho; conteúdo de comandos não é registrado."""
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import re
import time


class FormatoSeguro(logging.Formatter):
    converter = time.gmtime
    _segredo = re.compile(r'''(?i)(\b(?:auth|key|apiKey|idToken|refreshToken|token|password|senha)\b["']?\s*[=:]\s*["']?)([^"'\s&,}]+)''')

    def format(self, record):
        texto = super().format(record)
        texto = self._segredo.sub(r"\1[REMOVIDO]", texto)
        return re.sub(r"(?i)(Bearer\s+)\S+", r"\1[REMOVIDO]", texto)


def configurar_logging(diretorio=None):
    pasta = Path(diretorio) if diretorio is not None else Path(
        os.environ.get("LOCALAPPDATA", str(Path.home()))
    ) / "Ikuromimy" / "logs"
    caminho = pasta.resolve() / "assistente.log"
    logger = logging.getLogger("ikuromimy")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    for handler in logger.handlers:
        if getattr(handler, "baseFilename", None) == str(caminho):
            return caminho
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    try:
        pasta.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(caminho, maxBytes=1_048_576, backupCount=3, encoding="utf-8")
    except OSError:
        handler = logging.StreamHandler()
        caminho = None
    handler.setFormatter(FormatoSeguro("%(asctime)sZ %(levelname)s %(name)s %(message)s", "%Y-%m-%dT%H:%M:%S"))
    logger.addHandler(handler)
    return caminho
