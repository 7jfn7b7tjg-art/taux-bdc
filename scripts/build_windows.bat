@echo off
cd /d "%~dp0\.."
python -m pip install --upgrade pip pyinstaller
python -m PyInstaller --noconfirm --clean --onefile --console --name Taux-BdC taux_bdc.py
echo Built: dist\Taux-BdC.exe
pause
