@echo off
chcp 65001 >nul
title Metadata Studio - Compilador EXE
cd /d "%~dp0"
echo ============================================
echo   METADATA STUDIO - Compilando EXE
echo ============================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo [!] Falta el entorno. Ejecuta primero INSTALAR.bat
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
echo Limpiando compilaciones anteriores...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo Compilando MetadataStudio.exe (esto tarda unos minutos)...
pyinstaller --noconfirm --clean --onefile --windowed --name MetadataStudio ^
  --add-data "exiftool;exiftool" ^
  --collect-all customtkinter ^
  --collect-all tkinterdnd2 ^
  --collect-all mutagen ^
  --hidden-import PIL._tkinter_finder ^
  app.py

echo.
if exist "dist\MetadataStudio.exe" (
    echo [OK] EXE generado correctamente:
    echo      dist\MetadataStudio.exe
    echo.
    echo      Copia ese archivo a donde quieras y ejecutalo con doble clic.
) else (
    echo [ERROR] La compilacion fallo. Revisa los mensajes de arriba.
)
pause
