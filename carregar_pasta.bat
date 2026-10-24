@echo off
chcp 65001 >nul
cd /d "%~dp0"
if "%~1"=="" goto uso
if not exist ".venv\Scripts\python.exe" goto semambiente
".venv\Scripts\python.exe" -m scripts.carregar_pasta "%~1"
goto fim

:uso
echo Arraste a pasta das planilhas sobre este arquivo.
goto fim

:semambiente
echo Execute primeiro o iniciar.bat para preparar o ambiente.

:fim
pause
