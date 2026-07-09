#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m pip install --upgrade pip pyinstaller
python3 -m PyInstaller --noconfirm --clean --onefile --console --name Taux-BdC taux_bdc.py
echo "Built: dist/Taux-BdC"
