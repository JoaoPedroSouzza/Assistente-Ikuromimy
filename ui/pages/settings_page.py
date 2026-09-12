from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ui import startup_manager, theme_manager, version
from ui.widgets import ColorWheel


class SettingsPage(QWidget):
    """Aba de Configurações: escolher uma cor na roda gera um tema
    monocromático (fundo, cards, bordas e destaque derivados dela) e
    aplica no app inteiro."""

    def __init__(self):
        super().__init__()

        area = QVBoxLayout(self)

        titulo = QLabel("⚙ Configurações")
        titulo.setObjectName("titulo")

        subtitulo = QLabel("Escolha uma cor na roda para personalizar o tema")

        cor_salva = theme_manager.carregar_cor()

        # -- roda de cores + controles ao lado -----------------------------
        linha_wheel = QHBoxLayout()

        self.roda = ColorWheel(200)
        self.roda.definir_cor(cor_salva)
        self.roda.corSelecionada.connect(self._ao_mudar_cor)

        controles = QVBoxLayout()

        controles.addWidget(QLabel("Brilho"))
        self.slider_brilho = QSlider(Qt.Horizontal)
        self.slider_brilho.setRange(15, 100)
        self.slider_brilho.setValue(int(cor_salva.getHsvF()[2] * 100))
        self.slider_brilho.valueChanged.connect(
            lambda v: self.roda.definir_brilho(v / 100)
        )
        controles.addWidget(self.slider_brilho)

        controles.addWidget(QLabel("Ou digite um código hexadecimal"))
        self.campo_hex = QLineEdit(cor_salva.name())
        self.campo_hex.setPlaceholderText("#7c8cff")
        self.campo_hex.returnPressed.connect(self._ao_digitar_hex)
        controles.addWidget(self.campo_hex)
        controles.addStretch()

        linha_wheel.addWidget(self.roda)
        linha_wheel.addLayout(controles)
        linha_wheel.addStretch()

        # -- prévia da paleta monocromática ---------------------------------
        area.addWidget(titulo)
        area.addWidget(subtitulo)
        area.addLayout(linha_wheel)

        area.addWidget(QLabel("Paleta monocromática"))
        self.linha_paleta = QHBoxLayout()
        self.swatches: list[QPushButton] = []
        for _ in range(5):
            swatch = QPushButton()
            swatch.setFixedHeight(40)
            swatch.setCursor(Qt.PointingHandCursor)
            self.swatches.append(swatch)
            self.linha_paleta.addWidget(swatch)
        area.addLayout(self.linha_paleta)

        self.status = QLabel()
        area.addWidget(self.status)

        self.btn_aplicar = QPushButton("Aplicar tema")
        self.btn_aplicar.clicked.connect(self._aplicar)
        area.addWidget(self.btn_aplicar)

        # -- iniciar com o Windows -------------------------------------------
        self.chk_iniciar_windows = QCheckBox("Iniciar automaticamente com o Windows")
        self.chk_iniciar_windows.setChecked(startup_manager.esta_ativado())
        self.chk_iniciar_windows.stateChanged.connect(self._alternar_inicializacao)
        area.addWidget(self.chk_iniciar_windows)

        if startup_manager.executavel_atual() is None:
            # rodando via 'python interface.py' (modo dev): não tem
            # .exe pra apontar o atalho, então desativa a opção
            self.chk_iniciar_windows.setEnabled(False)
            self.chk_iniciar_windows.setToolTip(
                "Só funciona no aplicativo já empacotado (.exe). "
                "Rodando via 'python interface.py' isso fica desativado."
            )

        area.addStretch()

        rotulo_versao = QLabel(f"Versão {version.VERSAO}")
        rotulo_versao.setStyleSheet("color: #666666; font-size: 12px;")
        area.addWidget(rotulo_versao, alignment=Qt.AlignRight)

        self._atualizar_previa(cor_salva)

    # ----------------------------------------------------------------
    # eventos
    # ----------------------------------------------------------------

    def _ao_mudar_cor(self, cor: QColor) -> None:
        self.campo_hex.setText(cor.name())
        self._atualizar_previa(cor)

    def _ao_digitar_hex(self) -> None:
        cor = QColor(self.campo_hex.text().strip())
        if cor.isValid():
            self.roda.definir_cor(cor)
            self._atualizar_previa(cor)
        else:
            self.status.setText("❌ Código de cor inválido")

    def _selecionar_tom(self, cor: QColor) -> None:
        self.roda.definir_cor(cor)
        self.campo_hex.setText(cor.name())
        self._atualizar_previa(cor)

    def _atualizar_previa(self, cor: QColor) -> None:
        paleta = theme_manager.gerar_paleta_monocromatica(cor)
        for swatch, tom in zip(self.swatches, paleta):
            swatch.setStyleSheet(
                f"background-color: {tom.name()}; border-radius: 6px; "
                f"border: 1px solid #00000040;"
            )
            anterior = getattr(swatch, "_selecionar_cor", None)
            if anterior is not None:
                swatch.clicked.disconnect(anterior)
            swatch._selecionar_cor = lambda checked=False, c=tom: self._selecionar_tom(c)
            swatch.clicked.connect(swatch._selecionar_cor)

        self.status.setText(f"Cor selecionada: {cor.name()}")

    def _aplicar(self) -> None:
        cor = self.roda.cor_atual()
        theme_manager.aplicar_tema(cor)
        self.status.setText(f"✓ Tema aplicado: {cor.name()}")

    def _alternar_inicializacao(self, estado: int) -> None:
        if estado:
            ok = startup_manager.ativar()
            if ok:
                self.status.setText("✓ Vai abrir automaticamente com o Windows a partir de agora.")
            else:
                self.status.setText("❌ Não consegui ativar a inicialização automática.")
                self.chk_iniciar_windows.blockSignals(True)
                self.chk_iniciar_windows.setChecked(False)
                self.chk_iniciar_windows.blockSignals(False)
        else:
            startup_manager.desativar()
            self.status.setText("Inicialização automática desativada.")
