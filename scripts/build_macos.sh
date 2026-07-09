#!/usr/bin/env bash
# Construit une vraie app macOS (PyInstaller, sans Terminal) + copie à la racine.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m pip install --upgrade pip pyinstaller openpyxl pillow
python3 -m PyInstaller \
  --noconfirm --clean --windowed --onedir \
  --name "TauxBdC" \
  --icon packaging/assets/AppIcon.icns \
  --add-data "packaging/assets/logo_64.png:packaging/assets" \
  --add-data "packaging/assets/logo_128.png:packaging/assets" \
  --add-data "packaging/assets/app_icon.png:packaging/assets" \
  --hidden-import openpyxl \
  --collect-submodules openpyxl \
  gui_taux_bdc.py

rm -rf "Taux BdC.app"
cp -R "dist/TauxBdC.app" "Taux BdC.app"
/usr/libexec/PlistBuddy -c 'Set :CFBundleDisplayName Taux BdC' "Taux BdC.app/Contents/Info.plist" 2>/dev/null \
  || /usr/libexec/PlistBuddy -c 'Add :CFBundleDisplayName string Taux BdC' "Taux BdC.app/Contents/Info.plist"
/usr/libexec/PlistBuddy -c 'Set :CFBundleName Taux BdC' "Taux BdC.app/Contents/Info.plist" 2>/dev/null || true
xattr -cr "Taux BdC.app" 2>/dev/null || true
echo "Prêt : ./Taux BdC.app (double-clic, sans Terminal)"
