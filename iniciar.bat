@echo off
title ApexERP - Servidor
color 0B
cd /d "%~dp0"

echo ============================================
echo   ApexERP - Iniciando servidor...
echo   SI VES UN ERROR, SACALE FOTO
echo ============================================
echo.

:: Activar entorno virtual
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

:: Test rapido
python -c "print('Python OK')" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no funciona. Ejecuta setup.bat.
    pause
    exit /b 1
)

echo Servidor iniciando...
echo.
echo NO CIERRES ESTA VENTANA.
echo Si crashea, sacale foto al error y mandamela.
echo.
echo Abri http://localhost:8000/app en el navegador.
echo ============================================
echo.

:: Ejecutar desde esta misma ventana para ver errores
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 2>&1

echo.
echo El servidor se detuvo.
pause
