@echo off
REM Flash CLI — usage: taux 2026-06-15 usd [montant] [reference]
cd /d "%~dp0"
python python\taux_bdc.py %*
if errorlevel 1 py python\taux_bdc.py %*
