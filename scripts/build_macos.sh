#!/usr/bin/env bash
# Construit l'app macOS native SwiftUI + copie à la racine du repo.
set -euo pipefail
cd "$(dirname "$0")/.."

xcodebuild \
  -project macos/TauxBdC/TauxBdC.xcodeproj \
  -target TauxBdC \
  -configuration Release \
  CODE_SIGN_IDENTITY=- \
  CODE_SIGNING_REQUIRED=NO \
  CODE_SIGNING_ALLOWED=NO \
  build

APP="macos/TauxBdC/build/Release/Taux BdC.app"
codesign --force --deep -s - "$APP"

rm -rf "Taux BdC.app"
cp -R "$APP" "Taux BdC.app"
xattr -cr "Taux BdC.app" 2>/dev/null || true
echo "Prêt : ./Taux BdC.app (double-clic, sans Terminal)"
