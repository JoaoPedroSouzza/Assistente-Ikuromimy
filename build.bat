@echo off
setlocal

echo ================================================
echo   Assistente Virtual Ikuromimy - build do executavel (.exe)
echo ================================================
echo.

python --version

REM cria o ambiente virtual se ainda nao existir
if not exist venv (
    echo Criando ambiente virtual...
    python -m venv venv
)

call venv\Scripts\activate.bat

echo.
echo Instalando dependencias (pode levar um tempinho na primeira vez)...
python -m pip install --upgrade pip
pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ❌ Falha ao instalar as dependencias. Confere as mensagens acima.
    pause
    exit /b 1
)

echo.
echo Limpando builds antigos...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo Gerando o executavel com PyInstaller...
pyinstaller ikuro.spec

echo.
if exist "dist\Assistente Virtual Ikuromimy.exe" (
    echo ================================================
    echo   Pronto! Executavel gerado em:
    echo   dist\Assistente Virtual Ikuromimy.exe
    echo.
    echo   Agora roda: python criar_atalho.py
    echo   pra criar o atalho na Area de Trabalho.
    echo ================================================
) else (
    echo ❌ Algo deu errado, o .exe nao foi gerado.
    echo    Confere as mensagens de erro acima.
)

pause
