"""Interpretação pura; não executa comandos nem acessa o computador."""
import re
import difflib
from functools import lru_cache

def contem_palavra(comando: str, *palavras: str) -> bool:
    """Verifica se alguma das palavras aparece como palavra inteira no
    comando (evita, por exemplo, 'para' disparar dentro de 'parabéns')."""
    return any(re.search(rf"\b{re.escape(p)}\b", comando) for p in palavras)

def extrair_alvo(comando: str, *gatilhos: str) -> str:
    """Remove os gatilhos do comando e devolve o que sobrou (o 'alvo')."""
    alvo = comando
    for g in gatilhos:
        alvo = re.sub(rf"\b{re.escape(g)}\b", "", alvo)
    return alvo.strip()

PALAVRAS_CHAVE_CONHECIDAS = [
    "tocar", "pesquisar", "pesquisa", "buscar", "atualizar",
    "abrir", "abre", "fechar", "fecha",
    "play", "pause", "pausar",
    "próxima", "proxima", "pula", "next",
    "anterior", "voltar",
    "aumentar", "sobe", "diminuir", "abaixa",
    "loop", "repetir",
    "para", "sair", "encerrar",
]

@lru_cache(maxsize=256)
def _corrigir_palavra(primeira: str) -> str | None:
    candidatos = difflib.get_close_matches(primeira, PALAVRAS_CHAVE_CONHECIDAS, n=1, cutoff=0.72)
    return candidatos[0] if candidatos else None


def _tentar_corrigir_comando(comando: str) -> str | None:
    """Se a primeira palavra do comando não bate com nenhuma palavra-
    gatilho conhecida, tenta achar a mais parecida (erro de digitação,
    tipo 'abrri' em vez de 'abrir') e devolve o comando corrigido.
    Devolve None se não achar nada razoavelmente parecido."""
    partes = comando.split(maxsplit=1)
    if not partes:
        return None

    primeira = partes[0]
    resto = partes[1] if len(partes) > 1 else ""

    if primeira in PALAVRAS_CHAVE_CONHECIDAS:
        return None  # já bate certinho, não é isso que está falhando

    if len(primeira) > 128:
        return None
    corrigida = _corrigir_palavra(primeira)
    if corrigida is None:
        return None
    return f"{corrigida} {resto}".strip()

def eh_comando_conhecido(comando: str) -> bool:
    """Verifica (sem executar nada, sem falar nada) se o texto bate
    com algum padrão de comando direto conhecido. Usada pra decidir se
    um texto vai direto pro processar_comando() ou se é conversa de
    verdade e deve ir pra uma IA conversacional."""
    comando = comando.lower().strip()
    if not comando:
        return False

    if re.match(r"^tocar\s+.+", comando):
        return True
    if re.match(r"^(?:pesquisar|pesquisa|buscar)\s+.+", comando):
        return True
    if contem_palavra(comando, "atualizar") and "apps" in comando:
        return True
    if contem_palavra(comando, "abrir", "abre"):
        return True
    if contem_palavra(comando, "fechar", "fecha"):
        return True
    if contem_palavra(comando, "play", "pause", "pausar"):
        return True
    if contem_palavra(comando, "próxima", "proxima", "pula", "next"):
        return True
    if contem_palavra(comando, "anterior", "voltar"):
        return True
    if contem_palavra(comando, "aumentar", "sobe") and "volume" in comando:
        return True
    if contem_palavra(comando, "diminuir", "abaixa") and "volume" in comando:
        return True
    if contem_palavra(comando, "loop", "repetir"):
        return True
    if contem_palavra(comando, "para", "sair", "encerrar"):
        return True

    # também conta como comando conhecido se a autocorreção reconhecer
    # a primeira palavra como parecida com um gatilho (ex: "abrri spotify")
    if _tentar_corrigir_comando(comando):
        return True

    return False
