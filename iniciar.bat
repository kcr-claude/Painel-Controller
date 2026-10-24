@echo off
chcp 65001 >nul
title Controller Hoteleiro ARA
cd /d "%~dp0"

set "PY=python"
where py >nul 2>nul
if not errorlevel 1 set "PY=py -3"
%PY% --version >nul 2>nul
if errorlevel 1 goto sempython

if exist ".venv\Scripts\python.exe" goto iniciar
echo Preparando o ambiente. Ocorre apenas na primeira vez e leva alguns minutos...
%PY% -m venv .venv
if errorlevel 1 goto falha
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 goto falha

:iniciar
echo.
echo Plataforma disponivel em http://localhost:8000
echo Mantenha esta janela aberta enquanto usar. Para encerrar, feche a janela.
start "" cmd /c "timeout /t 5 /nobreak >nul & start http://localhost:8000"
".venv\Scripts\python.exe" -m uvicorn app.web.app:app --host 127.0.0.1 --port 8000
goto fim

:sempython
echo Python nao encontrado neste computador.
echo Instale a versao 3.12 em https://www.python.org/downloads/ marcando "Add python.exe to PATH".
goto fim

:falha
echo Nao foi possivel preparar o ambiente. Verifique a internet e execute novamente.
if exist ".venv" rmdir /s /q ".venv"

:fim
pause
