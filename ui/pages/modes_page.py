from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QLabel, QMenu, QPushButton, QVBoxLayout, QWidget

from ui import modes_manager
from ui.modes_dialog import CriarModoDialog
from ui.modes_executor import ExecutorModo

COLUNAS = 3


class ModesPage(QWidget):
    """Aba Modos: grupos de até 5 comandos que rodam em sequência com
    um clique. Clique direito em qualquer modo (inclusive os que já
    vêm prontos) pra editar ou remover."""

    def __init__(self):
        super().__init__()

        self._executor: ExecutorModo | None = None

        area = QVBoxLayout(self)

        titulo = QLabel("🧩 Modos")
        titulo.setObjectName("titulo")

        subtitulo = QLabel(
            "Um clique executa vários comandos em sequência — clique direito pra editar/remover"
        )

        area.addWidget(titulo)
        area.addWidget(subtitulo)

        self.grid = QGridLayout()
        area.addLayout(self.grid)

        self.status = QLabel("")
        area.addWidget(self.status)

        area.addStretch()

        self._montar_modos()

    def _montar_modos(self) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        modos = modes_manager.listar_modos()

        for i, modo in enumerate(modos):
            botao = QPushButton(modo["nome"])
            botao.setMinimumHeight(50)
            botao.setToolTip(" → ".join(modo["comandos"]))
            botao.clicked.connect(lambda checked=False, m=modo: self._executar_modo(m))

            botao.setContextMenuPolicy(Qt.CustomContextMenu)
            botao.customContextMenuRequested.connect(
                lambda pos, m=modo, b=botao: self._menu_contexto(m, b, pos)
            )

            linha, coluna = divmod(i, COLUNAS)
            self.grid.addWidget(botao, linha, coluna)

        total = len(modos)
        linha, coluna = divmod(total, COLUNAS)
        botao_criar = QPushButton("+ Criar modo")
        botao_criar.setMinimumHeight(50)
        botao_criar.clicked.connect(self._criar_modo)
        self.grid.addWidget(botao_criar, linha, coluna)

    def _menu_contexto(self, modo: dict, botao: QPushButton, pos) -> None:
        menu = QMenu(self)
        acao_editar = menu.addAction("Editar")
        acao_remover = menu.addAction("Remover")
        escolhida = menu.exec(botao.mapToGlobal(pos))

        if escolhida == acao_editar:
            self._editar_modo(modo)
        elif escolhida == acao_remover:
            modes_manager.remover_modo(modo["id"])
            self._montar_modos()
            self.status.setText(f'🗑 Modo "{modo["nome"]}" removido.')

    def _criar_modo(self) -> None:
        dialog = CriarModoDialog(self)
        if dialog.exec() == CriarModoDialog.DialogCode.Accepted:
            nome, comandos = dialog.dados()
            if not nome or not comandos:
                self.status.setText("❌ Precisa de um nome e pelo menos 1 comando.")
                return
            modes_manager.adicionar_modo(nome, comandos)
            self._montar_modos()
            self.status.setText(f'✓ Modo "{nome}" criado.')

    def _editar_modo(self, modo: dict) -> None:
        dialog = CriarModoDialog(self, nome_inicial=modo["nome"], comandos_iniciais=modo["comandos"])
        if dialog.exec() == CriarModoDialog.DialogCode.Accepted:
            nome, comandos = dialog.dados()
            if not nome or not comandos:
                self.status.setText("❌ Precisa de um nome e pelo menos 1 comando.")
                return
            modes_manager.editar_modo(modo["id"], nome, comandos)
            self._montar_modos()
            self.status.setText(f'✓ Modo "{nome}" atualizado.')

    def _executar_modo(self, modo: dict) -> None:
        if self._executor is not None and self._executor.isRunning():
            self.status.setText("Aguarde o modo atual terminar.")
            return
        self.status.setText(f'▶ Executando "{modo["nome"]}"...')
        self._executor = ExecutorModo(modo["comandos"])
        self._executor.finished.connect(
            lambda: self.status.setText(f'✓ "{modo["nome"]}" concluído.')
        )
        self._executor.start()
