from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from ui import remote_config
from ui.remote_server import PORTA_PADRAO, ServidorRemoto, gerar_token, obter_ip_local, obter_mac_local


class RemotePage(QWidget):
    """Aba Controle Remoto: mostra o endereço e a chave que o app
    Android precisa pra se conectar, e liga/desliga o servidor local."""

    def __init__(self):
        super().__init__()

        self._servidor: ServidorRemoto | None = None
        self._token = remote_config.carregar_token()

        area = QVBoxLayout(self)

        titulo = QLabel("📱 Controle Remoto")
        titulo.setObjectName("titulo")

        subtitulo = QLabel(
            "Liga aqui e digita esses dois dados no app Android pra conectar"
        )

        self.label_ip = QLabel(f"Endereço:  {obter_ip_local()}:{PORTA_PADRAO}")
        self.label_ip.setStyleSheet("font-size: 18px; font-weight: 600;")

        self.label_token = QLabel(f"Chave de acesso:  {self._token}")
        self.label_token.setStyleSheet("font-size: 18px; font-weight: 600;")

        mac = obter_mac_local()
        texto_mac = mac if mac else "não foi possível detectar"
        self.label_mac = QLabel(f"Endereço MAC (pra ligar o PC pelo celular):  {texto_mac}")
        self.label_mac.setStyleSheet("font-size: 14px; color: #9a9aa2;")
        self.label_mac.setWordWrap(True)

        self.btn_novo_token = QPushButton("Gerar nova chave")
        self.btn_novo_token.clicked.connect(self._gerar_novo_token)

        self.btn_ligar = QPushButton("▶ Ligar controle remoto")
        self.btn_ligar.clicked.connect(self._alternar_servidor)

        self.status = QLabel("Servidor desligado")

        aviso = QLabel(
            "⚠️ Só funciona com o celular na MESMA rede Wi-Fi do PC. "
            "Não expõe nada pra internet.\n"
            "⚠️ Pra 'Ligar PC' funcionar pelo celular (Wake-on-LAN), "
            "o PC precisa estar em Suspensão (não desligado de vez), "
            "e essa opção precisa estar habilitada no Windows/BIOS."
        )
        aviso.setWordWrap(True)
        aviso.setStyleSheet("color: #9a9aa2;")

        area.addWidget(titulo)
        area.addWidget(subtitulo)
        area.addWidget(self.label_ip)
        area.addWidget(self.label_token)
        area.addWidget(self.label_mac)
        area.addWidget(self.btn_novo_token, alignment=Qt.AlignLeft)
        area.addWidget(self.btn_ligar)
        area.addWidget(self.status)
        area.addWidget(aviso)
        area.addStretch()

    def _gerar_novo_token(self) -> None:
        self._token = gerar_token()
        remote_config.salvar_token(self._token)
        self.label_token.setText(f"Chave de acesso:  {self._token}")
        if self._servidor is not None:
            self.status.setText(
                "⚠️ Chave alterada — desliga e liga o servidor de novo pra aplicar."
            )

    def _alternar_servidor(self) -> None:
        if self._servidor is None:
            try:
                self._servidor = ServidorRemoto(self._token)
                self._servidor.start()
            except OSError as erro:
                self.status.setText(f"❌ Não consegui abrir a porta: {erro}")
                self._servidor = None
                return

            self.btn_ligar.setText("⏹ Desligar controle remoto")
            self.status.setText("✓ Servidor ligado, aguardando o celular conectar...")
        else:
            self._servidor.parar()
            self._servidor.wait(2000)
            self._servidor = None
            self.btn_ligar.setText("▶ Ligar controle remoto")
            self.status.setText("Servidor desligado")
