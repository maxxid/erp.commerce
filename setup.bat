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
    echo Descargalo: https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe
    echo IMPORTANTE: marcar "Add Python to PATH" al instalar.
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo Python detectado: %PYVER%

:: Verificar compatibilidad (3.14+ es muy nuevo, no hay wheels precompilados)
echo %PYVER% | findstr /r "^3\.1[4-9]" >nul
if %errorlevel% equ 0 (
    echo.
    echo [ADVERTENCIA] Python %PYVER% es muy reciente.
    echo Algunas librerias necesitan compilarse y requieren Visual C++ Build Tools.
    echo.
    echo Recomendacion: instalar Python 3.12 desde:
    echo   https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe
    echo.
    echo Si queres intentar con esta version, asegurate de tener instalado:
    echo   "Microsoft C++ Build Tools" desde https://visualstudio.microsoft.com/visual-cpp-build-tools/
    echo.
    choice /c SN /m "Continuar de todas formas"
    if errorlevel 2 exit /b 1
)

:: Crear entorno virtual
if not exist "venv" (
    echo.
    echo Creando entorno virtual...
    python -m venv venv
    echo [OK] Entorno virtual creado.
) else (
    echo [OK] Entorno virtual ya existe.
)

:: Activar venv e instalar dependencias
echo.
echo Instalando dependencias (esto puede tardar unos minutos)...
call venv\Scripts\activate.bat
pip install --upgrade pip --quiet
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Fallo la instalacion de dependencias.
    echo Si el error menciona "Building wheel for pydantic-core" o "link.exe not found":
    echo Necesitas Python 3.11 o 3.12 (NO 3.14). Instalalo y volve a ejecutar setup.bat
    pause
    exit /b 1
)
echo [OK] Dependencias instaladas.

:: Crear acceso directo en el Escritorio
echo.
echo Creando acceso directo en el Escritorio...
set "SCRIPT_DIR=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$WS = New-Object -ComObject WScript.Shell; $Desktop = [Environment]::GetFolderPath('Desktop'); $Shortcut = $WS.CreateShortcut($Desktop + '\ApexERP.lnk'); $Shortcut.TargetPath = '%SCRIPT_DIR%iniciar.bat'; $Shortcut.WorkingDirectory = '%SCRIPT_DIR%'; $Shortcut.IconLocation = 'C:\Windows\System32\SHELL32.dll,130'; $Shortcut.Save()"
if %errorlevel% equ 0 (
    echo [OK] Acceso directo creado en el Escritorio: ApexERP
) else (
    echo [AVISO] No se pudo crear el acceso directo. Podes iniciar manualmente con iniciar.bat
)

:: Crear carpeta de backups
if not exist "backups" mkdir backups

:: Generar DB fresca (sin DB vieja para que la licencia trial se cree nueva)
if exist "erp_comercio.db" (
    echo [OK] Base de datos existente conservada.
) else (
    echo [OK] Primera instalacion: la base de datos se creara al iniciar.
)

echo.
echo ============================================
echo   Instalacion completada.
echo.
echo   Para iniciar:
echo     1. Doble click en "ApexERP" en el Escritorio
echo     2. Abri http://localhost:8000/app
echo     3. Licencia trial: 30 dias gratis (automatica)
echo     4. Login: admin / admin
echo ============================================
echo.
pause
