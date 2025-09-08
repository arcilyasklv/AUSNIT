@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo --- Очистка старых сборок и кэша ---
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"

echo --- Сборка EXE по рецепту из AUSNIT.spec ---
python -m PyInstaller AUSNIT.spec

echo.
echo ==========================================
echo ✅ Сборка завершена!
echo Файл находится в папке 'dist'.
echo ==========================================
echo.
pause