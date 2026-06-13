@echo off
title Instalador ApexERP
color 0E
echo ============================================
echo   ApexERP - Instalador del Sistema
echo ============================================
echo.

:: Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no esta instalado.
    echo.
    echo Descargalo desde: https://www.python.org/downloads/
    echo Al instalar, MARCAR la casilla "Add Python to PATH"
    echo Luego volver a ejecutar este instalador.
    pause
    exit /b 1
)

echo [OK] Python encontrado:
python --version

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
echo Instalando dependencias...
call venv\Scripts\activate.bat
pip install -r requirements.txt --quiet
echo [OK] Dependencias instaladas.

:: Crear acceso directo en el Escritorio
echo.
echo Creando acceso directo en el Escritorio...
powershell -Command ^
    "$WS = New-Object -ComObject WScript.Shell; ^
     $Desktop = [Environment]::GetFolderPath('Desktop'); ^
     $Shortcut = $WS.CreateShortcut($Desktop + '\ApexERP.lnk'); ^
     $Shortcut.TargetPath = '%~dp0iniciar.bat'; ^
     $Shortcut.WorkingDirectory = '%~dp0'; ^
     $Shortcut.IconLocation = '%SystemRoot%\System32\SHELL32.dll,130'; ^
     $Shortcut.Save()"
echo [OK] Acceso directo creado: ApexERP en el Escritorio

:: Crear carpeta de backups
if not exist "backups" mkdir backups

echo.
echo ============================================
echo   Instalacion completada.
echo.
echo   Para iniciar el sistema:
echo     1. Doble click en "ApexERP" en el Escritorio
echo     2. Entrar a http://localhost:8000/app
echo     3. Activar la licencia DEMO (30 dias gratis)
echo     4. Usuario: admin - Contrasena: admin
echo ============================================
echo.
pause
