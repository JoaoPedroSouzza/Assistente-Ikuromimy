import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ui import ollama_manager
from ui.ai_worker import BaixarModeloWorker, ChatWorker, DownloadInstaladorWorker
from ui.voice_worker import VoiceWorker
from ui.wake_word_worker import WakeWordWorker

PADRAO_COMANDO = re.compile(r"<comando>(.*?)</comando>", re.IGNORECASE | re.DOTALL)
PALAVRA_ATIVACAO = "assistente"

PROMPT_SISTEMA = """Você é o Assistente Virtual Ikuromimy, um assistente pessoal estilo \
Jarvis, rodando localmente no computador do usuário. Fale em português do Brasil, de \
forma natural, breve e direta.

Você consegue executar ações de verdade no PC do usuário. Quando o pedido dele \
corresponder a uma ação, inclua na sua resposta uma tag no formato \
<comando>texto do comando</comando> — o app detecta essa tag e executa de verdade.

Comandos disponíveis (use exatamente essa sintaxe dentro da tag):
- abrir <nome do programa>
- fechar <nome do programa>
- tocar <nome da música>
- pesquisar <termo>
- play / pause / próxima / anterior
- aumentar volume / diminuir volume

Exemplo: se o usuário disser "abre o spotify pra mim", responda algo como \
"Claro! <comando>abrir spotify</comando> Já abri o Spotify pra você."

Se o pedido não for uma ação, apenas converse normalmente, sem usar a tag."""


class AIPage(QWidget):
    """Aba de IA: fluxo guiado pra detectar/instalar o Ollama e baixar
    um modelo, e depois disso, um chat estilo Jarvis que também
    consegue executar comandos reais do assistente."""

    def __init__(self):
        super().__init__()

        self._historico: list[dict] = [{"role": "system", "content": PROMPT_SISTEMA}]
        self._worker = None
        self._wake_worker: WakeWordWorker | None = None
        self._aguardando_comando_apos_wake = False

        self._area = QVBoxLayout(self)

        titulo = QLabel("🤖 Assistente IA (local)")
        titulo.setObjectName("titulo")
        self._area.addWidget(titulo)

        self.status_setup = QLabel("Verificando o Ollama...")
        self.status_setup.setWordWrap(True)
        self._area.addWidget(self.status_setup)

        self.barra_progresso = QProgressBar()
        self.barra_progresso.setVisible(False)
        self._area.addWidget(self.barra_progresso)

        self.btn_acao_setup = QPushButton()
        self.btn_acao_setup.setVisible(False)
        self._area.addWidget(self.btn_acao_setup, alignment=Qt.AlignLeft)

        # -- chat (só aparece quando tudo estiver pronto) --------------------
        self.chat_widget = QWidget()
        chat_layout = QVBoxLayout(self.chat_widget)
        chat_layout.setContentsMargins(0, 12, 0, 0)

        linha_modelo = QHBoxLayout()
        linha_modelo.addWidget(QLabel("Modelo:"))
        self.combo_modelo = QComboBox()
        linha_modelo.addWidget(self.combo_modelo)
        linha_modelo.addStretch()

        self.btn_escuta_continua = QPushButton(f'🎙 Ouvir sempre (diga "{PALAVRA_ATIVACAO}")')
        self.btn_escuta_continua.setCheckable(True)
        self.btn_escuta_continua.toggled.connect(self._alternar_escuta_continua)
        linha_modelo.addWidget(self.btn_escuta_continua)

        chat_layout.addLayout(linha_modelo)

        self.historico_chat = QTextEdit()
        self.historico_chat.setReadOnly(True)
        chat_layout.addWidget(self.historico_chat)

        linha_envio = QHBoxLayout()
        self.campo_mensagem = QLineEdit()
        self.campo_mensagem.setPlaceholderText("Fale com o assistente...")
        self.campo_mensagem.returnPressed.connect(self._enviar_mensagem)
        linha_envio.addWidget(self.campo_mensagem)

        self.btn_enviar = QPushButton("Enviar")
        self.btn_enviar.clicked.connect(self._enviar_mensagem)
        linha_envio.addWidget(self.btn_enviar)

        self.btn_microfone = QPushButton("🎤")
        self.btn_microfone.setFixedWidth(40)
        self.btn_microfone.setToolTip("Falar (grava 6 segundos)")
        self.btn_microfone.clicked.connect(self._iniciar_gravacao)
        linha_envio.addWidget(self.btn_microfone)

        chat_layout.addLayout(linha_envio)

        self.chat_widget.setVisible(False)
        self._area.addWidget(self.chat_widget, stretch=1)

        self._verificar_estado()

    # ------------------------------------------------------------------
    # fluxo guiado (instalar/iniciar/baixar modelo)
    # ------------------------------------------------------------------

    def _verificar_estado(self) -> None:
        self.btn_acao_setup.setVisible(False)
        self.barra_progresso.setVisible(False)

        if not ollama_manager.ollama_esta_instalado():
            self.status_setup.setText(
                "O Ollama (motor de IA local, gratuito) não está instalado nesse PC."
            )
            self.btn_acao_setup.setText("⬇ Baixar e instalar o Ollama")
            self.btn_acao_setup.clicked.disconnect() if self._tem_conexao(self.btn_acao_setup) else None
            self.btn_acao_setup.clicked.connect(self._baixar_ollama)
            self.btn_acao_setup.setVisible(True)
            return

        if not ollama_manager.ollama_esta_rodando():
            self.status_setup.setText("O Ollama está instalado, mas não está rodando.")
            self.btn_acao_setup.setText("▶ Iniciar o Ollama")
            self.btn_acao_setup.clicked.disconnect() if self._tem_conexao(self.btn_acao_setup) else None
            self.btn_acao_setup.clicked.connect(self._iniciar_ollama)
            self.btn_acao_setup.setVisible(True)
            return

        modelos = ollama_manager.listar_modelos_instalados()
        if not modelos:
            self.status_setup.setText(
                f"Ollama rodando, mas nenhum modelo baixado ainda. "
                f"Recomendado: {ollama_manager.MODELO_PADRAO} (~1.3GB, rápido)."
            )
            self.btn_acao_setup.setText(f"⬇ Baixar modelo ({ollama_manager.MODELO_PADRAO})")
            self.btn_acao_setup.clicked.disconnect() if self._tem_conexao(self.btn_acao_setup) else None
            self.btn_acao_setup.clicked.connect(self._baixar_modelo)
            self.btn_acao_setup.setVisible(True)
            return

        # tudo pronto
        self.status_setup.setText("✓ Ollama pronto.")
        self.combo_modelo.clear()
        self.combo_modelo.addItems(modelos)
        self.chat_widget.setVisible(True)

    def _tem_conexao(self, botao: QPushButton) -> bool:
        try:
            return botao.receivers(botao.clicked) > 0
        except Exception:
            return False

    def _baixar_ollama(self) -> None:
        self.btn_acao_setup.setEnabled(False)
        self.barra_progresso.setVisible(True)
        self.barra_progresso.setValue(0)
        self.status_setup.setText("Baixando o instalador do Ollama...")

        self._worker = DownloadInstaladorWorker()
        self._worker.progresso.connect(self._ao_progredir_download)
        self._worker.concluido.connect(self._ao_baixar_instalador)
        self._worker.start()

    def _ao_progredir_download(self, baixado: int, total: int) -> None:
        if total > 0:
            self.barra_progresso.setValue(int(baixado / total * 100))

    def _ao_baixar_instalador(self, caminho) -> None:
        self.barra_progresso.setVisible(False)
        self.btn_acao_setup.setEnabled(True)

        if not caminho:
            self.status_setup.setText("❌ Não consegui baixar o instalador do Ollama.")
            return

        ollama_manager.executar_instalador(caminho)
        self.status_setup.setText(
            "Instalador aberto — segue os passos na janela dele. "
            "Quando terminar, volta aqui e clica no botão abaixo."
        )
        self.btn_acao_setup.setText("🔄 Já instalei, verificar de novo")
        self.btn_acao_setup.clicked.disconnect() if self._tem_conexao(self.btn_acao_setup) else None
        self.btn_acao_setup.clicked.connect(self._verificar_estado)

    def _iniciar_ollama(self) -> None:
        ollama_manager.iniciar_ollama()
        self.status_setup.setText("Iniciando... aguenta um instante e clica em verificar de novo.")
        self.btn_acao_setup.setText("🔄 Verificar de novo")
        self.btn_acao_setup.clicked.disconnect() if self._tem_conexao(self.btn_acao_setup) else None
        self.btn_acao_setup.clicked.connect(self._verificar_estado)

    def _baixar_modelo(self) -> None:
        self.btn_acao_setup.setEnabled(False)
        self.barra_progresso.setVisible(True)
        self.barra_progresso.setValue(0)

        self._worker = BaixarModeloWorker(ollama_manager.MODELO_PADRAO)
        self._worker.progresso.connect(self._ao_progredir_modelo)
        self._worker.concluido.connect(self._ao_baixar_modelo)
        self._worker.start()

    def _ao_progredir_modelo(self, status: str, completado: int, total: int) -> None:
        self.status_setup.setText(f"Baixando modelo: {status}")
        if total > 0:
            self.barra_progresso.setValue(int(completado / total * 100))

    def _ao_baixar_modelo(self, sucesso: bool) -> None:
        self.barra_progresso.setVisible(False)
        self.btn_acao_setup.setEnabled(True)

        if not sucesso:
            self.status_setup.setText("❌ Não consegui baixar o modelo. Tenta de novo?")
            return

        self._verificar_estado()

    # ------------------------------------------------------------------
    # chat
    # ------------------------------------------------------------------

    def _enviar_mensagem(self) -> None:
        texto = self.campo_mensagem.text().strip()
        if not texto:
            return

        self.campo_mensagem.clear()

        # comando direto e reconhecido (mesma lógica do escravo.py) —
        # executa na hora, sem depender da IA formatar a tag certinho
        try:
            import escravo
            if escravo.eh_comando_conhecido(texto):
                self.historico_chat.append(f"<b>Você:</b> {texto}")
                self._executar_comando(texto)
                return
        except Exception:
            pass  # se der erro checando, cai pro fluxo normal (conversa com a IA)

        self.campo_mensagem.setEnabled(False)
        self.btn_enviar.setEnabled(False)

        self.historico_chat.append(f"<b>Você:</b> {texto}")
        self.historico_chat.append("<b>Assistente:</b> ")

        self._historico.append({"role": "user", "content": texto})

        modelo = self.combo_modelo.currentText() or ollama_manager.MODELO_PADRAO

        self._worker = ChatWorker(modelo, list(self._historico))
        self._worker.pedaco_recebido.connect(self._ao_receber_pedaco)
        self._worker.concluido.connect(self._ao_concluir_resposta)
        self._worker.erro.connect(self._ao_erro_chat)
        self._worker.start()

    def _ao_receber_pedaco(self, pedaco: str) -> None:
        cursor = self.historico_chat.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(pedaco)
        self.historico_chat.setTextCursor(cursor)

    def _ao_concluir_resposta(self, resposta_completa: str) -> None:
        self._historico.append({"role": "assistant", "content": resposta_completa})
        self.historico_chat.append("")

        self.campo_mensagem.setEnabled(True)
        self.btn_enviar.setEnabled(True)
        self.campo_mensagem.setFocus()

        comando = PADRAO_COMANDO.search(resposta_completa)
        if comando:
            texto_comando = comando.group(1).strip()
            self._executar_comando(texto_comando)

    def _ao_erro_chat(self, mensagem: str) -> None:
        self.historico_chat.append(f"<i>❌ Erro: {mensagem}</i>")
        self.campo_mensagem.setEnabled(True)
        self.btn_enviar.setEnabled(True)

    def _executar_comando(self, comando: str) -> None:
        try:
            import escravo
            escravo.processar_comando(comando)
            self.historico_chat.append(f"<i>⚙ Comando executado: {comando}</i>")
        except Exception as erro:
            self.historico_chat.append(f"<i>❌ Erro ao executar '{comando}': {erro}</i>")

    # ------------------------------------------------------------------
    # entrada por voz
    # ------------------------------------------------------------------

    def _iniciar_gravacao(self) -> None:
        self.btn_microfone.setEnabled(False)
        self.btn_microfone.setText("🔴")
        self.campo_mensagem.setEnabled(False)
        self.btn_enviar.setEnabled(False)
        self.campo_mensagem.setPlaceholderText("Gravando... fala agora (6 segundos)")

        self._voice_worker = VoiceWorker(duracao_segundos=6.0)
        self._voice_worker.concluido.connect(self._ao_transcrever)
        self._voice_worker.erro.connect(self._ao_erro_gravacao)
        self._voice_worker.start()

    def _ao_transcrever(self, texto: str) -> None:
        self._restaurar_botao_microfone()
        self.campo_mensagem.setText(texto)
        self._enviar_mensagem()

    def _ao_erro_gravacao(self, mensagem: str) -> None:
        self._restaurar_botao_microfone()
        self.historico_chat.append(f"<i>🎤 {mensagem}</i>")

    def _restaurar_botao_microfone(self) -> None:
        self.btn_microfone.setEnabled(True)
        self.btn_microfone.setText("🎤")
        self.campo_mensagem.setEnabled(True)
        self.btn_enviar.setEnabled(True)
        self.campo_mensagem.setPlaceholderText("Fale com o assistente...")

    # ------------------------------------------------------------------
    # escuta contínua com palavra de ativação
    # ------------------------------------------------------------------

    def _alternar_escuta_continua(self, ligado: bool) -> None:
        if ligado:
            self.btn_escuta_continua.setText("🔴 Ouvindo... (clique pra desligar)")
            self._aguardando_comando_apos_wake = False

            self._wake_worker = WakeWordWorker()
            self._wake_worker.frase_detectada.connect(self._ao_detectar_frase_continua)
            self._wake_worker.start()

            self.historico_chat.append(
                f'<i>🎙 Escuta contínua ligada. Diga "{PALAVRA_ATIVACAO}" antes do comando.</i>'
            )
        else:
            self.btn_escuta_continua.setText(f'🎙 Ouvir sempre (diga "{PALAVRA_ATIVACAO}")')
            if self._wake_worker:
                self._wake_worker.parar()
                self._wake_worker = None
            self.historico_chat.append("<i>🎙 Escuta contínua desligada.</i>")

    def _ao_detectar_frase_continua(self, texto: str) -> None:
        texto_normalizado = texto.strip().lower()
        prefixo = PALAVRA_ATIVACAO.lower()

        # já estávamos esperando o comando depois de um "assistente" sozinho
        if self._aguardando_comando_apos_wake:
            self._aguardando_comando_apos_wake = False
            self._processar_comando_de_voz(texto)
            return

        if not texto_normalizado.startswith(prefixo):
            return  # não era "pra ele" — ignora

        resto = texto[len(PALAVRA_ATIVACAO):].strip(" ,.:-")

        if not resto:
            # só disse "assistente" — responde e espera a próxima frase
            resposta = "Olá, o que deseja?"
            self.historico_chat.append(f"<b>Assistente:</b> {resposta}")
            try:
                import escravo
                escravo.falar(resposta)
            except Exception:
                pass
            self._aguardando_comando_apos_wake = True
            return

        self._processar_comando_de_voz(resto)

    def _processar_comando_de_voz(self, texto: str) -> None:
        self.campo_mensagem.setText(texto)
        self._enviar_mensagem()
