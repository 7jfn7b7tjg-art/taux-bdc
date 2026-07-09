@echo off
cd /d "%~dp0\.."
python -m pip install --upgrade pip pyinstaller openpyxl
python -m PyInstaller --noconfirm --clean --onefile --windowed --name Taux-BdC --hidden-import openpyxl --collect-submodules openpyxl python\gui_taux_bdc.py
echo Built: dist\Taux-BdC.exe
pause
