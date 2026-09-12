@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv-testes\Scripts\python.exe" (
    py -3 -m venv .venv-testes
    if errorlevel 1 exit /b 1
)
".venv-testes\Scripts\python.exe" -m pip install -r requirements-testes.txt
if errorlevel 1 exit /b 1
set QT_QPA_PLATFORM=offscreen
set PYTHONUTF8=1
if not exist "reports-pipeline" mkdir "reports-pipeline"
set COVERAGE_FILE=reports-pipeline\.coverage
".venv-testes\Scripts\python.exe" -m pytest --cov --cov-report=term-missing --cov-report=html --cov-report=xml:reports-pipeline/coverage.xml --junitxml=reports-pipeline/junit.xml %*
exit /b %errorlevel%
