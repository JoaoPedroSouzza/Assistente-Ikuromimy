"""
Cliente REST simples pro Firebase (Authentication + Realtime
Database) — fala direto com a API HTTP via urllib, sem biblioteca
nova nenhuma (mesmo padrão que já usamos pro GitHub/Ollama).

Precisa do arquivo ui/firebase_config.py preenchido com os dados do
SEU projeto Firebase (gratuito) — ver firebase_config_exemplo.py pra
instruções de como conseguir esses valores.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

from PySide6.QtCore import QSettings

try:
    from ui.firebase_config import FIREBASE_CONFIG
except ImportError:
    FIREBASE_CONFIG = None

_ORG = "Ikuromimy"
_APP = "AssistenteVirtual"
_CHAVE_SESSAO = "firebase/sessao"

_AUTH_BASE = "https://identitytoolkit.googleapis.com/v1"
_REFRESH_BASE = "https://securetoken.googleapis.com/v1"


def configurado() -> bool:
    return bool(FIREBASE_CONFIG and FIREBASE_CONFIG.get("apiKey") not in (None, "", "COLE_AQUI"))


def _api_key() -> str:
    return FIREBASE_CONFIG["apiKey"]


def _database_url() -> str:
    return FIREBASE_CONFIG["databaseURL"].rstrip("/")


def _post(url: str, corpo: dict) -> dict:
    dados = json.dumps(corpo).encode("utf-8")
    requisicao = urllib.request.Request(
        url, data=dados, method="POST", headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(requisicao, timeout=10) as resposta:
            return json.loads(resposta.read().decode("utf-8"))
    except urllib.error.HTTPError as erro:
        try:
            detalhe = json.loads(erro.read().decode("utf-8"))
            mensagem = detalhe.get("error", {}).get("message", str(erro))
        except Exception:
            mensagem = str(erro)
        raise RuntimeError(_traduzir_erro(mensagem))


def _traduzir_erro(codigo: str) -> str:
    traducoes = {
        "EMAIL_EXISTS": "Esse e-mail já tem uma conta cadastrada.",
        "EMAIL_NOT_FOUND": "Não existe conta com esse e-mail.",
        "INVALID_PASSWORD": "Senha incorreta.",
        "INVALID_LOGIN_CREDENTIALS": "E-mail ou senha incorretos.",
        "WEAK_PASSWORD": "Senha muito curta (mínimo 6 caracteres).",
        "TOO_MANY_ATTEMPTS_TRY_LATER": "Muitas tentativas — espera um pouco e tenta de novo.",
        "INVALID_EMAIL": "E-mail inválido.",
    }
    for chave, traducao in traducoes.items():
        if chave in codigo:
            return traducao
    return codigo


# ---------------------------------------------------------------------------
# sessão (login persistente entre aberturas do app)
# ---------------------------------------------------------------------------

def salvar_sessao(sessao: dict) -> None:
    settings = QSettings(_ORG, _APP)
    settings.setValue(_CHAVE_SESSAO, json.dumps(sessao))


def carregar_sessao() -> dict | None:
    settings = QSettings(_ORG, _APP)
    bruto = settings.value(_CHAVE_SESSAO, "")
    if not bruto:
        return None
    try:
        return json.loads(bruto)
    except (json.JSONDecodeError, TypeError):
        return None


def sair() -> None:
    settings = QSettings(_ORG, _APP)
    settings.remove(_CHAVE_SESSAO)


def _renovar_token(sessao: dict) -> dict:
    resultado = _post(
        f"{_REFRESH_BASE}/token?key={_api_key()}",
        {"grant_type": "refresh_token", "refresh_token": sessao["refreshToken"]},
    )
    nova_sessao = {
        "idToken": resultado["id_token"],
        "refreshToken": resultado["refresh_token"],
        "localId": resultado["user_id"],
        "expiraEm": time.time() + int(resultado["expires_in"]) - 60,
    }
    salvar_sessao(nova_sessao)
    return nova_sessao


def sessao_valida() -> dict | None:
    """Devolve a sessão atual, renovando o token automaticamente se
    estiver perto de expirar. Devolve None se não tiver sessão."""
    sessao = carregar_sessao()
    if not sessao:
        return None

    if time.time() >= sessao.get("expiraEm", 0):
        try:
            sessao = _renovar_token(sessao)
        except Exception:
            return None

    return sessao


# ---------------------------------------------------------------------------
# autenticação
# ---------------------------------------------------------------------------

def cadastrar(email: str, senha: str, nome_usuario: str) -> dict:
    nome_usuario = nome_usuario.strip()
    if not nome_usuario:
        raise RuntimeError("Escolhe um nome de usuário.")

    if buscar_uid_por_nome_usuario(nome_usuario):
        raise RuntimeError("Esse nome de usuário já está em uso.")

    resultado = _post(
        f"{_AUTH_BASE}/accounts:signUp?key={_api_key()}",
        {"email": email, "password": senha, "returnSecureToken": True},
    )

    sessao = {
        "idToken": resultado["idToken"],
        "refreshToken": resultado["refreshToken"],
        "localId": resultado["localId"],
        "expiraEm": time.time() + int(resultado["expiresIn"]) - 60,
    }
    salvar_sessao(sessao)

    uid = sessao["localId"]
    _escrever(f"/perfis/{uid}.json", {"nome_usuario": nome_usuario, "email": email}, sessao["idToken"])
    _escrever(f"/nomes_usuario/{nome_usuario.lower()}.json", uid, sessao["idToken"])

    return sessao


def entrar(email: str, senha: str) -> dict:
    resultado = _post(
        f"{_AUTH_BASE}/accounts:signInWithPassword?key={_api_key()}",
        {"email": email, "password": senha, "returnSecureToken": True},
    )
    sessao = {
        "idToken": resultado["idToken"],
        "refreshToken": resultado["refreshToken"],
        "localId": resultado["localId"],
        "expiraEm": time.time() + int(resultado["expiresIn"]) - 60,
    }
    salvar_sessao(sessao)
    return sessao


# ---------------------------------------------------------------------------
# banco de dados (Realtime Database)
# ---------------------------------------------------------------------------

def _ler(caminho: str, id_token: str) -> dict | None:
    url = f"{_database_url()}{caminho}?auth={id_token}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resposta:
            bruto = resposta.read()
            if not bruto or bruto == b"null":
                return None
            try:
                return json.loads(bruto)
            except json.JSONDecodeError:
                raise RuntimeError(
                    f"Resposta inesperada do Firebase pra '{caminho}' "
                    f"(confere se o caminho termina em .json e se a URL "
                    f"do databaseURL no firebase_config.py está certa)."
                )
    except urllib.error.HTTPError as erro:
        raise RuntimeError(f"Erro ao ler dados: {erro}")


def _escrever(caminho: str, valor, id_token: str, metodo: str = "PUT") -> None:
    url = f"{_database_url()}{caminho}?auth={id_token}"
    dados = json.dumps(valor).encode("utf-8")
    requisicao = urllib.request.Request(url, data=dados, method=metodo)
    try:
        with urllib.request.urlopen(requisicao, timeout=10):
            pass
    except urllib.error.HTTPError as erro:
        raise RuntimeError(f"Erro ao salvar dados: {erro}")


def buscar_uid_por_nome_usuario(nome_usuario: str) -> str | None:
    try:
        url = f"{_database_url()}/nomes_usuario/{nome_usuario.strip().lower()}.json"
        with urllib.request.urlopen(url, timeout=10) as resposta:
            bruto = resposta.read()
            return json.loads(bruto) if bruto and bruto != b"null" else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# presença (status online)
# ---------------------------------------------------------------------------

def atualizar_presenca(online: bool, status_texto: str) -> None:
    sessao = sessao_valida()
    if not sessao:
        return
    uid = sessao["localId"]
    _escrever(
        f"/presenca/{uid}.json",
        {"online": online, "status_texto": status_texto, "atualizado_em": time.time()},
        sessao["idToken"],
    )


def obter_presenca(uid: str, sessao: dict) -> dict | None:
    return _ler(f"/presenca/{uid}.json", sessao["idToken"])


def obter_perfil(uid: str, sessao: dict) -> dict | None:
    return _ler(f"/perfis/{uid}.json", sessao["idToken"])


# ---------------------------------------------------------------------------
# amizades
# ---------------------------------------------------------------------------

def enviar_pedido_amizade(nome_usuario_amigo: str) -> str:
    sessao = sessao_valida()
    if not sessao:
        raise RuntimeError("Você precisa estar logado.")

    uid_amigo = buscar_uid_por_nome_usuario(nome_usuario_amigo)
    if not uid_amigo:
        raise RuntimeError(f'Não achei ninguém com o nome de usuário "{nome_usuario_amigo}".')

    meu_uid = sessao["localId"]
    if uid_amigo == meu_uid:
        raise RuntimeError("Você não pode adicionar a si mesmo.")

    # escrita nos dois lados numa requisição só (multi-path update na raiz)
    atualizacao = {
        f"amizades/{meu_uid}/{uid_amigo}": "pendente_enviado",
        f"amizades/{uid_amigo}/{meu_uid}": "pendente_recebido",
    }
    _escrever("/.json", atualizacao, sessao["idToken"], metodo="PATCH")
    return uid_amigo


def aceitar_pedido(uid_amigo: str) -> None:
    sessao = sessao_valida()
    if not sessao:
        raise RuntimeError("Você precisa estar logado.")
    meu_uid = sessao["localId"]

    atualizacao = {
        f"amizades/{meu_uid}/{uid_amigo}": "aceito",
        f"amizades/{uid_amigo}/{meu_uid}": "aceito",
    }
    _escrever("/.json", atualizacao, sessao["idToken"], metodo="PATCH")


def recusar_pedido(uid_amigo: str) -> None:
    sessao = sessao_valida()
    if not sessao:
        raise RuntimeError("Você precisa estar logado.")
    meu_uid = sessao["localId"]

    atualizacao = {
        f"amizades/{meu_uid}/{uid_amigo}": None,
        f"amizades/{uid_amigo}/{meu_uid}": None,
    }
    _escrever("/.json", atualizacao, sessao["idToken"], metodo="PATCH")


def listar_amizades() -> tuple[dict, dict]:
    """Devolve (amizades, sessao) — amizades é {uid_amigo: status}
    ('pendente_enviado', 'pendente_recebido' ou 'aceito')."""
    sessao = sessao_valida()
    if not sessao:
        return {}, {}
    resultado = _ler(f"/amizades/{sessao['localId']}.json", sessao["idToken"])
    return (resultado or {}), sessao


# ---------------------------------------------------------------------------
# mensagens diretas entre amigos
# ---------------------------------------------------------------------------

def _id_conversa(uid1: str, uid2: str) -> str:
    """ID estável e igual pros dois lados, não importa quem pergunta."""
    return "_".join(sorted([uid1, uid2]))


def enviar_mensagem_amigo(uid_destinatario: str, texto: str) -> None:
    texto = texto.strip()
    if not texto:
        return

    sessao = sessao_valida()
    if not sessao:
        raise RuntimeError("Você precisa estar logado.")

    meu_uid = sessao["localId"]
    id_conversa = _id_conversa(meu_uid, uid_destinatario)

    mensagem = {
        "remetente": meu_uid,
        "texto": texto,
        "timestamp": time.time(),
    }

    # POST (em vez de PUT) faz o Firebase gerar uma chave única e
    # ordenável por tempo sozinho — perfeito pra um histórico de chat
    url = f"{_database_url()}/mensagens/{id_conversa}.json?auth={sessao['idToken']}"
    dados = json.dumps(mensagem).encode("utf-8")
    requisicao = urllib.request.Request(url, data=dados, method="POST")
    try:
        with urllib.request.urlopen(requisicao, timeout=10):
            pass
    except urllib.error.HTTPError as erro:
        raise RuntimeError(f"Erro ao enviar mensagem: {erro}")


def buscar_mensagens(uid_amigo: str) -> list[dict]:
    """Devolve a conversa inteira com esse amigo, em ordem
    cronológica: [{'remetente': uid, 'texto': str, 'timestamp': float}]."""
    sessao = sessao_valida()
    if not sessao:
        return []

    meu_uid = sessao["localId"]
    id_conversa = _id_conversa(meu_uid, uid_amigo)

    dados = _ler(f"/mensagens/{id_conversa}.json", sessao["idToken"]) or {}
    mensagens = list(dados.values())
    mensagens.sort(key=lambda m: m.get("timestamp", 0))
    return mensagens
