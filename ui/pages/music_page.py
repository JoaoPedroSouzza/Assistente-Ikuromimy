from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.media_info_worker import MediaInfoPoller

TAMANHO_CAPA = 140


class MusicPage(QWidget):
    """Página de controle de música. Play/pause/próxima/anterior usam
    as teclas de mídia do sistema (funciona com Spotify, YouTube
    Music, ou qualquer player tocando no momento). Volume usa a API de
    áudio do Windows direto, pra subir/descer em 10% exatos. A capa +
    nome da música tocando vêm da mesma API que a Central de Ações do
    Windows usa (System Media Transport Controls)."""

    PASSO_VOLUME = 10  # pontos percentuais por clique

    def __init__(self):
        super().__init__()

        self._poller: MediaInfoPoller | None = None

        area = QVBoxLayout(self)

        titulo = QLabel("🎵 Música")
        titulo.setObjectName("titulo")

        subtitulo = QLabel("Controle a reprodução atual")

        # -- música tocando agora (capa + nome) ------------------------------
        agora_tocando = QHBoxLayout()

        self.label_capa = QLabel()
        self.label_capa.setFixedSize(TAMANHO_CAPA, TAMANHO_CAPA)
        self.label_capa.setAlignment(Qt.AlignCenter)
        self.label_capa.setStyleSheet(
            "background-color: #26262b; border-radius: 8px; color: #666666;"
        )
        self.label_capa.setText("🎵")
        agora_tocando.addWidget(self.label_capa)

        info_texto = QVBoxLayout()
        self.label_titulo_musica = QLabel("Nada tocando no momento")
        self.label_titulo_musica.setStyleSheet("font-size: 16px; font-weight: 600;")
        self.label_titulo_musica.setWordWrap(True)

        self.label_artista = QLabel("")
        self.label_artista.setStyleSheet("color: #9a9aa2;")
        self.label_artista.setWordWrap(True)

        info_texto.addWidget(self.label_titulo_musica)
        info_texto.addWidget(self.label_artista)
        info_texto.addStretch()
        agora_tocando.addLayout(info_texto)
        agora_tocando.addStretch()

        # -- play/pause/próxima/anterior --------------------------------------
        botoes_layout = QHBoxLayout()

        self.btn_anterior = QPushButton("⏮ Anterior")
        self.btn_play_pause = QPushButton("⏯ Play / Pause")
        self.btn_proxima = QPushButton("⏭ Próxima")

        for botao in (self.btn_anterior, self.btn_play_pause, self.btn_proxima):
            botao.setMinimumHeight(70)
            botoes_layout.addWidget(botao)

        # -- volume ----------------------------------------------------------
        volume_layout = QHBoxLayout()

        self.btn_diminuir_volume = QPushButton(f"🔉 -{self.PASSO_VOLUME}%")
        self.label_volume = QLabel("Volume: --")
        self.label_volume.setAlignment(Qt.AlignCenter)
        self.btn_aumentar_volume = QPushButton(f"🔊 +{self.PASSO_VOLUME}%")

        for widget in (self.btn_diminuir_volume, self.label_volume, self.btn_aumentar_volume):
            widget.setMinimumHeight(45)
            volume_layout.addWidget(widget)

        self.btn_abrir_spotify = QPushButton("Abrir Spotify")
        self.btn_abrir_spotify.setMinimumHeight(45)

        self.status = QLabel("")
        self.status.setObjectName("status_musica")

        self.btn_anterior.clicked.connect(self.faixa_anterior)
        self.btn_play_pause.clicked.connect(self.play_pause)
        self.btn_proxima.clicked.connect(self.proxima_faixa)
        self.btn_abrir_spotify.clicked.connect(self.abrir_spotify)
        self.btn_aumentar_volume.clicked.connect(lambda: self._alterar_volume(self.PASSO_VOLUME))
        self.btn_diminuir_volume.clicked.connect(lambda: self._alterar_volume(-self.PASSO_VOLUME))

        area.addWidget(titulo)
        area.addWidget(subtitulo)
        area.addLayout(agora_tocando)
        area.addLayout(botoes_layout)
        area.addLayout(volume_layout)
        area.addWidget(self.btn_abrir_spotify)
        area.addWidget(self.status)
        area.addStretch()

        self._atualizar_label_volume()
        self._iniciar_poller()

    # ------------------------------------------------------------------
    # play/pause/próxima/anterior/spotify
    # ------------------------------------------------------------------

    def _executar(self, func, mensagem_sucesso: str) -> None:
        try:
            func()
            self.status.setText(mensagem_sucesso)
        except Exception as erro:
            self.status.setText(f"❌ Erro: {erro}")

    def play_pause(self) -> None:
        import escravo
        self._executar(escravo.media_play_pause, "⏯ Play / Pause enviado")

    def proxima_faixa(self) -> None:
        import escravo
        self._executar(escravo.media_next, "⏭ Próxima faixa")

    def faixa_anterior(self) -> None:
        import escravo
        self._executar(escravo.media_prev, "⏮ Faixa anterior")

    def abrir_spotify(self) -> None:
        import escravo
        self._executar(escravo.focar_janela_spotify, "🎵 Abrindo/focando o Spotify")

    # ------------------------------------------------------------------
    # volume
    # ------------------------------------------------------------------

    def _atualizar_label_volume(self) -> None:
        try:
            from ui import audio_control
            percentual = audio_control.obter_volume_percentual()
            self.label_volume.setText(f"Volume: {percentual}%")
        except Exception:
            self.label_volume.setText("Volume: indisponível")

    def _alterar_volume(self, delta: int) -> None:
        try:
            from ui import audio_control
            novo = audio_control.alterar_volume(delta)
            self.label_volume.setText(f"Volume: {novo}%")
            self.status.setText(f"🔊 Volume ajustado pra {novo}%")
        except Exception as erro:
            self.status.setText(f"❌ Não consegui ajustar o volume: {erro}")

    # ------------------------------------------------------------------
    # música tocando agora
    # ------------------------------------------------------------------

    def _iniciar_poller(self) -> None:
        try:
            self._poller = MediaInfoPoller(intervalo=3.0)
            self._poller.atualizado.connect(self._atualizar_agora_tocando)
            self._poller.start()

            app = QApplication.instance()
            if app is not None:
                app.aboutToQuit.connect(self._poller.parar)
        except Exception as erro:
            self.label_titulo_musica.setText("Não foi possível detectar a música tocando")
            self.label_artista.setText(str(erro))

    def _atualizar_agora_tocando(self, info: dict | None) -> None:
        if not info or not info.get("titulo"):
            self.label_titulo_musica.setText("Nada tocando no momento")
            self.label_artista.setText("")
            self.label_capa.setText("🎵")
            self.label_capa.setPixmap(QPixmap())
            return

        self.label_titulo_musica.setText(info["titulo"])
        self.label_artista.setText(info.get("artista", ""))

        capa_bytes = info.get("capa")
        if capa_bytes:
            pixmap = QPixmap()
            if pixmap.loadFromData(capa_bytes):
                pixmap = pixmap.scaled(
                    QSize(TAMANHO_CAPA, TAMANHO_CAPA),
                    Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation,
                )
                self.label_capa.setPixmap(pixmap)
                self.label_capa.setText("")
                return

        self.label_capa.setPixmap(QPixmap())
        self.label_capa.setText("🎵")
