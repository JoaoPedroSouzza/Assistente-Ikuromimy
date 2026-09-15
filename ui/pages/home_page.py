from PySide6.QtCore import Qt, QStringListModel
from PySide6.QtWidgets import (
    QCompleter,
    QGridLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from ui.components.motion import ReactiveButton


from ui import command_history, shortcuts_manager
from ui.command_worker import CommandWorker

COLUNAS_ATALHOS = 4


class HomePage(QWidget):
    """Página inicial: atalhos pré-definidos (um clique executa),
    campo de comando livre com autocompletar/sugestão + log."""

    def __init__(self, engine=None, theme=None, bus=None):
        super().__init__()
        self._worker = None
        if engine is not None:
            self._build_reactive(engine, theme, bus)
            return

        area = QVBoxLayout(self)

        titulo = QLabel("🤖 Assistente Virtual Ikuromimy")
        titulo.setObjectName("titulo")

        subtitulo = QLabel("Digite um comando, clique em um atalho, ou clique direito pra editar/remover")

        # -- atalhos pré-definidos ------------------------------------------
        area.addWidget(titulo)
        area.addWidget(subtitulo)

        self.grid_atalhos = QGridLayout()
        area.addLayout(self.grid_atalhos)
        self._montar_atalhos()

        # -- campo de comando com autocompletar ------------------------------
        self.comando = QLineEdit()
        self.comando.setPlaceholderText("Ex: abrir spotify...")
        self.comando.returnPressed.connect(self.executar_comando)

        self._completer = QCompleter()
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchContains)
        self.comando.setCompleter(self._completer)
        self._atualizar_sugestoes()

        botao = ReactiveButton("▶ Executar")
        self.btn_executar = botao
        botao.clicked.connect(self.executar_comando)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.append("Sistema iniciado...")

        area.addWidget(self.comando)
        area.addWidget(botao)
        area.addWidget(self.log)

    def _build_reactive(self, engine, theme, bus):
        from PySide6.QtWidgets import QHBoxLayout, QFrame, QStackedWidget
        from ui.components.ai_core import AICore
        from ui.state.assistant_state import LABELS
        self.bus = bus
        area = QVBoxLayout(self)
        area.setContentsMargins(28, 16, 28, 12)
        self.views = QStackedWidget()
        area.addWidget(self.views, 1)
        hero = QWidget()
        hero_area = QVBoxLayout(hero)
        hero_area.setContentsMargins(0, 8, 0, 0)
        overline = QLabel("SEU ESPAÇO. SUA INTELIGÊNCIA.")
        overline.setObjectName("eyebrow"); overline.setAlignment(Qt.AlignCenter)
        hero_area.addWidget(overline)
        title = QLabel("Como posso ajudar?")
        title.setObjectName("heroTitle"); title.setAlignment(Qt.AlignCenter)
        hero_area.addWidget(title)
        note = QLabel("Uma ideia, uma conversa ou o próximo passo.")
        note.setObjectName("muted"); note.setAlignment(Qt.AlignCenter); hero_area.addWidget(note)
        self.core = AICore(engine, theme, bus)
        hero_area.addWidget(self.core, 1)
        self.state_label = QLabel("●  Aguardando você")
        self.state_label.setAlignment(Qt.AlignCenter)
        hero_area.addWidget(self.state_label)
        bus.assistant_state_changed.connect(lambda state, detail: self.state_label.setText("●  " + (detail or LABELS[state])))
        hero_area.addSpacing(12)
        self.quick = QFrame(); self.quick.setObjectName("glass")
        quick_area = QHBoxLayout(self.quick)
        for label, key in (("↗  Atalhos", "atalhos"), ("♫  Música", "musica"), ("◇  Modos", "modos")):
            button = ReactiveButton(label)
            button.clicked.connect(lambda checked=False, k=key: bus.page_changed.emit(k))
            quick_area.addWidget(button)
        hero_area.addWidget(self.quick)
        self.views.addWidget(hero)
        shortcuts = QWidget(); shortcut_area = QVBoxLayout(shortcuts)
        title = QLabel("Seus atalhos"); title.setObjectName("titulo"); shortcut_area.addWidget(title)
        subtitle = QLabel("Clique para executar. Clique direito para editar ou remover.")
        subtitle.setWordWrap(True); subtitle.setObjectName("muted"); shortcut_area.addWidget(subtitle)
        self.grid_atalhos = QGridLayout(); shortcut_area.addLayout(self.grid_atalhos)
        self._montar_atalhos()
        self.comando = QLineEdit(); self.comando.setPlaceholderText("Ex: abrir spotify...")
        self.comando.returnPressed.connect(self.executar_comando)
        self._completer = QCompleter(); self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchContains); self.comando.setCompleter(self._completer)
        self._atualizar_sugestoes()
        self.btn_executar = ReactiveButton("▶ Executar"); self.btn_executar.clicked.connect(self.executar_comando)
        shortcut_area.addWidget(self.comando); shortcut_area.addWidget(self.btn_executar)
        self.log = QTextEdit(); self.log.setReadOnly(True); self.log.append("Sistema iniciado...")
        shortcut_area.addWidget(self.log, 1)
        self.views.addWidget(shortcuts)

    def set_view(self, shortcuts=False):
        self.views.setCurrentIndex(1 if shortcuts else 0)

    # ----------------------------------------------------------------
    # atalhos pré-definidos
    # ----------------------------------------------------------------

    def _montar_atalhos(self) -> None:
        while self.grid_atalhos.count():
            item = self.grid_atalhos.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        atalhos = shortcuts_manager.listar_atalhos()

        for i, atalho in enumerate(atalhos):
            botao = ReactiveButton(atalho["label"])
            botao.clicked.connect(
                lambda checked=False, c=atalho["comando"]: self._executar_texto(c)
            )

            botao.setContextMenuPolicy(Qt.CustomContextMenu)
            botao.customContextMenuRequested.connect(
                lambda pos, a=atalho, b=botao: self._menu_contexto_atalho(a, b, pos)
            )

            linha, coluna = divmod(i, COLUNAS_ATALHOS)
            self.grid_atalhos.addWidget(botao, linha, coluna)

        # botão de adicionar, sempre por último
        total = len(atalhos)
        linha, coluna = divmod(total, COLUNAS_ATALHOS)
        botao_add = ReactiveButton("+ Novo atalho")
        botao_add.clicked.connect(self._adicionar_atalho)
        self.grid_atalhos.addWidget(botao_add, linha, coluna)

    def _menu_contexto_atalho(self, atalho: dict, botao: QPushButton, pos) -> None:
        menu = QMenu(self)
        acao_editar = menu.addAction("Editar")
        acao_remover = menu.addAction("Remover")
        escolhida = menu.exec(botao.mapToGlobal(pos))

        if escolhida == acao_editar:
            self._editar_atalho(atalho)
        elif escolhida == acao_remover:
            shortcuts_manager.remover_atalho(atalho["id"])
            self._montar_atalhos()

    def _adicionar_atalho(self) -> None:
        label, ok = QInputDialog.getText(self, "Novo atalho", "Nome do botão (ex: 🎮 Abrir Steam):")
        if not ok or not label.strip():
            return

        comando, ok = QInputDialog.getText(self, "Novo atalho", "Comando a executar (ex: abrir steam):")
        if not ok or not comando.strip():
            return

        shortcuts_manager.adicionar_atalho(label.strip(), comando.strip())
        self._montar_atalhos()

    def _editar_atalho(self, atalho: dict) -> None:
        novo_label, ok = QInputDialog.getText(
            self, "Editar atalho", "Nome do botão:", text=atalho["label"]
        )
        if not ok or not novo_label.strip():
            return

        novo_comando, ok = QInputDialog.getText(
            self, "Editar atalho", "Comando a executar:", text=atalho["comando"]
        )
        if not ok or not novo_comando.strip():
            return

        shortcuts_manager.editar_atalho(atalho["id"], novo_label.strip(), novo_comando.strip())
        self._montar_atalhos()

    # ----------------------------------------------------------------
    # autocompletar
    # ----------------------------------------------------------------

    def _atualizar_sugestoes(self, historico=None) -> None:
        sugestoes = [
            "tocar ", "pesquisar ", "abrir ", "fechar ",
            "play", "pause", "próxima", "anterior",
            "aumentar volume", "diminuir volume",
            "atualizar apps", "sair",
        ]

        try:
            import escravo
            for nome in escravo.listar_apps_conhecidos():
                sugestoes.append(f"abrir {nome}")
        except Exception:
            pass

        # histórico primeiro (mais relevante), sem duplicar
        if historico is None:
            historico = command_history.carregar_historico()
        sugestoes = historico + [s for s in sugestoes if s not in historico]

        modelo = self._completer.model()
        if modelo is None:
            self._completer.setModel(QStringListModel(sugestoes, self._completer))
        else:
            modelo.setStringList(sugestoes)

    # ----------------------------------------------------------------
    # execução
    # ----------------------------------------------------------------

    def _executar_texto(self, texto: str) -> None:
        self.comando.setText(texto)
        self.executar_comando()

    def executar_comando(self):
        if self._worker is not None and self._worker.isRunning():
            return
        comando = self.comando.text()

        if not comando.strip():
            return

        self.log.append(f"Você: {comando}")

        self.btn_executar.setEnabled(False)
        self._worker = CommandWorker(comando)
        self._worker.concluido.connect(lambda continuar: self._ao_concluir(comando, continuar))
        self._worker.erro.connect(self._ao_erro)
        self._worker.finished.connect(lambda: self.btn_executar.setEnabled(True))
        self._worker.start()

    def _ao_concluir(self, comando, continuar):
        if continuar:
            self.log.append("✓ Comando executado\n")
            historico = command_history.adicionar_ao_historico(comando)
            self._atualizar_sugestoes(historico)
        else:
            self.log.append("Assistente encerrado\n")

    def _ao_erro(self, erro):
        self.log.append(f"❌ Erro: {erro}")
