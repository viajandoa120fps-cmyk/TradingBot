@echo off
title AERO BOT PRO
echo.
echo  ============================================
echo   AERO BOT PRO - Elite v2.0
echo   Iniciando servidor...
echo  ============================================
echo.
cd /d "%~dp0"
python main.py
echo.
echo  El servidor se detuvo. Presiona cualquier tecla para cerrar.
pause >nul
