"""
Integração com o Ollama (https://ollama.com) — motor de IA local e
gratuito. Sem chave de API, sem custo, sem internet depois de baixado
o modelo. Esse módulo cuida de: detectar se está instalado/rodando,
baixar/instalar, baixar um modelo, e conversar com ele.

O Ollama em si (o programa) não pode vir embutido no nosso .exe — ele
e os modelos pesam de centenas de MB a alguns GB. Em vez de pedir pra
pessoa mexer em terminal, guiamos tudo pela interface (ver
ui/pages/ai_page.py).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path

URL_BASE = "http://localhost:11434"
URL_INSTALADOR_WINDOWS = "https://ollama.com/download/OllamaSetup.exe"

MODELO_PADRAO = "llama3.2:1b"  # pequeno e rápido, roda bem até em PC mais fraco


def ollama_esta_instalado() -> bool:
    """Confere se o executável do Ollama existe no PATH ou no local
    padrão de instalação (%LOCALAPPDATA%\\Programs\\Ollama)."""
    if shutil.which("ollama"):
        return True

    caminho_padrao = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
    return caminho_padrao.exists()


def ollama_esta_rodando() -> bool:
    """O Ollama expõe um servidor local na porta 11434 quando está de
    pé. Confere isso com uma requisição rápida."""
    try:
        with urllib.request.urlopen(f"{URL_BASE}/api/tags", timeout=2):
            return True
    except Exception:
        return False


def iniciar_ollama() -> bool:
    """Tenta iniciar o serviço do Ollama em segundo plano (ele roda
    como um servidor local, sem janela). Devolve True se conseguiu
    disparar o processo (não garante que já subiu — chame
    ollama_esta_rodando() depois de um instante pra confirmar)."""
    caminho = shutil.which("ollama")
    if not caminho:
        caminho_padrao = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
        if caminho_padrao.exists():
            caminho = str(caminho_padrao)

    if not caminho:
        return False

    try:
        subprocess.Popen(
            [caminho, "serve"],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return True
    except Exception:
        return False


def baixar_instalador(progresso=None) -> str | None:
    """Baixa o instalador oficial do Ollama pro Windows. Devolve o
    caminho do arquivo baixado, ou None se falhar."""
    try:
        destino = Path(tempfile.gettempdir()) / "OllamaSetup.exe"
        requisicao = urllib.request.Request(
            URL_INSTALADOR_WINDOWS, headers={"User-Agent": "AssistenteVirtualIkuromimy"}
        )
        with urllib.request.urlopen(requisicao, timeout=30) as resposta:
            total = int(resposta.headers.get("Content-Length", 0))
            baixado = 0
            with open(destino, "wb") as arquivo:
                while True:
                    bloco = resposta.read(65536)
                    if not bloco:
                        break
                    arquivo.write(bloco)
                    baixado += len(bloco)
                    if progresso:
                        progresso(baixado, total)
        return str(destino)
    except Exception:
        return None


def executar_instalador(caminho_instalador: str) -> bool:
    """Abre o instalador do Ollama (janela normal — a pessoa clica
    'Instalar' como qualquer programa; não arriscamos instalação
    silenciosa sem confirmar os parâmetros certos)."""
    try:
        os.startfile(caminho_instalador)
        return True
    except Exception:
        return False


def listar_modelos_instalados() -> list[str]:
    try:
        with urllib.request.urlopen(f"{URL_BASE}/api/tags", timeout=5) as resposta:
            dados = json.loads(resposta.read().decode("utf-8"))
        return [m.get("name", "") for m in dados.get("models", [])]
    except Exception:
        return []


def baixar_modelo(nome_modelo: str, progresso=None) -> bool:
    """Manda o Ollama baixar um modelo (ex: 'llama3.2:1b'). Isso pode
    demorar bastante (o modelo tem uns 1-2GB). 'progresso', se
    passado, é chamado com (status_texto, completado, total) a cada
    atualização que o Ollama manda."""
    try:
        corpo = json.dumps({"name": nome_modelo, "stream": True}).encode("utf-8")
        requisicao = urllib.request.Request(
            f"{URL_BASE}/api/pull", data=corpo, method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(requisicao, timeout=None) as resposta:
            for linha in resposta:
                if not linha.strip():
                    continue
                evento = json.loads(linha.decode("utf-8"))
                status = evento.get("status", "")
                completado = evento.get("completed", 0)
                total = evento.get("total", 0)
                if progresso:
                    progresso(status, completado, total)
                if evento.get("error"):
                    return False
        return True
    except Exception:
        return False


def enviar_mensagem(modelo: str, mensagens: list[dict], on_chunk=None) -> str:
    """Manda o histórico de mensagens (formato [{'role': 'user'|
    'assistant'|'system', 'content': '...'}]) pro modelo e devolve a
    resposta completa. 'on_chunk', se passado, é chamado com cada
    pedacinho de texto assim que chega (efeito "digitando")."""
    corpo = json.dumps({"model": modelo, "messages": mensagens, "stream": True}).encode("utf-8")
    requisicao = urllib.request.Request(
        f"{URL_BASE}/api/chat", data=corpo, method="POST",
        headers={"Content-Type": "application/json"},
    )

    texto_completo = ""
    with urllib.request.urlopen(requisicao, timeout=None) as resposta:
        for linha in resposta:
            if not linha.strip():
                continue
            evento = json.loads(linha.decode("utf-8"))
            pedaco = evento.get("message", {}).get("content", "")
            if pedaco:
                texto_completo += pedaco
                if on_chunk:
                    on_chunk(pedaco)
            if evento.get("done"):
                break

    return texto_completo
