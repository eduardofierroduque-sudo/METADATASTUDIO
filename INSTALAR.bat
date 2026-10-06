@echo off
chcp 65001 >nul
title Metadata Studio - Instalador
cd /d "%~dp0"
echo ============================================
echo   METADATA STUDIO - Configuracion inicial
echo ============================================
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo [ERROR] No se encontro Python. Instalalo desde python.org
    echo         marca la casilla "Add python.exe to PATH"
    pause
    exit /b 1
)

if not exist "venv\Scripts\python.exe" (
    echo [1/3] Creando entorno virtual...
    py -3.12 -m venv venv
    if errorlevel 1 (
        echo [ERROR] No se pudo crear el entorno. Se necesita Python 3.12
        pause
        exit /b 1
    )
) else (
    echo [1/3] Entorno virtual ya existente.
)

call venv\Scripts\activate.bat
echo [2/3] Instalando dependencias...
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
pip install pillow mutagen --quiet

echo [3/3] Verificando ExifTool...
if exist "exiftool\exiftool.exe" (
    echo         ExifTool encontrado.
) else (
    echo [ERROR] Falta la carpeta "exiftool" con exiftool.exe
)

echo.
echo [OK] Instalacion completada.
echo      Para abrir el programa ejecuta:  INICIAR.bat
echo      Para crear el EXE ejecuta:       COMPILAR.bat
pause
