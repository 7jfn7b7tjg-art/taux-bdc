@echo off
cd /d "%~dp0\.."
python -m pip install --upgrade pip pyinstaller -r python\requirements.txt
python -m PyInstaller --noconfirm --clean --onefile --windowed --name Taux-BdC --hidden-import openpyxl --hidden-import tkinterdnd2 --collect-submodules openpyxl --collect-all tkinterdnd2 python\gui_taux_bdc.py
echo Built: dist\Taux-BdC.exe
pause
