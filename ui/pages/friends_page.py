from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ui import firebase_client
from ui.friends_worker import ListaAmigosWorker, MensagensWorker, PresencaWorker


class ChatAmigoDialog(QDialog):
    """Janela de conversa com um amigo. Atualiza a cada poucos
    segundos (polling, mesmo padrão do resto do app — sem depender de
    websocket/realtime subscription pra evitar dependência nova)."""

    INTERVALO_ATUALIZACAO_MS = 4_000

    def __init__(self, uid_amigo: str, nome_amigo: str, parent=None):
        super().__init__(parent)
        self.uid_amigo = uid_amigo
        self.setWindowTitle(f"Conversa com {nome_amigo}")
        self.setMinimumSize(420, 500)

        layout = QVBoxLayout(self)

        self.historico = QTextEdit()
        self.historico.setReadOnly(True)
        layout.addWidget(self.historico)

        linha_envio = QHBoxLayout()
        self.campo_mensagem = QLineEdit()
        self.campo_mensagem.setPlaceholderText("Digite uma mensagem...")
        self.campo_mensagem.returnPressed.connect(self._enviar)
        linha_envio.addWidget(self.campo_mensagem)

        btn_enviar = QPushButton("Enviar")
        btn_enviar.clicked.connect(self._enviar)
        linha_envio.addWidget(btn_enviar)

        layout.addLayout(linha_envio)

        self._worker: MensagensWorker | None = None
        self._ultima_contagem = -1

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._atualizar_mensagens)
        self._timer.setInterval(self.INTERVALO_ATUALIZACAO_MS)
        self._timer.start()

        self._atualizar_mensagens()

    def _enviar(self) -> None:
        texto = self.campo_mensagem.text().strip()
        if not texto:
            return

        try:
            firebase_client.enviar_mensagem_amigo(self.uid_amigo, texto)
            self.campo_mensagem.clear()
            self._ultima_contagem = -1  # força recarregar já
            self._atualizar_mensagens()
        except Exception as erro:
            self.historico.append(f"<i>❌ Erro ao enviar: {erro}</i>")

    def _atualizar_mensagens(self) -> None:
        self._worker = MensagensWorker(self.uid_amigo)
        self._worker.concluido.connect(self._ao_receber_mensagens)
        self._worker.start()

    def _ao_receber_mensagens(self, mensagens: list) -> None:
        if len(mensagens) == self._ultima_contagem:
            return  # nada novo, evita "piscar" recarregando à toa
        self._ultima_contagem = len(mensagens)

        sessao = firebase_client.sessao_valida()
        meu_uid = sessao["localId"] if sessao else None

        self.historico.clear()
        for msg in mensagens:
            quem = "Você" if msg.get("remetente") == meu_uid else "Amigo"
            self.historico.append(f"<b>{quem}:</b> {msg.get('texto', '')}")

        barra = self.historico.verticalScrollBar()
        barra.setValue(barra.maximum())

    def closeEvent(self, event) -> None:
        self._timer.stop()
        super().closeEvent(event)


class FriendsPage(QWidget):
    """Aba Amigos: login/cadastro (Firebase) + lista de amigos com
    status online e o que estão ouvindo no momento."""

    def __init__(self):
        super().__init__()

        self._presenca_worker: PresencaWorker | None = None
        self._lista_worker: ListaAmigosWorker | None = None
        self._modo_cadastro = False

        area = QVBoxLayout(self)

        titulo = QLabel("👥 Amigos")
        titulo.setObjectName("titulo")
        area.addWidget(titulo)

        if not firebase_client.configurado():
            aviso = QLabel(
                "⚠️ O sistema de amigos ainda não foi configurado. "
                "Preenche ui/firebase_config.py com os dados do seu "
                "projeto Firebase (gratuito) — veja "
                "firebase_config_exemplo.py pra instruções passo a passo."
            )
            aviso.setWordWrap(True)
            area.addWidget(aviso)
            area.addStretch()
            return

        self._pilha = QStackedWidget()
        area.addWidget(self._pilha)

        self._pagina_login = self._criar_pagina_login()
        self._pagina_amigos = self._criar_pagina_amigos()

        self._pilha.addWidget(self._pagina_login)
        self._pilha.addWidget(self._pagina_amigos)

        self._timer_atualizacao = QTimer(self)
        self._timer_atualizacao.timeout.connect(self._atualizar_lista_amigos)
        self._timer_atualizacao.setInterval(20_000)

        self._verificar_sessao()

    # ------------------------------------------------------------------
    # login / cadastro
    # ------------------------------------------------------------------

    def _criar_pagina_login(self) -> QWidget:
        pagina = QWidget()
        layout = QVBoxLayout(pagina)

        self.campo_email = QLineEdit()
        self.campo_email.setPlaceholderText("E-mail")
        layout.addWidget(self.campo_email)

        self.campo_senha = QLineEdit()
        self.campo_senha.setPlaceholderText("Senha (mínimo 6 caracteres)")
        self.campo_senha.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.campo_senha)

        self.campo_nome_usuario = QLineEdit()
        self.campo_nome_usuario.setPlaceholderText("Nome de usuário (só no cadastro)")
        self.campo_nome_usuario.setVisible(False)
        layout.addWidget(self.campo_nome_usuario)

        self.status_login = QLabel("")
        self.status_login.setWordWrap(True)
        layout.addWidget(self.status_login)

        self.btn_entrar = QPushButton("Entrar")
        self.btn_entrar.clicked.connect(self._fazer_login)
        layout.addWidget(self.btn_entrar)

        self.btn_alternar_modo = QPushButton("Não tem conta? Cadastre-se")
        self.btn_alternar_modo.clicked.connect(self._alternar_modo_login)
        layout.addWidget(self.btn_alternar_modo, alignment=Qt.AlignLeft)

        layout.addStretch()
        return pagina

    def _alternar_modo_login(self) -> None:
        self._modo_cadastro = not self._modo_cadastro
        self.campo_nome_usuario.setVisible(self._modo_cadastro)
        self.btn_entrar.setText("Cadastrar" if self._modo_cadastro else "Entrar")
        self.btn_alternar_modo.setText(
            "Já tem conta? Entrar" if self._modo_cadastro else "Não tem conta? Cadastre-se"
        )

    def _fazer_login(self) -> None:
        email = self.campo_email.text().strip()
        senha = self.campo_senha.text()

        if not email or not senha:
            self.status_login.setText("Preenche e-mail e senha.")
            return

        self.btn_entrar.setEnabled(False)
        self.status_login.setText("Aguenta um instante...")

        try:
            if self._modo_cadastro:
                nome_usuario = self.campo_nome_usuario.text().strip()
                if not nome_usuario:
                    self.status_login.setText("Escolhe um nome de usuário.")
                    return
                firebase_client.cadastrar(email, senha, nome_usuario)
            else:
                firebase_client.entrar(email, senha)

            self._entrar_na_area_logada()
        except Exception as erro:
            self.status_login.setText(f"❌ {erro}")
        finally:
            self.btn_entrar.setEnabled(True)

    def _verificar_sessao(self) -> None:
        if firebase_client.sessao_valida():
            self._entrar_na_area_logada()
        else:
            self._pilha.setCurrentWidget(self._pagina_login)

    def _entrar_na_area_logada(self) -> None:
        self._pilha.setCurrentWidget(self._pagina_amigos)
        self._atualizar_lista_amigos()
        self._timer_atualizacao.start()

        if not self._presenca_worker:
            self._presenca_worker = PresencaWorker()
            self._presenca_worker.start()

    # ------------------------------------------------------------------
    # lista de amigos
    # ------------------------------------------------------------------

    def _criar_pagina_amigos(self) -> QWidget:
        pagina = QWidget()
        layout = QVBoxLayout(pagina)

        linha_add = QHBoxLayout()
        self.campo_novo_amigo = QLineEdit()
        self.campo_novo_amigo.setPlaceholderText("Nome de usuário do seu amigo")
        linha_add.addWidget(self.campo_novo_amigo)

        btn_add = QPushButton("+ Adicionar amigo")
        btn_add.clicked.connect(self._adicionar_amigo)
        linha_add.addWidget(btn_add)
        layout.addLayout(linha_add)

        self.status_amigos = QLabel("")
        self.status_amigos.setWordWrap(True)
        layout.addWidget(self.status_amigos)

        layout.addWidget(QLabel("Pedidos recebidos:"))
        self.lista_pedidos = QListWidget()
        self.lista_pedidos.setMaximumHeight(120)
        layout.addWidget(self.lista_pedidos)

        layout.addWidget(QLabel("Seus amigos:"))
        self.lista_amigos = QListWidget()
        layout.addWidget(self.lista_amigos)

        btn_sair = QPushButton("Sair da conta")
        btn_sair.clicked.connect(self._sair)
        layout.addWidget(btn_sair, alignment=Qt.AlignLeft)

        return pagina

    def _adicionar_amigo(self) -> None:
        nome = self.campo_novo_amigo.text().strip()
        if not nome:
            return
        try:
            firebase_client.enviar_pedido_amizade(nome)
            self.status_amigos.setText(f"✓ Pedido enviado pra {nome}.")
            self.campo_novo_amigo.clear()
            self._atualizar_lista_amigos()
        except Exception as erro:
            self.status_amigos.setText(f"❌ {erro}")

    def _atualizar_lista_amigos(self) -> None:
        self._lista_worker = ListaAmigosWorker()
        self._lista_worker.concluido.connect(self._ao_atualizar_lista)
        self._lista_worker.erro.connect(lambda msg: self.status_amigos.setText(f"❌ {msg}"))
        self._lista_worker.start()

    def _ao_atualizar_lista(self, amigos: list) -> None:
        self.lista_pedidos.clear()
        self.lista_amigos.clear()

        algum_pedido = False

        for amigo in amigos:
            if amigo["status_amizade"] == "pendente_recebido":
                algum_pedido = True
                item = QListWidgetItem()
                self.lista_pedidos.addItem(item)

                widget_linha = QWidget()
                layout_linha = QHBoxLayout(widget_linha)
                layout_linha.setContentsMargins(4, 2, 4, 2)
                layout_linha.addWidget(QLabel(f'{amigo["nome_usuario"]} quer te adicionar'))
                layout_linha.addStretch()

                btn_aceitar = QPushButton("Aceitar")
                btn_aceitar.clicked.connect(
                    lambda checked=False, uid=amigo["uid"]: self._aceitar(uid)
                )
                layout_linha.addWidget(btn_aceitar)

                btn_recusar = QPushButton("Recusar")
                btn_recusar.clicked.connect(
                    lambda checked=False, uid=amigo["uid"]: self._recusar(uid)
                )
                layout_linha.addWidget(btn_recusar)

                item.setSizeHint(widget_linha.sizeHint())
                self.lista_pedidos.setItemWidget(item, widget_linha)

            elif amigo["status_amizade"] == "aceito":
                bolinha = "🟢" if amigo["online"] else "⚪"
                texto = f'{bolinha} {amigo["nome_usuario"]}'
                if amigo["online"] and amigo["status_texto"]:
                    texto += f'  —  {amigo["status_texto"]}'

                item = QListWidgetItem()
                self.lista_amigos.addItem(item)

                widget_linha = QWidget()
                layout_linha = QHBoxLayout(widget_linha)
                layout_linha.setContentsMargins(4, 2, 4, 2)
                layout_linha.addWidget(QLabel(texto))
                layout_linha.addStretch()

                btn_conversar = QPushButton("💬 Conversar")
                btn_conversar.clicked.connect(
                    lambda checked=False, uid=amigo["uid"], nome=amigo["nome_usuario"]:
                        self._abrir_chat(uid, nome)
                )
                layout_linha.addWidget(btn_conversar)

                item.setSizeHint(widget_linha.sizeHint())
                self.lista_amigos.setItemWidget(item, widget_linha)

            elif amigo["status_amizade"] == "pendente_enviado":
                self.lista_amigos.addItem(
                    QListWidgetItem(f'⏳ {amigo["nome_usuario"]} (pedido enviado, aguardando)')
                )

        if not algum_pedido:
            self.lista_pedidos.addItem(QListWidgetItem("Nenhum pedido pendente."))

    def _aceitar(self, uid_amigo: str) -> None:
        try:
            firebase_client.aceitar_pedido(uid_amigo)
            self._atualizar_lista_amigos()
        except Exception as erro:
            self.status_amigos.setText(f"❌ {erro}")

    def _recusar(self, uid_amigo: str) -> None:
        try:
            firebase_client.recusar_pedido(uid_amigo)
            self._atualizar_lista_amigos()
        except Exception as erro:
            self.status_amigos.setText(f"❌ {erro}")

    def _abrir_chat(self, uid_amigo: str, nome_amigo: str) -> None:
        dialogo = ChatAmigoDialog(uid_amigo, nome_amigo, parent=self)
        dialogo.exec()

    def _sair(self) -> None:
        firebase_client.sair()
        if self._presenca_worker:
            self._presenca_worker.parar()
            self._presenca_worker = None
        self._timer_atualizacao.stop()
        self.campo_email.clear()
        self.campo_senha.clear()
        self._pilha.setCurrentWidget(self._pagina_login)
