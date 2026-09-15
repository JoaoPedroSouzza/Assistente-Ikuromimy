"""
Escravo - Assistente de comandos por voz/texto
------------------------------------------------
Versão revisada: mais robusta, com tratamento de erros, comando de
fechar programas, correspondência por palavra inteira (evita falsos
positivos), melhor organização do código, e agora com abertura de
QUALQUER executável instalado no PC (via índice de atalhos do Menu
Iniciar + registro "App Paths" do Windows). Play/pause/próxima/anterior
usam as teclas de mídia do sistema (pyautogui), como no script original.
"""

from __future__ import annotations

import os
import re
from core.comandos import PALAVRAS_CHAVE_CONHECIDAS as PALAVRAS_CHAVE_CONHECIDAS
from core.comandos import _tentar_corrigir_comando as _tentar_corrigir_comando
from core.comandos import contem_palavra as contem_palavra
from core.comandos import eh_comando_conhecido as eh_comando_conhecido
from core.comandos import extrair_alvo as extrair_alvo
import tempfile
import time
import uuid
import subprocess
import shutil
import webbrowser
import urllib.parse
from pathlib import Path

import pyautogui
import psutil
from gtts import gTTS
from playsound import playsound
from core.visual_events import publish

try:
    import win32gui
    import win32process
    import win32con
    import win32com.client
    PYWIN32_DISPONIVEL = True
except ImportError:
    PYWIN32_DISPONIVEL = False

try:
    import winreg
    WINREG_DISPONIVEL = True
except ImportError:
    WINREG_DISPONIVEL = False


# ---------------------------------------------------------------------------
# CONFIGURAÇÃO
# ---------------------------------------------------------------------------

VOZ_ATIVA = True          # coloque False se quiser respostas só em texto (mais rápido)
IDIOMA_VOZ = "pt"
ESPERA_BUSCA_SPOTIFY = 3.5  # segundos até apertar Enter após abrir a busca (modo navegador)

MODO_SPOTIFY = "app"      # "app" = busca dentro do app desktop | "navegador" = abre no browser
ESPERA_FOCO_APP = 2.5       # segundos até começar a procurar a janela do Spotify
ESPERA_APOS_FOCO = 2.0      # segundos após confirmar o foco, antes de mandar Ctrl+K (dá tempo da UI carregar)
ESPERA_APOS_CTRL_K = 0.8    # segundos após abrir a busca, antes de colar o texto
ESPERA_DROPDOWN_APP = 1.5   # segundos até o dropdown de resultados aparecer, no app
ESPERA_APOS_SELECIONAR = 1.0  # segundos após dar Enter na música, antes de garantir o play

# Motor de busca padrão usado pelo comando "pesquisar"
MOTOR_BUSCA_PADRAO = "google"  # "google" | "bing" | "duckduckgo" | "youtube"

URLS_BUSCA = {
    "google": "https://www.google.com/search?q={q}",
    "bing": "https://www.bing.com/search?q={q}",
    "duckduckgo": "https://duckduckgo.com/?q={q}",
    "youtube": "https://www.youtube.com/results?search_query={q}",
}

# Nomes de processo (para fechar) — o valor deve bater com o que aparece no Gerenciador de Tarefas
# Continua existindo para os apps mais comuns; pra fechar outros, dá pra
# usar o nome do processo direto (ex: "fechar chrome.exe").
PROCESSOS_APPS = {
    "bloco": "notepad.exe",
    "notas": "notepad.exe",
    "chrome": "chrome.exe",
    "spotify": "Spotify.exe",
}

TEMP_DIR = Path(tempfile.gettempdir())


# ---------------------------------------------------------------------------
# CONTROLE DE MÍDIA (teclas de mídia do sistema)
# ---------------------------------------------------------------------------

def media_play_pause() -> None:
    try:
        pyautogui.press("playpause")
    except Exception as e:
        print(f"⚠️ Não consegui enviar play/pause: {e}")


def media_next() -> None:
    try:
        pyautogui.press("nexttrack")
    except Exception as e:
        print(f"⚠️ Não consegui pular a faixa: {e}")


def media_prev() -> None:
    try:
        pyautogui.press("prevtrack")
    except Exception as e:
        print(f"⚠️ Não consegui voltar a faixa: {e}")


# ---------------------------------------------------------------------------
# FALA (TEXT-TO-SPEECH)
# ---------------------------------------------------------------------------

def falar(texto: str) -> None:
    """Fala o texto em voz alta. Nunca derruba o programa se falhar
    (ex.: sem internet para o gTTS, ou player indisponível)."""
    print(f"🤖 Thiago: {texto}")

    if not VOZ_ATIVA:
        return

    arquivo = TEMP_DIR / f"temp_{uuid.uuid4().hex}.mp3"
    try:
        tts = gTTS(text=texto, lang=IDIOMA_VOZ, slow=False)
        tts.save(str(arquivo))
        publish("speech_source", str(arquivo))
        publish("speaking", True)
        playsound(str(arquivo))
    except Exception as e:
        print(f"⚠️  Não consegui falar ({e}). Seguindo só com texto.")
    finally:
        publish("speaking", False)
        if arquivo.exists():
            try:
                arquivo.unlink()
            except OSError:
                pass


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------





def fechar_processo(nome_exe: str) -> bool:
    """Tenta fechar todos os processos com o nome dado. Retorna True se
    encontrou e fechou pelo menos um."""
    encontrado = False
    for proc in psutil.process_iter(["name"]):
        try:
            if proc.info["name"] and proc.info["name"].lower() == nome_exe.lower():
                proc.terminate()
                encontrado = True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return encontrado


# ---------------------------------------------------------------------------
# ÍNDICE DE APLICATIVOS INSTALADOS (para "abrir <qualquer coisa>")
# ---------------------------------------------------------------------------
#
# Estratégia: em vez de cadastrar caminho por caminho, montamos um índice
# nome -> caminho do .exe olhando em dois lugares que o Windows já usa:
#
#  1. Registro "App Paths" (HKLM/HKCU ...CurrentVersion\App Paths):
#     é onde a maioria dos instaladores registra o executável principal.
#  2. Atalhos (.lnk) do Menu Iniciar (todos os usuários + usuário atual):
#     cobre praticamente tudo que aparece quando você abre o Menu Iniciar
#     e digita o nome do programa.
#
# O índice é montado uma vez (cache em memória) e reaproveitado. Use o
# comando "atualizar apps" se instalar algo novo durante a sessão.

_CACHE_APPS: dict[str, Path] = {}
_CACHE_CARREGADO = False


def _indexar_atalhos(pasta: Path, indice: dict[str, Path]) -> None:
    """Varre uma pasta (recursivamente) atrás de atalhos .lnk e resolve
    o executável alvo de cada um, guardando nome_do_atalho -> caminho."""
    if not PYWIN32_DISPONIVEL or not pasta.exists():
        return

    try:
        shell = win32com.client.Dispatch("WScript.Shell")
    except Exception:
        return

    for lnk in pasta.rglob("*.lnk"):
        try:
            atalho = shell.CreateShortcut(str(lnk))
            alvo = atalho.Targetpath
            if alvo and alvo.lower().endswith(".exe") and Path(alvo).exists():
                nome = lnk.stem.lower()
                indice.setdefault(nome, Path(alvo))
        except Exception:
            continue


def _indexar_app_paths(indice: dict[str, Path]) -> None:
    """Lê o registro do Windows em busca de executáveis registrados por
    instaladores (chave 'App Paths')."""
    if not WINREG_DISPONIVEL:
        return

    raizes = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
    ]
    for hive, caminho in raizes:
        try:
            with winreg.OpenKey(hive, caminho) as chave:
                i = 0
                while True:
                    try:
                        subnome = winreg.EnumKey(chave, i)
                    except OSError:
                        break
                    i += 1
                    try:
                        with winreg.OpenKey(chave, subnome) as subchave:
                            valor, _ = winreg.QueryValueEx(subchave, "")
                            if valor and Path(valor).exists():
                                nome = Path(subnome).stem.lower()
                                indice.setdefault(nome, Path(valor))
                    except OSError:
                        continue
        except OSError:
            continue


def _construir_indice_apps() -> dict[str, Path]:
    indice: dict[str, Path] = {}

    _indexar_app_paths(indice)

    pastas_atalhos = [
        Path(os.environ.get("ProgramData", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
        Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
        # área de trabalho também costuma ter atalhos de apps instalados
        Path(os.environ.get("USERPROFILE", "")) / "Desktop",
        Path(r"C:\Users\Public\Desktop"),
    ]
    for pasta in pastas_atalhos:
        _indexar_atalhos(pasta, indice)

    return indice


def _carregar_cache_apps(forcar: bool = False) -> dict[str, Path]:
    global _CACHE_CARREGADO
    if forcar or not _CACHE_CARREGADO:
        print("🔎 Indexando aplicativos instalados (pode levar alguns segundos)...")
        _CACHE_APPS.clear()
        _CACHE_APPS.update(_construir_indice_apps())
        _CACHE_CARREGADO = True
        print(f"✅ {len(_CACHE_APPS)} aplicativos encontrados.")
    return _CACHE_APPS


def encontrar_executavel_generico(nome_app: str) -> Path | None:
    """Tenta achar o .exe de QUALQUER app instalado a partir de um nome
    falado/digitado. Ordem de tentativa:

      1. Se já veio um caminho completo pra um .exe existente, usa direto.
      2. Correspondência exata no índice (atalhos + App Paths).
      3. Correspondência parcial (nome falado contido no nome indexado,
         ou vice-versa) — pega o candidato com nome mais curto/parecido.
    """
    nome_app = nome_app.strip().strip('"').strip("'")
    if not nome_app:
        return None

    # 1. Caminho completo já informado (ex: "abrir C:\Jogos\game.exe")
    if nome_app.lower().endswith(".exe"):
        p = Path(nome_app)
        if p.exists():
            return p

    indice = _carregar_cache_apps()
    nome_busca = nome_app.lower()

    # 2. correspondência exata
    if nome_busca in indice:
        return indice[nome_busca]

    # 3. correspondência parcial nos dois sentidos
    candidatos = [
        nome for nome in indice
        if nome_busca in nome or nome in nome_busca
    ]
    if candidatos:
        # prioriza o nome mais curto (tende a ser o match mais "direto")
        candidatos.sort(key=len)
        return indice[candidatos[0]]

    return None


# ---------------------------------------------------------------------------
# LINKS DE PROTOCOLO (steam://, epicgames://, battlenet://, etc.)
# ---------------------------------------------------------------------------
#
# Coisas como "steam://rungameid/431960" não são um arquivo .exe — são uma
# URI de protocolo customizado. O Windows já sabe, pelo registro, qual app
# deve tratar cada protocolo (ex: "steam://" abre via Steam), então basta
# "executar" a URI como se fosse um link, sem precisar achar caminho de
# arquivo nenhum.

# Nome falado -> appid da Steam. Adicione os seus jogos aqui.
JOGOS_STEAM = {
    "cs2": "730",
    "counter strike": "730",
    "counter-strike": "730",
    "wallpaper": "431960",
    
}

# Prefixos de protocolo de outros launchers, caso queira mapear jogos deles
# do mesmo jeito (ex: JOGOS_EPIC = {"fortnite": "com.epicgames.launcher://apps/fortnite?action=launch"})
JOGOS_EPIC: dict[str, str] = {}
JOGOS_BATTLENET: dict[str, str] = {}


def abrir_link_protocolo(uri: str) -> bool:
    """Abre uma URI de protocolo customizado (steam://, epicgames://,
    battlenet://, riotclient://, origin://, uplay://, etc.). O Windows
    resolve automaticamente pro app dono daquele protocolo."""
    esquema = urllib.parse.urlsplit(uri).scheme.lower()
    if esquema not in {"steam", "epicgames", "battlenet", "riotclient", "origin", "uplay", "spotify", "https", "http"}:
        return False
    try:
        os.startfile(uri)
        return True
    except Exception:
        pass
    try:
        webbrowser.open(uri)
        return True
    except Exception as e:
        print(f"Erro ao abrir link {uri}: {e}")
        return False


def _buscar_em_dicionario_jogos(nome: str, dicionario: dict[str, str]) -> str | None:
    nome = nome.lower().strip()
    if nome in dicionario:
        return dicionario[nome]
    candidatos = [k for k in dicionario if nome in k or k in nome]
    if candidatos:
        candidatos.sort(key=len)
        return dicionario[candidatos[0]]
    return None


def resolver_link_de_jogo(nome: str) -> str | None:
    """Tenta transformar um nome de jogo falado num link de protocolo
    pronto pra abrir (Steam, Epic, Battle.net...)."""
    appid = _buscar_em_dicionario_jogos(nome, JOGOS_STEAM)
    if appid:
        return f"steam://rungameid/{appid}"

    link_epic = _buscar_em_dicionario_jogos(nome, JOGOS_EPIC)
    if link_epic:
        return link_epic

    link_bnet = _buscar_em_dicionario_jogos(nome, JOGOS_BATTLENET)
    if link_bnet:
        return link_bnet

    return None


# ---------------------------------------------------------------------------
# AÇÕES
# ---------------------------------------------------------------------------

def encontrar_executavel_spotify() -> Path | None:
    """Procura o Spotify.exe nos locais padrão de instalação no Windows."""
    candidatos = [
        Path(os.environ.get("APPDATA", "")) / "Spotify" / "Spotify.exe",
        Path(r"C:\Program Files\Spotify\Spotify.exe"),
        Path(r"C:\Program Files (x86)\Spotify\Spotify.exe"),
    ]
    for c in candidatos:
        if c.exists():
            return c
    return None


def _janelas_do_processo(nome_exe: str) -> list[int]:
    """Retorna os HWNDs de janelas visíveis e com título pertencentes a um
    processo com o nome dado. Diferente de buscar por texto no título,
    isso não quebra quando o Spotify troca o título da janela para
    'Artista - Música' enquanto toca algo."""
    hwnds: list[int] = []

    def callback(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd) or not win32gui.GetWindowText(hwnd):
            return True
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc = psutil.Process(pid)
            if proc.name().lower() == nome_exe.lower():
                hwnds.append(hwnd)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        return True

    win32gui.EnumWindows(callback, None)
    return hwnds


def focar_janela_spotify(tentativas: int = 8, intervalo: float = 0.5) -> bool:
    """Abre (ou traz pra frente) a janela do app desktop do Spotify e SÓ
    retorna True se confirmar que ela está mesmo em primeiro plano.
    Identifica a janela pelo processo dono (Spotify.exe), não pelo texto
    do título — o título muda para 'Artista - Música' quando toca algo."""

    if not PYWIN32_DISPONIVEL:
        print("⚠️ Instale 'pywin32' (pip install pywin32) para eu "
              "conseguir confirmar o foco no Spotify antes de digitar. Sem "
              "isso, por segurança, não vou enviar comandos de teclado.")
        return False

    ja_aberto = bool(_janelas_do_processo("Spotify.exe"))

    exe = encontrar_executavel_spotify()
    if not ja_aberto:
        try:
            if exe:
                subprocess.Popen([str(exe)])
            else:
                # fallback via protocolo — sintaxe correta do "start" precisa
                # de um título (mesmo vazio) antes do alvo entre aspas
                subprocess.Popen(["cmd", "/c", "start", "", "spotify:"], shell=False)
                print("⚠️ Spotify.exe não encontrado nos caminhos padrão. Usando "
                      "'spotify:' via protocolo — se isso abrir o navegador em vez "
                      "do app, o Spotify desktop pode não estar instalado/registrado.")
        except Exception as e:
            print(f"⚠️ Não consegui iniciar o Spotify: {e}")
            return False
        time.sleep(ESPERA_FOCO_APP)
    else:
        print("ℹ️ Spotify já estava aberto, só vou trazer a janela pra frente.")

    for _ in range(tentativas):
        hwnds = _janelas_do_processo("Spotify.exe")
        if hwnds:
            hwnd = hwnds[0]
            try:
                if win32gui.IsIconic(hwnd):
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

                # O Windows bloqueia SetForegroundWindow vindo de um processo
                # que não está em primeiro plano ("foreground lock"). Simular
                # um Alt "vazio" antes costuma contornar essa proteção.
                try:
                    win32com.client.Dispatch("WScript.Shell").SendKeys("%")
                except Exception:
                    pass

                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.4)

                pid_ativo = win32process.GetWindowThreadProcessId(win32gui.GetForegroundWindow())[1]
                if psutil.Process(pid_ativo).name().lower() == "spotify.exe":
                    return True
            except Exception:
                pass
        time.sleep(intervalo)

    return False


def buscar_no_app_spotify(alvo: str) -> None:
    """Busca uma música dentro do app desktop do Spotify usando atalhos de
    teclado: Ctrl+K abre a busca, cola o texto e navega no dropdown de
    resultados. É automação de UI — pode precisar ajustar os tempos de
    espera dependendo da velocidade da sua máquina."""

    if not focar_janela_spotify():
        falar("Não consegui confirmar que o Spotify está em primeiro plano, "
              "então não vou mandar comandos de teclado pra não bagunçar outra janela.")
        print("Dica: abra o Spotify manualmente antes de usar o comando 'tocar', "
              "ou confira se 'pygetwindow' está instalado.")
        return

    # A janela pode reportar foco antes da UI interna do Spotify estar
    # realmente pronta pra receber atalhos — por isso essa espera extra.
    print(f"✅ Spotify focado. Aguardando {ESPERA_APOS_FOCO}s antes de digitar...")
    time.sleep(ESPERA_APOS_FOCO)

    try:
        pyautogui.hotkey("ctrl", "k")
        time.sleep(ESPERA_APOS_CTRL_K)
        time.sleep(0.6)

        try:
            import pyperclip
            pyperclip.copy(alvo)
            pyautogui.hotkey("ctrl", "v")
        except ImportError:
            print("⚠️ Instale 'pyperclip' (pip install pyperclip) pra digitar "
                  "acentos/ç corretamente. Usando modo de digitação simples.")
            pyautogui.write(alvo, interval=0.03)

        time.sleep(ESPERA_DROPDOWN_APP)
        # O Spotify já deixa o PRIMEIRO resultado do dropdown destacado
        # assim que a busca aparece — por isso NÃO mandamos "down" aqui.
        # Um "down" extra pularia pro segundo item da lista (era o bug).
        pyautogui.press("enter")  # seleciona/toca o item já destacado

        # O Enter geralmente só ABRE a página da música/álbum, sem
        # necessariamente começar a tocar sozinho. Garantimos o play
        # explicitamente logo em seguida — como nesse momento o Spotify
        # normalmente ainda está parado (acabou de abrir/focar/navegar),
        # isso já inicia a reprodução na prática.
        time.sleep(ESPERA_APOS_SELECIONAR)
        media_play_pause()
    except Exception as e:
        falar("Não consegui buscar dentro do app do Spotify.")
        print(f"Erro: {e}")


def buscar_no_navegador_spotify(alvo: str) -> None:
    try:
        webbrowser.open(f"https://open.spotify.com/search/{alvo.replace(' ', '%20')}")
        time.sleep(ESPERA_BUSCA_SPOTIFY)
        pyautogui.press("enter")
    except Exception as e:
        falar("Não consegui abrir o Spotify no navegador.")
        print(f"Erro: {e}")


def acao_tocar_musica(alvo: str) -> None:
    if not alvo:
        falar("Você não disse o nome da música.")
        return
    falar(f"Buscando {alvo} no Spotify")

    if MODO_SPOTIFY == "app":
        buscar_no_app_spotify(alvo)
    else:
        buscar_no_navegador_spotify(alvo)


def acao_pesquisar(termo: str, motor: str = MOTOR_BUSCA_PADRAO) -> None:
    """Abre o navegador padrão já pesquisando o termo no motor de busca
    escolhido (Google por padrão). Detecta se o próprio termo começa com
    o nome de outro motor (ex: 'pesquisar no youtube gatinhos') e usa
    esse motor em vez do padrão."""
    if not termo:
        falar("Pesquisar o quê?")
        return

    termo = termo.strip()

    # Permite trocar de motor dentro do próprio comando, ex:
    # "pesquisar no youtube receita de bolo" ou "pesquisar no bing clima"
    m = re.match(r"^(?:no|na)\s+(google|bing|duckduckgo|duck duck go|youtube)\s+(.+)$", termo)
    if m:
        motor_falado = m.group(1).replace("duck duck go", "duckduckgo")
        if motor_falado in URLS_BUSCA:
            motor = motor_falado
            termo = m.group(2).strip()

    if not termo:
        falar("Pesquisar o quê?")
        return

    falar(f"Pesquisando {termo}")
    try:
        query = urllib.parse.quote_plus(termo)
        url_base = URLS_BUSCA.get(motor, URLS_BUSCA[MOTOR_BUSCA_PADRAO])
        webbrowser.open(url_base.format(q=query))
    except Exception as e:
        falar("Não consegui abrir a pesquisa.")
        print(f"Erro: {e}")


def acao_abrir(app: str) -> None:
    """Abre qualquer aplicativo instalado no PC.

    Ordem de tentativa:
      1. Casos especiais mais rápidos/confiáveis (bloco de notas).
      2. Índice de apps (atalhos do Menu Iniciar + registro App Paths) —
         cobre a esmagadora maioria dos programas instalados.
      3. Fallback via 'start', deixando o Windows tentar resolver (funciona
         pra apps que estão no PATH, ex.: "code", "python", "explorer").
    """
    if not app:
        falar("Abrir o quê?")
        return

    if contem_palavra(app, "bloco", "notas"):
        falar(f"Abrindo {app}")
        os.startfile("notepad.exe")
        return

    # 1. Já é um link de protocolo pronto (ex: "steam://rungameid/431960")
    if "://" in app:
        falar(f"Abrindo {app}")
        if not abrir_link_protocolo(app):
            falar("Não consegui abrir esse link.")
        return

    falar(f"Abrindo {app}")
    try:
        # 2. Nome de jogo mapeado (Steam/Epic/Battle.net) -> vira link de protocolo
        link_jogo = resolver_link_de_jogo(app)
        if link_jogo:
            if not abrir_link_protocolo(link_jogo):
                falar("Não consegui abrir o jogo.")
            return

        # 3. Índice de apps (atalhos + registro)
        exe = encontrar_executavel_generico(app)
        if exe:
            os.startfile(str(exe))
            return

        # 4. Resolve executáveis do PATH sem interpretar texto como shell.
        caminho_path = shutil.which(app)
        if caminho_path:
            os.startfile(caminho_path)
            return

        falar(f"Não encontrei o app {app} no seu PC.")
        print("Dica: fale 'atualizar apps' se você acabou de instalar algo novo, "
              "ou tente o nome exatamente como aparece no Menu Iniciar.")
    except Exception as e:
        falar(f"Deu erro ao abrir {app}.")
        print(f"Erro: {e}")


def acao_fechar(app: str) -> None:
    if not app:
        falar("Fechar o quê?")
        return

    nome_exe = None
    for chave, exe in PROCESSOS_APPS.items():
        if chave in app:
            nome_exe = exe
            break

    # permite fechar também pelo nome exato do processo (ex: "fechar chrome.exe")
    if not nome_exe and app.lower().endswith(".exe"):
        nome_exe = app

    if not nome_exe:
        falar(f"Não sei qual processo fechar para {app}.")
        return

    if fechar_processo(nome_exe):
        falar(f"Fechando {app}")
    else:
        falar(f"{app} não parece estar aberto.")


# ---------------------------------------------------------------------------
# LOOP PRINCIPAL
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# AUTOCOMPLETAR / AUTOCORREÇÃO DE COMANDOS
# ---------------------------------------------------------------------------

# Todas as palavras-gatilho que o processar_comando reconhece. Usado
# tanto pra sugestão (autocompletar na interface) quanto pra tentar
# corrigir erro de digitação na primeira palavra do comando.


def listar_apps_conhecidos() -> list[str]:
    """Devolve os nomes dos apps já indexados (atalhos do Menu Iniciar
    + registro do Windows) — útil pra sugestão/autocompletar na
    interface, ex: sugerir 'abrir spotify' enquanto o usuário digita."""
    return sorted(_carregar_cache_apps().keys())






def processar_comando(comando: str, permitir_correcao: bool = True) -> bool:
    """Processa um comando. Retorna False se o programa deve encerrar."""

    comando = comando.lower().strip()
    if not comando:
        return True

    # Buscar/tocar música (prioridade alta, tem argumento livre)
    m = re.match(r"^tocar\s+(.+)", comando)
    if m:
        acao_tocar_musica(m.group(1).strip())
        return True

    # Pesquisar algo no navegador (prioridade alta, argumento livre)
    # aceita "pesquisar", "pesquisa" e "buscar" como sinônimos
    m = re.match(r"^(?:pesquisar|pesquisa|buscar)\s+(.+)", comando)
    if m:
        acao_pesquisar(m.group(1).strip())
        return True

    if contem_palavra(comando, "atualizar") and "apps" in comando:
        _carregar_cache_apps(forcar=True)
        falar("Lista de aplicativos atualizada.")
        return True

    if contem_palavra(comando, "abrir", "abre"):
        alvo = extrair_alvo(comando, "abrir", "abre")
        acao_abrir(alvo)
        return True

    if contem_palavra(comando, "fechar", "fecha"):
        alvo = extrair_alvo(comando, "fechar", "fecha")
        acao_fechar(alvo)
        return True

    if contem_palavra(comando, "play", "pause", "pausar"):
        falar("Play / Pause")
        media_play_pause()
        return True

    if contem_palavra(comando, "próxima", "proxima", "pula", "next"):
        falar("Próxima faixa")
        media_next()
        return True

    if contem_palavra(comando, "anterior", "voltar"):
        falar("Faixa anterior")
        media_prev()
        return True

    if contem_palavra(comando, "aumentar", "sobe") and "volume" in comando:
        pyautogui.press("volumeup")
        return True

    if contem_palavra(comando, "diminuir", "abaixa") and "volume" in comando:
        pyautogui.press("volumedown")
        return True

    if contem_palavra(comando, "loop", "repetir"):
        falar("Tentando loop")
        pyautogui.hotkey("ctrl", "l")
        return True

    if contem_palavra(comando, "para", "sair", "encerrar"):
        falar("Tchau!")
        return False

    if permitir_correcao:
        corrigido = _tentar_corrigir_comando(comando)
        if corrigido and corrigido != comando:
            falar(f'Não entendi "{comando}", tentando como "{corrigido}"...')
            return processar_comando(corrigido, permitir_correcao=False)

    falar("Não entendi o comando.")
    return True


def main():
    print("🚀 Escravo corrigido - Testa ai'")
    # monta o índice de apps já no início, pra "abrir" não travar na primeira vez
    _carregar_cache_apps()
    try:
        while True:
            comando = input("\nComando: ")
            continuar = processar_comando(comando)
            if not continuar:
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n👋 Encerrado pelo usuário (Ctrl+C).")


if __name__ == "__main__":
    main()
