from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Signal
from PySide6.QtWidgets import QPushButton, QVBoxLayout, QWidget

LARGURA_RECOLHIDA = 60
LARGURA_EXPANDIDA = 220
DURACAO_ANIMACAO_MS = 180


class Sidebar(QWidget):

    # emite a "chave" da página que deve ser exibida (ex: "musica")
    pagina_selecionada = Signal(str)

    def __init__(self):
        super().__init__()

        self._expandida = False

        # não usa setFixedWidth aqui de propósito — precisamos animar
        # entre min/max, e setFixedWidth trava os dois no mesmo valor
        self.setMinimumWidth(LARGURA_RECOLHIDA)
        self.setMaximumWidth(LARGURA_RECOLHIDA)

        layout = QVBoxLayout(self)

        # (ícone, texto, chave da página) — separados pra poder mostrar
        # só o ícone quando recolhida, e ícone+texto quando expandida
        self._info_botoes = [
            ("🏠", "Início", "inicio"),
            ("🎵", "Música", "musica"),
            ("🧩", "Modos", "modos"),
            ("🤖", "IA", "ia"),
            ("📱", "Controle Remoto", "remoto"),
            ("💻", "Sistema", "sistema"),
            ("⚙", "Configurações", "config"),
        ]

        self._botoes: list[QPushButton] = []
        for icone, texto, chave in self._info_botoes:
            botao = QPushButton(icone)
            botao.setObjectName("botao_sidebar")
            botao.setToolTip(texto)
            botao.clicked.connect(
                lambda checked=False, c=chave: self.pagina_selecionada.emit(c)
            )
            layout.addWidget(botao)
            self._botoes.append(botao)

        layout.addStretch()

        self._anim_min = QPropertyAnimation(self, b"minimumWidth")
        self._anim_min.setDuration(DURACAO_ANIMACAO_MS)
        self._anim_min.setEasingCurve(QEasingCurve.Type.InOutCubic)

        self._anim_max = QPropertyAnimation(self, b"maximumWidth")
        self._anim_max.setDuration(DURACAO_ANIMACAO_MS)
        self._anim_max.setEasingCurve(QEasingCurve.Type.InOutCubic)

    # ------------------------------------------------------------------
    # expandir ao passar o mouse, recolher ao tirar
    # ------------------------------------------------------------------

    def enterEvent(self, event) -> None:
        self._expandir()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._recolher()
        super().leaveEvent(event)

    def _expandir(self) -> None:
        if self._expandida:
            return
        self._expandida = True
        self._animar_para(LARGURA_EXPANDIDA)
        for (icone, texto, _chave), botao in zip(self._info_botoes, self._botoes):
            botao.setText(f"{icone}  {texto}")

    def _recolher(self) -> None:
        if not self._expandida:
            return
        self._expandida = False
        self._animar_para(LARGURA_RECOLHIDA)
        for (icone, _texto, _chave), botao in zip(self._info_botoes, self._botoes):
            botao.setText(icone)

    def _animar_para(self, largura: int) -> None:
        largura_atual = self.width()

        self._anim_min.stop()
        self._anim_min.setStartValue(largura_atual)
        self._anim_min.setEndValue(largura)

        self._anim_max.stop()
        self._anim_max.setStartValue(largura_atual)
        self._anim_max.setEndValue(largura)

        self._anim_min.start()
        self._anim_max.start()
