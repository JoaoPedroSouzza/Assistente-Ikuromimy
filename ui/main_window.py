import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QSizeGrip,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ui.sidebar import Sidebar
from ui.pages.home_page import HomePage
from ui.pages.music_page import MusicPage
from ui.pages.settings_page import SettingsPage
from ui.pages.system_page import SystemPage
from ui.pages.remote_page import RemotePage
from ui.pages.modes_page import ModesPage
from ui.pages.ai_page import AIPage
from ui.pages.friends_page import FriendsPage
from ui.title_bar import TitleBar
from ui import theme_manager


def _caminho_icone() -> str | None:
    """Acha o icon.ico tanto rodando via 'python interface.py' quanto
    dentro do .exe empacotado (sys._MEIPASS)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    caminho = os.path.join(base, "icon.ico")
    return caminho if os.path.exists(caminho) else None


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        # janela "sem moldura" — a barra de título é toda nossa, feita
        # em ui/title_bar.py, pra combinar com o tema do app
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.resize(1100, 700)

        caminho_icone = _caminho_icone()
        if caminho_icone:
            icone = QIcon(caminho_icone)
            self.setWindowIcon(icone)
            app = QApplication.instance()
            if app is not None:
                app.setWindowIcon(icone)  # ícone na barra de tarefas

        # reaplica o tema escolhido numa sessão anterior (ou o padrão,
        # se o usuário nunca personalizou nada ainda)
        theme_manager.aplicar_tema(theme_manager.carregar_cor())

        self.criar_interface(caminho_icone)

    def criar_interface(self, caminho_icone: str | None):

        principal = QWidget()
        self.setCentralWidget(principal)

        layout_geral = QVBoxLayout(principal)
        layout_geral.setContentsMargins(0, 0, 0, 0)
        layout_geral.setSpacing(0)

        # BARRA DE TÍTULO CUSTOMIZADA
        self.barra_titulo = TitleBar("Assistente Virtual Ikuromimy", caminho_icone, self)
        layout_geral.addWidget(self.barra_titulo)

        # CORPO (sidebar + páginas)
        corpo = QWidget()
        layout_corpo = QHBoxLayout(corpo)
        layout_corpo.setContentsMargins(0, 0, 0, 0)
        layout_corpo.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.pagina_selecionada.connect(self.trocar_pagina)
        layout_corpo.addWidget(self.sidebar)

        self.paginas = QStackedWidget()

        self.pagina_inicio = HomePage()
        self.pagina_musica = MusicPage()
        self.pagina_config = SettingsPage()
        self.pagina_sistema = SystemPage()
        self.pagina_remoto = RemotePage()
        self.pagina_modos = ModesPage()
        self.pagina_ia = AIPage()
        self.pagina_amigos = FriendsPage()

        self.paginas.addWidget(self.pagina_inicio)
        self.paginas.addWidget(self.pagina_musica)
        self.paginas.addWidget(self.pagina_config)
        self.paginas.addWidget(self.pagina_sistema)
        self.paginas.addWidget(self.pagina_remoto)
        self.paginas.addWidget(self.pagina_modos)
        self.paginas.addWidget(self.pagina_ia)
        self.paginas.addWidget(self.pagina_amigos)

        # mapa chave -> página, pra achar rápido quando a sidebar avisar
        self._mapa_paginas = {
            "inicio": self.pagina_inicio,
            "musica": self.pagina_musica,
            "config": self.pagina_config,
            "sistema": self.pagina_sistema,
            "remoto": self.pagina_remoto,
            "modos": self.pagina_modos,
            "ia": self.pagina_ia,
            "amigos": self.pagina_amigos,
        }

        layout_corpo.addWidget(self.paginas)
        layout_geral.addWidget(corpo, stretch=1)

        # "puxador" de redimensionar no canto inferior direito (janela
        # sem moldura não vem com isso de graça)
        rodape = QHBoxLayout()
        rodape.setContentsMargins(0, 0, 0, 0)
        rodape.addStretch()
        rodape.addWidget(QSizeGrip(self))
        layout_geral.addLayout(rodape)

    def trocar_pagina(self, chave: str) -> None:
        pagina = self._mapa_paginas.get(chave, self.pagina_inicio)
        self.paginas.setCurrentWidget(pagina)
