@echo off
title ApexERP - Sistema de Gestion
color 0B
cd /d "%~dp0"

echo ============================================
echo   ApexERP - Iniciando servidor...
echo ============================================
echo.

:: Activar entorno virtual
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

:: Test rapido: verificar que Python funciona
python -c "print('Python OK')" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no funciona. Ejecuta setup.bat de nuevo.
    pause
    exit /b 1
)

echo Iniciando servidor en ventana separada...
echo Si ves errores, NO la cierres asi podemos diagnosticar.
echo.
start "ApexERP Server" python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

echo Esperando a que el servidor este listo (max 60s)...
set /a count=0
:wait
timeout /t 2 /nobreak >nul
set /a count+=1
powershell -NoProfile -Command "try { $null = irm http://localhost:8000/api/licencia/estado -TimeoutSec 2 -ErrorAction Stop; exit 0 } catch { exit 1 }" >nul 2>&1
if %errorlevel% equ 0 goto :listo
if %count% lss 30 goto :wait

echo.
echo [ERROR] El servidor no respondio despues de 60 segundos.
echo.
echo Posibles causas:
echo   - Error en la ventana del servidor (mira la otra ventana)
echo   - Python 3.12 no instalado. Ejecuta setup.bat
echo   - Puerto 8000 bloqueado por firewall/antivirus
echo.
pause
exit /b 1

:listo
echo [OK] Servidor listo.
start "" http://localhost:8000/app
echo.
echo ============================================
echo   ApexERP corriendo en http://localhost:8000/app
echo   NO CIERRES la ventana del servidor.
echo   Para detener: Ctrl+C en la ventana del servidor.
echo ============================================
echo.
pause
