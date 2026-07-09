@echo off
chcp 65001 >nul
cd /d "%~dp0"
python python\gui_taux_bdc.py
if errorlevel 1 (
  echo.
  echo Python introuvable ou erreur. Essayez: py python\gui_taux_bdc.py
  py python\gui_taux_bdc.py
)
echo.
pause
