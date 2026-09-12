from unittest.mock import MagicMock

from ui import updater
from ui.updater_worker import UpdaterWorker


def test_falha_ao_iniciar_update_preserva_executaveis(qtbot, monkeypatch, tmp_path):
    atual = tmp_path / "assistente.exe"
    novo = tmp_path / "novo.exe"
    atual.write_bytes(b"versao atual simulada")
    novo.write_bytes(b"nova versao simulada")
    monkeypatch.setattr(updater, "executavel_atual", lambda: str(atual))
    monkeypatch.setattr(updater, "baixar_atualizacao", lambda *a, **k: str(novo))
    monkeypatch.setattr(updater.subprocess, "Popen", MagicMock(side_effect=OSError("sem permissao")))
    worker = UpdaterWorker("baixar", "https://teste.invalid/novo.exe")
    try:
        with qtbot.waitSignal(worker.concluido, timeout=5000) as resultado:
            worker.start()
        assert resultado.args[0] is False
        assert "sem permissao" in resultado.args[1]
        assert atual.read_bytes() == b"versao atual simulada"
        assert novo.read_bytes() == b"nova versao simulada"
    finally:
        assert worker.wait(5000)


def test_pagina_update_falha_reabilita_controles(qtbot, desktop_simulado):
    from ui.pages.system_page import SystemPage
    page = SystemPage()
    qtbot.addWidget(page)
    page.btn_verificar_update.setEnabled(False)
    page.barra_progresso.show()
    page._ao_concluir(False, "Download falhou")
    assert page.btn_verificar_update.isEnabled()
    assert page.barra_progresso.isHidden()
    assert page.status_update.text() == "Download falhou"


def test_pagina_musica_informa_volume_indisponivel(qtbot, monkeypatch, desktop_simulado):
    from ui import audio_control
    from ui.pages.music_page import MusicPage
    monkeypatch.setattr(audio_control, "_obter_interface_volume", MagicMock(side_effect=OSError("sem dispositivo")))
    page = MusicPage()
    qtbot.addWidget(page)
    try:
        assert "indisponível" in page.label_volume.text()
        page._alterar_volume(10)
        assert "sem dispositivo" in page.status.text()
        page._atualizar_agora_tocando({"titulo": "Faixa", "artista": "Artista", "capa": b"imagem invalida"})
        assert page.label_titulo_musica.text() == "Faixa"
        assert page.label_artista.text() == "Artista"
        assert page.label_capa.text() == "🎵"
    finally:
        page._poller.parar()
        assert page._poller.wait(5000)
