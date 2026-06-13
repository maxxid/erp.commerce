@echo off
title ApexERP - Instalador Completo
color 0B
setlocal enabledelayedexpansion
echo ============================================
echo   ApexERP - Instalador (con Python 3.12)
echo ============================================
echo.

:: Buscar Python 3.12 ya instalado
set "PY312="
if exist "C:\Python312\python.exe" set "PY312=C:\Python312\python.exe"
if exist "C:\Program Files\Python312\python.exe" set "PY312=C:\Program Files\Python312\python.exe"

if not "%PY312%"=="" (
    echo [OK] Python 3.12 detectado: %PY312%
    goto :create_venv
)

:: Verificar el Python del sistema
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo No hay Python. Descargando Python 3.12.8...
    goto :download_python
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo Python del sistema: %PYVER%

:: Si es 3.11, 3.12, o 3.13, usarlo directamente
echo %PYVER% | findstr /r "^3\.1[1-3]" >nul
if %errorlevel% equ 0 (
    set "PY312=python"
    echo [OK] Version compatible. Usando python del sistema.
    goto :create_venv
)

:: Si es 3.14+, descargar 3.12
echo [AVISO] Python %PYVER% es muy nuevo. Instalando Python 3.12 aparte...

:download_python
echo.
echo Descargando Python 3.12.8 (25 MB)...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe' -OutFile '%TEMP%\python312.exe'"
if %errorlevel% neq 0 (
    echo [ERROR] No se pudo descargar Python.
    echo Verifica tu conexion a internet y volve a intentar.
    pause
    exit /b 1
)

echo Instalando Python 3.12 en C:\Python312 (NO modifica tu Python actual)...
"%TEMP%\python312.exe" /quiet InstallAllUsers=0 TargetDir=C:\Python312 PrependPath=0 Include_test=0
del "%TEMP%\python312.exe"

if exist "C:\Python312\python.exe" (
    set "PY312=C:\Python312\python.exe"
    echo [OK] Python 3.12 instalado en C:\Python312
) else (
    echo [ERROR] Fallo la instalacion de Python 3.12.
    echo Intentar instalar manualmente desde:
    echo   https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe
    pause
    exit /b 1
)

:create_venv
:: Limpiar venv anterior
if exist "venv" (
    echo Limpiando instalacion anterior...
    rmdir /s /q venv
)

echo.
echo Creando entorno virtual...
"%PY312%" -m venv venv
if %errorlevel% neq 0 (
    echo [ERROR] No se pudo crear el entorno virtual.
    pause
    exit /b 1
)

:: Activar e instalar
call venv\Scripts\activate.bat
echo Actualizando pip...
python -m pip install --upgrade pip --quiet

echo.
echo Instalando dependencias (1-2 minutos)...
echo.
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Fallo la instalacion de dependencias.
    pause
    exit /b 1
)

echo [OK] Dependencias instaladas.

:: Crear acceso directo
echo.
echo Creando acceso directo...
echo Set WS = WScript.CreateObject("WScript.Shell") > "%TEMP%\acceso.vbs"
echo DesktopPath = WS.SpecialFolders("Desktop") >> "%TEMP%\acceso.vbs"
echo Set Shortcut = WS.CreateShortcut(DesktopPath ^& "\ApexERP.lnk") >> "%TEMP%\acceso.vbs"
echo Shortcut.TargetPath = "%~dp0iniciar.bat" >> "%TEMP%\acceso.vbs"
echo Shortcut.WorkingDirectory = "%~dp0" >> "%TEMP%\acceso.vbs"
echo Shortcut.IconLocation = "C:\Windows\System32\SHELL32.dll,130" >> "%TEMP%\acceso.vbs"
echo Shortcut.Save >> "%TEMP%\acceso.vbs"
cscript //nologo "%TEMP%\acceso.vbs"
del "%TEMP%\acceso.vbs"
echo [OK] Acceso directo "ApexERP" en el Escritorio.

:: Carpeta backups
if not exist "backups" mkdir backups

echo.
echo ============================================
echo   INSTALACION COMPLETADA
echo.
echo   Doble click en "ApexERP" del Escritorio
echo   Abri http://localhost:8000/app
echo   Login: admin / admin
echo   Licencia: 30 dias de prueba (automatica)
echo ============================================
echo.
pause
