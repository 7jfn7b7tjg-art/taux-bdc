# Taux BdC — macOS (SwiftUI)

Native macOS app (SwiftUI). Windows users keep the Python / PyInstaller build.

## Prérequis / Requirements

1. Installer **Xcode** depuis l’App Store (pas seulement les Command Line Tools)
2. Ouvrir un terminal et pointer les outils développeur vers Xcode :

```bash
sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
sudo xcodebuild -license accept   # une fois
```

## Ouvrir et lancer

```bash
open "/Users/clement/Taux de change/macos/TauxBdC/TauxBdC.xcodeproj"
```

Dans Xcode : schéma **TauxBdC** → **My Mac** → ▶ Run.

Ou en ligne de commande :

```bash
cd macos/TauxBdC
xcodebuild -scheme TauxBdC -configuration Release -derivedDataPath DerivedData build
open "DerivedData/Build/Products/Release/Taux BdC.app"
```

Une copie prête à double-cliquer est aussi générée à la racine du repo : `Taux BdC.app`.

## Fonctions

- Conversion unitaire (Decimal, Valet BdC, week-end → jour ouvré précédent)
- Lot CSV (import / traiter / exporter)
- FR / EN
- Cache : `data/cache_taux.json` (à côté de l’app si possible)
- Audit : `data/historique_conversions.log`
- Logo forex + icône Dock

## Windows

Ne pas utiliser ce dossier. Voir la racine du repo : `gui_taux_bdc.py` et les Releases `Taux-BdC-Windows.zip`.
