@echo off
chcp 65001 >nul
cd /d "%~dp0"
python taux_bdc.py
if errorlevel 1 (
  echo.
  echo Python introuvable ou erreur. Essayez: py taux_bdc.py
  py taux_bdc.py
)
echo.
pause
