"""
Descobre qual música está tocando no momento lendo o título da janela
do Spotify — que fica no formato "Artista - Faixa" enquanto toca algo,
e só "Spotify" quando está parado.

A capa do álbum vem da API pública de busca da Apple (iTunes Search):
gratuita, sem chave de API, sem cadastro, sem login — funciona pra
qualquer pessoa que baixar o app, sem nenhum setup. A busca é por
texto (artista + música), então ocasionalmente pode trazer a capa de
uma versão/cover diferente da que está tocando de verdade, mas pra
faixas conhecidas costuma acertar.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request

import psutil

try:
    import win32gui
    import win32process
    PYWIN32_DISPONIVEL = True
except ImportError:
    PYWIN32_DISPONIVEL = False

_USER_AGENT = "AssistenteVirtualIkuromimy"

# cache simples em memória: evita rebuscar a mesma capa a cada
# consulta do poller (a cada poucos segundos, enquanto a mesma música
# continua tocando)
_cache_capa: dict[str, bytes | None] = {}


def _titulo_janela_spotify() -> str | None:
    if not PYWIN32_DISPONIVEL:
        return None

    titulo_encontrado = None

    def callback(hwnd, _):
        nonlocal titulo_encontrado
        if not win32gui.IsWindowVisible(hwnd):
            return True

        texto = win32gui.GetWindowText(hwnd)
        if not texto:
            return True

        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            processo = psutil.Process(pid)
            if processo.name().lower() == "spotify.exe":
                titulo_encontrado = texto
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        return True

    win32gui.EnumWindows(callback, None)
    return titulo_encontrado


def _buscar_capa_itunes(artista: str, titulo: str) -> bytes | None:
    """Consulta a API pública do iTunes por 'artista + música' e
    devolve os bytes da capa em alta resolução, ou None se não achar
    nada ou a consulta falhar (sem internet, por exemplo)."""
    try:
        termo = urllib.parse.quote(f"{artista} {titulo}".strip())
        url_busca = f"https://itunes.apple.com/search?term={termo}&media=music&limit=1"

        requisicao = urllib.request.Request(url_busca, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(requisicao, timeout=5) as resposta:
            dados = json.loads(resposta.read().decode("utf-8"))

        resultados = dados.get("results", [])
        if not resultados:
            return None

        url_capa = resultados[0].get("artworkUrl100", "")
        if not url_capa:
            return None

        # a URL padrão vem em 100x100 — troca pra uma resolução maior
        url_capa_grande = url_capa.replace("100x100bb", "600x600bb")

        requisicao_imagem = urllib.request.Request(url_capa_grande, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(requisicao_imagem, timeout=5) as resposta_imagem:
            return resposta_imagem.read()
    except Exception:
        return None


def _buscar_capa_com_cache(artista: str, titulo: str) -> bytes | None:
    chave = f"{artista}|{titulo}".lower()

    if chave in _cache_capa:
        return _cache_capa[chave]

    capa = _buscar_capa_itunes(artista, titulo)
    _cache_capa[chave] = capa

    # evita o cache crescer sem limite numa sessão muito longa
    if len(_cache_capa) > 200:
        _cache_capa.clear()

    return capa


def obter_info_musica_atual() -> dict | None:
    """Devolve {titulo, artista, capa (bytes de imagem ou None),
    tocando (bool)} lendo o título da janela do Spotify + buscando a
    capa no iTunes. Devolve None se o Spotify não estiver aberto."""
    titulo_janela = _titulo_janela_spotify()
    if not titulo_janela:
        return None

    if titulo_janela.strip().lower() == "spotify":
        return {"titulo": "", "artista": "", "capa": None, "tocando": False}

    if " - " in titulo_janela:
        artista, titulo = titulo_janela.split(" - ", 1)
    else:
        artista, titulo = "", titulo_janela

    artista = artista.strip()
    titulo = titulo.strip()

    capa = _buscar_capa_com_cache(artista, titulo) if titulo else None

    return {
        "titulo": titulo,
        "artista": artista,
        "capa": capa,
        "tocando": True,
    }
