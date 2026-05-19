@echo off
title Assistente Meet - Inicializador
echo Iniciando o Assistente Meet no ambiente virtual Python...
cd /d "%~dp0"
call .venv\Scripts\activate.bat
uv run python main.py
if %errorlevel% neq 0 (
    echo.
    echo Ocorreu um erro ao iniciar o assistente.
    echo Verifique se o ambiente virtual (.venv) está configurado corretamente.
    pause
)
