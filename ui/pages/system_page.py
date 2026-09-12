from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui import system_info
from ui.updater_worker import UpdaterWorker
from ui.version import VERSAO


class SystemPage(QWidget):
    """Aba Sistema: mostra processador, RAM, placa de vídeo e
    armazenamento do PC em cards. Lê tudo assim que a página é criada;
    o botão 'Atualizar' relê na hora (útil pro uso de RAM/disco, que
    muda com o tempo)."""

    def __init__(self):
        super().__init__()

        area = QVBoxLayout(self)

        titulo = QLabel("💻 Sistema")
        titulo.setObjectName("titulo")

        subtitulo = QLabel("Informações de hardware do seu PC")

        self.btn_atualizar = QPushButton("🔄 Atualizar")
        self.btn_atualizar.clicked.connect(self._carregar)

        area.addWidget(titulo)
        area.addWidget(subtitulo)
        area.addWidget(self.btn_atualizar, alignment=Qt.AlignLeft)

        self._grid = QGridLayout()
        self._grid.setHorizontalSpacing(16)
        self._grid.setVerticalSpacing(16)
        area.addLayout(self._grid)

        # -- atualização do assistente --------------------------------------
        self._worker: UpdaterWorker | None = None
        self._info_atualizacao: dict | None = None

        rotulo_versao = QLabel(f"Versão instalada: {VERSAO}")
        rotulo_versao.setStyleSheet("color: #9a9aa2; margin-top: 16px;")

        self.btn_verificar_update = QPushButton("🔄 Atualizar Assistente")
        self.btn_verificar_update.clicked.connect(self._verificar_atualizacao)

        self.barra_progresso = QProgressBar()
        self.barra_progresso.setVisible(False)

        self.status_update = QLabel("")
        self.status_update.setWordWrap(True)

        area.addWidget(rotulo_versao)
        area.addWidget(self.btn_verificar_update, alignment=Qt.AlignLeft)
        area.addWidget(self.barra_progresso)
        area.addWidget(self.status_update)

        area.addStretch()

        self._carregar()

    # ------------------------------------------------------------------

    def _limpar_grid(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _card(self, titulo_texto: str, linhas: list[str]) -> QFrame:
        card = QFrame()
        card.setObjectName("card")

        layout = QVBoxLayout(card)

        rotulo_titulo = QLabel(titulo_texto)
        rotulo_titulo.setStyleSheet("font-weight: 600; font-size: 15px;")
        layout.addWidget(rotulo_titulo)

        if not linhas:
            layout.addWidget(QLabel("Não foi possível detectar"))
        else:
            for linha in linhas:
                rotulo = QLabel(linha)
                rotulo.setWordWrap(True)
                layout.addWidget(rotulo)

        return card

    def _carregar(self) -> None:
        self._limpar_grid()

        info = system_info.obter_resumo_sistema()

        card_cpu = self._card(
            "🧠 Processador",
            [info["processador"], info["nucleos"]],
        )

        card_ram = self._card(
            "💾 Memória RAM",
            [f"Total: {info['ram']['total']}", info["ram"]["uso"]],
        )

        card_gpu = self._card(
            "🎮 Placa de Vídeo",
            info["placas_de_video"],
        )

        linhas_disco = [
            f"{d['unidade']}  —  {d['total']}  ({d['usado']})"
            for d in info["armazenamento"]
        ] or ["Nenhuma unidade detectada"]

        card_disco = self._card("🗄 Armazenamento", linhas_disco)

        self._grid.addWidget(card_cpu, 0, 0)
        self._grid.addWidget(card_ram, 0, 1)
        self._grid.addWidget(card_gpu, 1, 0)
        self._grid.addWidget(card_disco, 1, 1)

    # ------------------------------------------------------------------
    # atualização do assistente
    # ------------------------------------------------------------------

    def _verificar_atualizacao(self) -> None:
        self.btn_verificar_update.setEnabled(False)
        self.status_update.setText("Procurando atualizações...")

        self._worker = UpdaterWorker(modo="verificar")
        self._worker.verificado.connect(self._ao_verificar)
        self._worker.start()

    def _ao_verificar(self, resultado: dict) -> None:
        self.btn_verificar_update.setEnabled(True)

        if not resultado.get("ok"):
            self.status_update.setText(f"❌ {resultado.get('erro', 'Falha ao verificar atualização.')}")
            return

        atualizacao = resultado.get("atualizacao")
        if not atualizacao:
            self.status_update.setText("✓ Você já está na versão mais recente.")
            return

        self._info_atualizacao = atualizacao

        caixa = QMessageBox(self)
        caixa.setWindowTitle("Atualização disponível")
        caixa.setText(
            f"Tem uma versão nova: {atualizacao['tag']}\n\n"
            f"{atualizacao['notas'] or 'Sem notas de versão.'}\n\n"
            "Baixar e instalar agora? O app vai fechar e abrir de novo "
            "automaticamente."
        )
        caixa.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        if caixa.exec() == QMessageBox.Yes:
            self._baixar_atualizacao()

    def _baixar_atualizacao(self) -> None:
        if not self._info_atualizacao:
            return

        self.btn_verificar_update.setEnabled(False)
        self.barra_progresso.setVisible(True)
        self.barra_progresso.setValue(0)
        self.status_update.setText("Baixando atualização...")

        self._worker = UpdaterWorker(
            modo="baixar", url_download=self._info_atualizacao["url_download"]
        )
        self._worker.progresso.connect(self._ao_progredir)
        self._worker.concluido.connect(self._ao_concluir)
        self._worker.start()

    def _ao_progredir(self, baixado: int, total: int) -> None:
        if total > 0:
            self.barra_progresso.setValue(int(baixado / total * 100))

    def _ao_concluir(self, sucesso: bool, mensagem: str) -> None:
        self.status_update.setText(mensagem)
        self.barra_progresso.setVisible(False)
        self.btn_verificar_update.setEnabled(True)

        if sucesso:
            from PySide6.QtWidgets import QApplication
            QApplication.instance().quit()
