@echo off
title Instalador ApexERP
color 0E
setlocal enabledelayedexpansion
echo ============================================
echo   ApexERP - Instalador del Sistema
echo ============================================
echo.

:: Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no esta instalado.
    echo.
    echo Descargalo: https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe
    echo IMPORTANTE: marcar "Add Python to PATH" al instalar.
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo Python detectado: %PYVER%

:: Crear entorno virtual
if exist "venv" (
    echo [OK] Entorno virtual ya existe. Limpiando...
    rmdir /s /q venv
)
echo Creando entorno virtual...
python -m venv venv
if %errorlevel% neq 0 (
    echo [ERROR] No se pudo crear el entorno virtual.
    pause
    exit /b 1
)
echo [OK] Entorno virtual creado.

:: Activar venv
call venv\Scripts\activate.bat

:: Actualizar pip
echo.
echo Actualizando pip...
python -m pip install --upgrade pip --quiet

:: Instalar dependencias
echo.
echo Instalando dependencias (esto puede tardar varios minutos)...
echo.
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo ============================================
    echo [ERROR] Fallo la instalacion.
    echo.
    echo Si ves "Building wheel for pydantic-core" o "link.exe":
    echo   Necesitas Python 3.11 o 3.12 (NO 3.14).
    echo.
    echo Si ves "Building wheel for bcrypt":
    echo   Necesitas Microsoft C++ Build Tools instalado.
    echo.
    echo Instala Python 3.12 de:
    echo   https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe
    echo ============================================
    pause
    exit /b 1
)
echo [OK] Dependencias instaladas.

:: Crear acceso directo usando VBScript (mas fiable que PowerShell)
echo.
echo Creando acceso directo en el Escritorio...
set "VBS=%TEMP%\crear_acceso.vbs"
echo Set WS = WScript.CreateObject("WScript.Shell") > "%VBS%"
echo DesktopPath = WS.SpecialFolders("Desktop") >> "%VBS%"
echo Set Shortcut = WS.CreateShortcut(DesktopPath ^& "\ApexERP.lnk") >> "%VBS%"
echo Shortcut.TargetPath = "%~dp0iniciar.bat" >> "%VBS%"
echo Shortcut.WorkingDirectory = "%~dp0" >> "%VBS%"
echo Shortcut.IconLocation = "C:\Windows\System32\SHELL32.dll,130" >> "%VBS%"
echo Shortcut.Save >> "%VBS%"
cscript //nologo "%VBS%"
del "%VBS%"
echo [OK] Acceso directo "ApexERP" creado en el Escritorio.

:: Crear carpeta de backups
if not exist "backups" mkdir backups

echo.
echo ============================================
echo   INSTALACION COMPLETADA
echo.
echo   Para iniciar el sistema:
echo     1. Doble click en "ApexERP" en el Escritorio
echo     2. Abri http://localhost:8000/app
echo     3. Licencia: 30 dias de prueba (automatica)
echo     4. Login: admin / admin
echo ============================================
echo.
pause
