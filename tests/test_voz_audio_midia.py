import io
import json
from unittest.mock import MagicMock

import numpy as np
import pytest
from ui import voice_input, wake_word_listener as wake, media_info, audio_control
from ui.voice_worker import VoiceWorker
from ui.media_info_worker import MediaInfoPoller


@pytest.mark.parametrize("erro,trecho", [(voice_input.sr.UnknownValueError(), "entender"), (voice_input.sr.RequestError("offline"), "internet")])
def test_transcricao_falha_com_mensagem_amigavel(monkeypatch, erro, trecho):
    monkeypatch.setattr(voice_input.sd, "rec", MagicMock(return_value=np.zeros((10, 1), dtype=np.int16)))
    monkeypatch.setattr(voice_input.sd, "wait", MagicMock())
    monkeypatch.setattr(voice_input.sr.Recognizer, "recognize_google", MagicMock(side_effect=erro))
    with pytest.raises(RuntimeError, match=trecho):
        voice_input.gravar_e_transcrever()


def test_microfone_ausente_nao_transcreve(monkeypatch):
    monkeypatch.setattr(voice_input.sd, "rec", MagicMock(side_effect=OSError("sem dispositivo")))
    with pytest.raises(RuntimeError, match="microfone"):
        voice_input.gravar_e_transcrever()


def test_gravacao_usa_formato_e_idioma_corretos(monkeypatch):
    amostras = np.array([[1], [-2]], dtype=np.int16)
    gravar = MagicMock(return_value=amostras)
    reconhecer = MagicMock(return_value="play")
    monkeypatch.setattr(voice_input.sd, "rec", gravar)
    monkeypatch.setattr(voice_input.sd, "wait", MagicMock())
    monkeypatch.setattr(voice_input.sr.Recognizer, "recognize_google", reconhecer)
    assert voice_input.gravar_e_transcrever(2, "pt-BR") == "play"
    gravar.assert_called_once_with(32000, samplerate=16000, channels=1, dtype="int16")
    assert reconhecer.call_args.args[0].frame_data == amostras.tobytes()
    assert reconhecer.call_args.kwargs == {"language": "pt-BR"}


@pytest.mark.parametrize("falha", [False, True])
def test_voice_worker_real_entrega_texto_ou_erro(qtbot, monkeypatch, falha):
    monkeypatch.setattr(voice_input, "gravar_e_transcrever", MagicMock(return_value="play", side_effect=RuntimeError("sem microfone") if falha else None))
    worker = VoiceWorker()
    try:
        with qtbot.waitSignal(worker.erro if falha else worker.concluido, timeout=5000) as resultado:
            worker.start()
        assert resultado.args == ["sem microfone" if falha else "play"]
    finally:
        assert worker.wait(5000)


def test_energia_nao_estoura_int16():
    assert wake._rms(np.array([32767, -32767], dtype=np.int16)) == pytest.approx(32767)


@pytest.mark.parametrize("resultado", ["Ikuro play", "", None])
def test_escuta_so_entrega_frase_nao_vazia(resultado):
    callback = MagicMock()
    escuta = wake.EscutaContinua(callback)
    reconhecedor = MagicMock()
    reconhecedor.recognize_google.return_value = resultado
    escuta._processar_utterance(np.zeros((16, 1), dtype=np.int16), reconhecedor)
    if resultado:
        callback.assert_called_once_with(resultado)
    else:
        callback.assert_not_called()


@pytest.mark.parametrize("erro", [voice_input.sr.UnknownValueError(), voice_input.sr.RequestError("offline")])
def test_escuta_ignora_falha_de_reconhecimento(erro):
    callback = MagicMock()
    escuta = wake.EscutaContinua(callback)
    reconhecedor = MagicMock()
    reconhecedor.recognize_google.side_effect = erro
    escuta._processar_utterance(np.zeros((16, 1), dtype=np.int16), reconhecedor)
    callback.assert_not_called()


def test_parar_escuta_fecha_stream_uma_vez():
    escuta = wake.EscutaContinua(MagicMock())
    stream = MagicMock()
    escuta._stream = stream
    escuta._rodando = True
    escuta.parar()
    escuta.parar()
    stream.stop.assert_called_once()
    stream.close.assert_called_once()
    assert not escuta._rodando
    assert escuta._stream is None


def test_escuta_libera_stream_se_captura_falhar(monkeypatch):
    stream = MagicMock()
    monkeypatch.setattr(wake.sd, "InputStream", MagicMock(return_value=stream))
    escuta = wake.EscutaContinua(MagicMock())
    monkeypatch.setattr(escuta, "_loop_captura", MagicMock(side_effect=RuntimeError("captura falhou")))
    with pytest.raises(RuntimeError, match="captura falhou"):
        escuta.iniciar()
    stream.close.assert_called_once()
    assert not escuta._rodando


@pytest.mark.parametrize("silencio", [False, True])
def test_captura_encerra_frase_por_silencio_ou_duracao(monkeypatch, silencio):
    escuta = wake.EscutaContinua(MagicMock())
    monkeypatch.setattr(wake, "TAXA_AMOSTRAGEM", 4)
    monkeypatch.setattr(wake, "TAMANHO_BLOCO", 1)
    monkeypatch.setattr(wake, "SILENCIO_PARA_ENCERRAR", 0.5)
    monkeypatch.setattr(wake, "DURACAO_MAXIMA_UTTERANCE", 1)
    blocos = [1000, 0, 0] if silencio else [1000] * 4
    fila = MagicMock()
    def proximo(**kwargs):
        if not blocos:
            escuta.parar()
            raise wake.queue.Empty
        return np.array([[blocos.pop(0)]], dtype=np.int16)
    fila.get.side_effect = proximo
    escuta._fila = fila
    processar = MagicMock()
    monkeypatch.setattr(escuta, "_processar_utterance", processar)
    escuta._rodando = True
    escuta._loop_captura()
    processar.assert_called_once()
    assert len(processar.call_args.args[0]) == (3 if silencio else 4)


@pytest.mark.parametrize("atual,delta,esperado", [(0, -10, 0), (95, 10, 100), (50, -10, 40)])
def test_volume_limita_escala_sem_alterar_pc(monkeypatch, atual, delta, esperado):
    interface = MagicMock()
    interface.GetMasterVolumeLevelScalar.return_value = atual / 100
    monkeypatch.setattr(audio_control, "_obter_interface_volume", lambda: interface)
    assert audio_control.alterar_volume(delta) == esperado
    interface.SetMasterVolumeLevelScalar.assert_called_once_with(esperado / 100, None)


def test_dispositivo_audio_ausente(monkeypatch):
    monkeypatch.setattr(audio_control, "_obter_interface_volume", MagicMock(side_effect=OSError("sem áudio")))
    with pytest.raises(OSError, match="sem áudio"):
        audio_control.obter_volume_percentual()


@pytest.mark.parametrize("titulo,esperado", [(None, None), ("Spotify", {"titulo": "", "artista": "", "capa": None, "tocando": False}), ("Artista - Faixa - ao vivo", {"titulo": "Faixa - ao vivo", "artista": "Artista", "capa": b"capa", "tocando": True})])
def test_musica_atual_interpreta_estado(monkeypatch, titulo, esperado):
    monkeypatch.setattr(media_info, "_titulo_janela_spotify", lambda: titulo)
    monkeypatch.setattr(media_info, "_buscar_capa_itunes", lambda *a: b"capa")
    assert media_info.obter_info_musica_atual() == esperado


def test_capa_cache_evitar_repetir_rede(monkeypatch):
    buscar = MagicMock(return_value=b"imagem")
    monkeypatch.setattr(media_info, "_buscar_capa_itunes", buscar)
    assert media_info._buscar_capa_com_cache("Artista", "Faixa") == b"imagem"
    assert media_info._buscar_capa_com_cache("ARTISTA", "FAIXA") == b"imagem"
    buscar.assert_called_once()


def test_busca_capa_http_e_resolucao(monkeypatch):
    respostas = [io.BytesIO(json.dumps({"results": [{"artworkUrl100": "https://teste.invalid/100x100bb.jpg"}]}).encode()), io.BytesIO(b"imagem")]
    rede = MagicMock(side_effect=respostas)
    monkeypatch.setattr(media_info.urllib.request, "urlopen", rede)
    assert media_info._buscar_capa_itunes("Artista", "Faixa") == b"imagem"
    assert "Artista%20Faixa" in rede.call_args_list[0].args[0].full_url
    assert rede.call_args_list[1].args[0].full_url == "https://teste.invalid/600x600bb.jpg"


@pytest.mark.parametrize("resposta", [b'{"results":[]}', b'{"results":[{}]}', b'invalido'])
def test_capa_indisponivel_nao_quebra(monkeypatch, resposta):
    monkeypatch.setattr(media_info.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(resposta))
    assert media_info._buscar_capa_itunes("Artista", "Faixa") is None


def test_poller_real_emite_e_encerra(qtbot, monkeypatch):
    monkeypatch.setattr(media_info, "obter_info_musica_atual", lambda: None)
    worker = MediaInfoPoller(intervalo=0.02)
    try:
        with qtbot.waitSignal(worker.atualizado, timeout=5000) as resultado:
            worker.start()
        assert resultado.args == [None]
    finally:
        worker.parar()
        assert worker.wait(5000)
