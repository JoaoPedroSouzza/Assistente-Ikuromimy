# -*- mode: python ; coding: utf-8 -*-
#
# Receita de empacotamento do Assistente Virtual Ikuromimy. Roda com:
#   pyinstaller ikuro.spec
# (o build.bat já faz isso pra você)

import os

# se você colocar um icon.ico na raiz do projeto, ele é usado
# automaticamente no .exe e no atalho; se não existir, fica sem ícone
# customizado (usa o padrão do Windows), sem quebrar o build.
caminho_icone = "icon.ico" if os.path.exists("icon.ico") else None

a = Analysis(
    ["interface.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("styles/dark.qss", "styles"),
        *([(caminho_icone, ".")] if caminho_icone else []),
    ],
    hiddenimports=[
        "win32timezone",   # dependência "escondida" comum do pywin32
        "win32com.client",
        "pyperclip",
        "werkzeug.serving",   # usado pelo servidor do controle remoto
        "flask",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Assistente Virtual Ikuromimy",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,      # False = sem janela de terminal preta atrás do app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=caminho_icone,
)
