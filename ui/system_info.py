"""
Coleta informações de hardware do PC (processador, RAM, placa de vídeo,
armazenamento) pra mostrar na aba Sistema.

Usa WMI (via win32com, o mesmo pacote que o escravo.py já usa pra
achar/focar janelas) pra pegar o nome exato do processador e da(s)
placa(s) de vídeo no Windows — informação que o psutil sozinho não
fornece. RAM e disco vêm do psutil, que é multiplataforma.
"""

from __future__ import annotations

import platform

import psutil

try:
    import win32com.client
    PYWIN32_DISPONIVEL = True
except ImportError:
    PYWIN32_DISPONIVEL = False


def _consultar_wmi(classe: str, propriedade: str) -> list[str]:
    """Pergunta ao WMI do Windows por uma propriedade de uma classe
    (ex: nome de todos os Win32_VideoController). Devolve lista vazia
    se não for Windows, não tiver pywin32, ou a consulta falhar."""
    if not PYWIN32_DISPONIVEL:
        return []
    try:
        conexao = win32com.client.GetObject("winmgmts:")
        resultados = []
        for item in conexao.InstancesOf(classe):
            valor = getattr(item, propriedade, None)
            if valor:
                resultados.append(str(valor).strip())
        return resultados
    except Exception:
        return []


def obter_processador() -> str:
    nomes = _consultar_wmi("Win32_Processor", "Name")
    if nomes:
        return nomes[0]
    nome = platform.processor()
    return nome if nome else "Não foi possível identificar"


def obter_nucleos() -> str:
    fisicos = psutil.cpu_count(logical=False) or 0
    logicos = psutil.cpu_count(logical=True) or 0
    return f"{fisicos} núcleos físicos / {logicos} threads"


def obter_ram() -> dict:
    mem = psutil.virtual_memory()
    total_gb = mem.total / (1024 ** 3)
    usado_gb = mem.used / (1024 ** 3)
    return {
        "total": f"{total_gb:.1f} GB",
        "uso": f"{mem.percent:.0f}% em uso ({usado_gb:.1f} GB)",
    }


def obter_placas_de_video() -> list[str]:
    placas = _consultar_wmi("Win32_VideoController", "Name")
    return placas if placas else ["Não foi possível detectar"]


def obter_armazenamento() -> list[dict]:
    discos = []
    for particao in psutil.disk_partitions(all=False):
        try:
            uso = psutil.disk_usage(particao.mountpoint)
        except (PermissionError, OSError):
            continue
        discos.append({
            "unidade": particao.device,
            "total": f"{uso.total / (1024 ** 3):.0f} GB",
            "usado": f"{uso.percent:.0f}% em uso",
        })
    return discos


def obter_resumo_sistema() -> dict:
    """Junta tudo num dicionário só, pra página de Sistema consumir
    de uma vez."""
    return {
        "processador": obter_processador(),
        "nucleos": obter_nucleos(),
        "ram": obter_ram(),
        "placas_de_video": obter_placas_de_video(),
        "armazenamento": obter_armazenamento(),
        "sistema_operacional": f"{platform.system()} {platform.release()}",
    }
