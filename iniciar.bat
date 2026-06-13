@echo off
title ApexERP - Sistema de Gestion
color 0B

:: Usar el directorio donde esta este archivo como raiz
cd /d "%~dp0"

echo ============================================
echo   ApexERP - Iniciando servidor...
echo ============================================
echo.
echo   Frontend : http://localhost:8000/app
echo   API Docs : http://localhost:8000/docs
echo.
echo   NO CIERRES esta ventana mientras usas el sistema.
echo   Para detener: presiona Ctrl+C o cierra esta ventana.
echo ============================================
echo.

:: Activar entorno virtual si existe
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

:: Esperar 2 segundos y abrir el navegador
start "" http://localhost:8000/app

:: Iniciar el servidor
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

pause
