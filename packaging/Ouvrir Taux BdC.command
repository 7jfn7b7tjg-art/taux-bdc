#!/bin/bash
cd "$(dirname "$0")"
if [ -d "Taux-BdC.app" ]; then
  open "Taux-BdC.app"
elif [ -x "./Taux-BdC" ]; then
  ./Taux-BdC
else
  echo "Taux-BdC introuvable / not found in this folder."
  read -n 1 -s -r -p "Press any key to close…"
fi
