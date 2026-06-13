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

:: Iniciar servidor en segundo plano
start /min "ApexERP-Server" python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

echo Aguardando que el servidor este listo...
:: Esperar hasta que el servidor responda (max 30s)
powershell -NoProfile -Command "$ok=0; for($i=0;$i -lt 30;$i++){try{$r=irm http://localhost:8000/api/licencia/estado -TimeoutSec 2 -ErrorAction Stop; if($r){$ok=1;break}}catch{Start-Sleep 1}}; if($ok){Write-Host 'LISTO'}else{Write-Host 'TIMEOUT'}"

echo.
echo Abriendo http://localhost:8000/app ...
start "" http://localhost:8000/app

echo.
echo ============================================
echo   Servidor corriendo en segundo plano.
echo   NO CIERRES la ventana del servidor.
echo   Para detener: Ctrl+C en la ventana del servidor
echo   o busca "ApexERP-Server" y cerrala.
echo ============================================
echo.
pause
