#!/bin/bash
cd "$(dirname "$0")"
python3 taux_bdc.py
echo
read -n 1 -s -r -p "Appuyez sur une touche pour fermer…"
echo
