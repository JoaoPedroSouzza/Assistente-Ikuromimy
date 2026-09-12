import os
import sys
import logging
from core.logging_config import configurar_logging

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def resource_path(caminho_relativo: str) -> str:
    """Resolve um caminho relativo tanto rodando 'python interface.py'
    quanto rodando o .exe empacotado pelo PyInstaller. No .exe, os
    arquivos de dados (como styles/dark.qss) ficam extraídos numa pasta
    temporária apontada por sys._MEIPASS — que só existe quando o app
    está "congelado" (frozen) pelo PyInstaller."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, caminho_relativo)


def main() -> None:
    if "--self-test" in sys.argv:
        # Smoke test do pacote: imports, interpretação e recursos; sem janela,
        # rede, microfone, comandos ou escrita de configurações do usuário.
        from core.comandos import eh_comando_conhecido
        ok = eh_comando_conhecido("play") and os.path.isfile(resource_path("styles/dark.qss"))
        sys.exit(0 if ok else 1)
    configurar_logging()
    logging.getLogger("ikuromimy.app").info("aplicativo_iniciado")
    app = QApplication(sys.argv)

    caminho_qss = resource_path(os.path.join("styles", "dark.qss"))
    try:
        with open(caminho_qss, "r", encoding="utf-8") as arquivo:
            app.setStyleSheet(arquivo.read())
    except FileNotFoundError:
        # não é fatal: a página de Configurações aplica um tema por
        # cima assim que a MainWindow abre, então o app continua com
        # uma aparência normal mesmo sem esse arquivo.
        logging.getLogger("ikuromimy.app").warning("estilo_base_ausente")

    janela = MainWindow()
    janela.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
