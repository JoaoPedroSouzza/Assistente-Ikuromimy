"""
Barra de título customizada (substitui a barra padrão do Windows),
combinando com o tema escuro do app. Usa os métodos nativos do Qt6
(startSystemMove) pra arrastar a janela com o mesmo comportamento de
uma barra de título de verdade, incluindo o "encaixe" nas bordas da
tela do Windows 11.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

ALTURA_BARRA = 36


class TitleBar(QWidget):

    def __init__(self, titulo: str, caminho_icone: str | None, parent=None):
        super().__init__(parent)
        self.setObjectName("barra_titulo")
        self.setFixedHeight(ALTURA_BARRA)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 0, 0)
        layout.setSpacing(8)

        if caminho_icone:
            icone_label = QLabel()
            icone_label.setPixmap(QIcon(caminho_icone).pixmap(QSize(18, 18)))
            layout.addWidget(icone_label)

        label_titulo = QLabel(titulo)
        label_titulo.setObjectName("titulo_barra")
        layout.addWidget(label_titulo)

        layout.addStretch()

        self.btn_minimizar = self._criar_botao("—", "botao_titulo")
        self.btn_maximizar = self._criar_botao("☐", "botao_titulo")
        self.btn_fechar = self._criar_botao("✕", "botao_fechar")

        self.btn_minimizar.clicked.connect(self._minimizar)
        self.btn_maximizar.clicked.connect(self._alternar_maximizado)
        self.btn_fechar.clicked.connect(self._fechar)

        layout.addWidget(self.btn_minimizar)
        layout.addWidget(self.btn_maximizar)
        layout.addWidget(self.btn_fechar)

    def _criar_botao(self, texto: str, nome_objeto: str) -> QPushButton:
        botao = QPushButton(texto)
        botao.setObjectName(nome_objeto)
        botao.setFixedSize(46, ALTURA_BARRA)
        botao.setCursor(Qt.PointingHandCursor)
        return botao

    def _minimizar(self) -> None:
        self.window().showMinimized()

    def _alternar_maximizado(self) -> None:
        janela = self.window()
        if janela.isMaximized():
            janela.showNormal()
            self.btn_maximizar.setText("☐")
        else:
            janela.showMaximized()
            self.btn_maximizar.setText("❐")

    def _fechar(self) -> None:
        self.window().close()

    # ------------------------------------------------------------------
    # arrastar a janela pela barra (API nativa do Qt6 — dá o mesmo
    # comportamento de mover/encaixar que uma barra de título normal)
    # ------------------------------------------------------------------

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            alca = self.window().windowHandle()
            if alca is not None:
                alca.startSystemMove()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        self._alternar_maximizado()
        super().mouseDoubleClickEvent(event)
