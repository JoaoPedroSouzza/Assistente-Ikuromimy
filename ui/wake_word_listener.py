"""
Escuta contínua: o microfone fica sempre ouvindo em segundo plano.
Detecta quando alguém começa a falar (energia do áudio acima de um
limiar) e quando para (silêncio sustentado), captura esse trecho como
uma "frase" e manda pro reconhecedor. Quem decide se a frase era
"pra ele" (começa com a palavra de ativação) é quem usa essa classe —
ver ui/pages/ai_page.py.

Aviso importante: TUDO que for falado perto do microfone enquanto isso
está ativo é transcrito (mandado pro reconhecedor gratuito do Google)
— a palavra de ativação só filtra o que o app FAZ com o texto depois,
não evita a transcrição em si. Por isso a escuta contínua é uma opção
que liga/desliga, não fica ativa o tempo todo sem escolha do usuário.
"""

from __future__ import annotations

import queue

import numpy as np
import sounddevice as sd
import speech_recognition as sr

TAXA_AMOSTRAGEM = 16000
TAMANHO_BLOCO = 1024
LIMIAR_ENERGIA = 300          # ajuste se estiver sensível demais/de menos
SILENCIO_PARA_ENCERRAR = 1.0    # segundos de silêncio = frase acabou
DURACAO_MAXIMA_UTTERANCE = 10.0   # corta frases absurdamente longas


def _rms(bloco: np.ndarray) -> float:
    return float(np.sqrt(np.mean(bloco.astype(np.float64) ** 2)))


class EscutaContinua:
    """Motor de escuta contínua.

    Uso:
        escuta = EscutaContinua(ao_detectar_frase=minha_funcao)
        escuta.iniciar()   # bloqueia até parar() ser chamado de outra thread
        ...
        escuta.parar()

    'ao_detectar_frase' é chamado (de dentro da thread de escuta) com
    o texto reconhecido de CADA frase captada — a decisão do que fazer
    com isso é de quem usa essa classe.
    """

    def __init__(self, ao_detectar_frase):
        self.ao_detectar_frase = ao_detectar_frase
        self._rodando = False
        self._stream = None
        self._fila: queue.Queue = queue.Queue()

    def iniciar(self) -> None:
        self._rodando = True
        self._stream = sd.InputStream(
            samplerate=TAXA_AMOSTRAGEM,
            channels=1,
            dtype="int16",
            blocksize=TAMANHO_BLOCO,
            callback=self._callback_audio,
        )
        self._stream.start()
        self._loop_captura()

    def parar(self) -> None:
        self._rodando = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def _callback_audio(self, indata, frames, tempo, status) -> None:
        self._fila.put(indata.copy())

    def _loop_captura(self) -> None:
        reconhecedor = sr.Recognizer()
        buffer_fala: list[np.ndarray] = []
        em_fala = False
        blocos_silencio = 0

        blocos_por_segundo = TAXA_AMOSTRAGEM / TAMANHO_BLOCO
        blocos_silencio_max = int(blocos_por_segundo * SILENCIO_PARA_ENCERRAR)
        blocos_max_utterance = int(blocos_por_segundo * DURACAO_MAXIMA_UTTERANCE)

        while self._rodando:
            try:
                bloco = self._fila.get(timeout=0.5)
            except queue.Empty:
                continue

            energia = _rms(bloco)

            if energia > LIMIAR_ENERGIA:
                em_fala = True
                blocos_silencio = 0
                buffer_fala.append(bloco)
            elif em_fala:
                buffer_fala.append(bloco)
                blocos_silencio += 1

                fim_por_silencio = blocos_silencio >= blocos_silencio_max
                fim_por_duracao = len(buffer_fala) >= blocos_max_utterance

                if fim_por_silencio or fim_por_duracao:
                    audio_completo = np.concatenate(buffer_fala)
                    self._processar_utterance(audio_completo, reconhecedor)
                    buffer_fala = []
                    em_fala = False
                    blocos_silencio = 0

    def _processar_utterance(self, audio: np.ndarray, reconhecedor: sr.Recognizer) -> None:
        audio_bytes = audio.tobytes()
        audio_data = sr.AudioData(audio_bytes, TAXA_AMOSTRAGEM, 2)  # 2 bytes = int16

        try:
            texto = reconhecedor.recognize_google(audio_data, language="pt-BR")
        except (sr.UnknownValueError, sr.RequestError):
            return

        if texto:
            self.ao_detectar_frase(texto)
