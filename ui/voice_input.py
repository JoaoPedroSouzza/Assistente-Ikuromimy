"""
Reconhecimento de voz: grava um trecho do microfone e transforma em
texto usando o reconhecedor gratuito do Google (sem chave de API,
sem custo nenhum) — só precisa de internet no momento de transcrever.

Optamos por isso em vez de um modelo 100% offline pra manter a
instalação simples pra qualquer pessoa que for usar o app — sem
precisar baixar mais um modelo separado (além do modelo de IA que o
Ollama já pede). Grava com 'sounddevice' (em vez de PyAudio) porque
tem disponibilidade de pacote pronto mais consistente em versões
novas do Python no Windows.
"""

from __future__ import annotations

import sounddevice as sd
import speech_recognition as sr

TAXA_AMOSTRAGEM = 16000
CANAIS = 1


def gravar_e_transcrever(duracao_segundos: float = 6.0, idioma: str = "pt-BR", on_level=None) -> str:
    """Grava do microfone padrão por 'duracao_segundos' segundos e
    devolve o texto reconhecido. Levanta RuntimeError com uma mensagem
    amigável se não conseguir gravar ou entender o que foi falado."""
    try:
        if on_level is None:
            audio_gravado = sd.rec(
                int(duracao_segundos * TAXA_AMOSTRAGEM), samplerate=TAXA_AMOSTRAGEM,
                channels=CANAIS, dtype="int16",
            )
            sd.wait()
        else:
            import numpy as np
            from threading import Event
            blocks = []
            complete = Event()
            remaining = int(duracao_segundos * TAXA_AMOSTRAGEM)
            def receive(indata, frames, timing, status):
                nonlocal remaining
                if remaining <= 0: return
                block = indata[:remaining].copy()
                blocks.append(block)
                remaining -= len(block)
                rms = float(np.sqrt(np.mean(block.astype(np.float64)**2)))
                on_level(min(1., rms/6000.))
                if remaining <= 0: complete.set()
            with sd.InputStream(samplerate=TAXA_AMOSTRAGEM, channels=CANAIS,
                                dtype="int16", blocksize=1024, callback=receive):
                if not complete.wait(duracao_segundos+3):
                    raise RuntimeError("O microfone não entregou áudio no tempo esperado.")
            on_level(0.)
            audio_gravado = np.concatenate(blocks)
    except Exception as erro:
        raise RuntimeError(f"Não consegui acessar o microfone: {erro}")

    audio_bytes = audio_gravado.tobytes()
    audio_data = sr.AudioData(audio_bytes, TAXA_AMOSTRAGEM, 2)  # 2 bytes = int16

    reconhecedor = sr.Recognizer()
    reconhecedor.operation_timeout = 10
    try:
        return reconhecedor.recognize_google(audio_data, language=idioma)
    except sr.UnknownValueError:
        raise RuntimeError("Não consegui entender o que foi falado. Tenta de novo?")
    except sr.RequestError as erro:
        raise RuntimeError(f"Erro ao consultar o reconhecimento de voz (precisa de internet): {erro}")
