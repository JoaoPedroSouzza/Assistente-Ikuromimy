from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from PySide6.QtCore import Signal


class Sidebar(QWidget):

    # emite a "chave" da página que deve ser exibida (ex: "musica")
    pagina_selecionada = Signal(str)

    def __init__(self):
        super().__init__()

        self.setFixedWidth(220)

        layout = QVBoxLayout(self)

        # (texto do botão, chave da página correspondente)
        botoes = [
            ("🏠 Início", "inicio"),
            ("🎵 Música", "musica"),
            ("🧩 Modos", "modos"),
            ("🤖 IA", "ia"),
            ("📱 Controle Remoto", "remoto"),
            ("💻 Sistema", "sistema"),
            ("⚙ Configurações", "config"),
        ]

        for texto, chave in botoes:
            botao = QPushButton(texto)
            botao.setObjectName("botao_sidebar")
            botao.clicked.connect(
                lambda checked=False, c=chave: self.pagina_selecionada.emit(c)
            )
            layout.addWidget(botao)

        layout.addStretch()
