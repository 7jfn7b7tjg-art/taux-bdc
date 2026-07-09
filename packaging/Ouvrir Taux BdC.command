#!/bin/bash
cd "$(dirname "$0")/.."
if [ -d "Taux BdC.app" ]; then
  open "Taux BdC.app"
else
  echo "Taux BdC.app introuvable. Lancez : ./scripts/build_macos.sh"
  read -n 1 -s -r -p "Appuyez sur une touche…"
fi
