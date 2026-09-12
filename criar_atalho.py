"""
Cria um atalho do Assistente Virtual Ikuromimy na Área de Trabalho,
apontando pro executável gerado em dist/. Rode DEPOIS do build.bat:

    python criar_atalho.py

(pode rodar com o venv ativado ou não — só precisa do pywin32
instalado, que já está no requirements.txt)
"""

import os
import sys

import win32com.client

PASTA_PROJETO = os.path.dirname(os.path.abspath(__file__))
CAMINHO_EXE = os.path.join(PASTA_PROJETO, "dist", "Assistente Virtual Ikuromimy.exe")
CAMINHO_ICONE = os.path.join(PASTA_PROJETO, "icon.ico")


def criar_atalho() -> None:
    if not os.path.exists(CAMINHO_EXE):
        print("❌ Não encontrei o executável em:")
        print(f"   {CAMINHO_EXE}")
        print("   Rode o build.bat primeiro pra gerar o .exe.")
        sys.exit(1)

    area_trabalho = os.path.join(os.environ["USERPROFILE"], "Desktop")
    caminho_atalho = os.path.join(area_trabalho, "Assistente Virtual Ikuromimy.lnk")

    shell = win32com.client.Dispatch("WScript.Shell")
    atalho = shell.CreateShortcut(caminho_atalho)
    atalho.TargetPath = CAMINHO_EXE
    # importante: roda com a pasta do próprio .exe como diretório de
    # trabalho, senão o app pode não achar arquivos relativos
    atalho.WorkingDirectory = os.path.dirname(CAMINHO_EXE)

    if os.path.exists(CAMINHO_ICONE):
        atalho.IconLocation = CAMINHO_ICONE

    atalho.Description = "Assistente Virtual Ikuromimy"
    atalho.save()

    print("✅ Atalho criado em:")
    print(f"   {caminho_atalho}")


if __name__ == "__main__":
    criar_atalho()
