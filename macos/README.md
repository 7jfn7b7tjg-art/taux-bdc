# Taux BdC — macOS (SwiftUI)

Native macOS app for Canadian accountants. Windows users: see the root README and Releases `Taux-BdC-Windows.zip`.

## Prérequis / Requirements

1. Install **Xcode** from the App Store (not just Command Line Tools)
2. Point developer tools to Xcode:

```bash
sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
sudo xcodebuild -license accept   # once
```

## Ouvrir et lancer / Open and run

```bash
open macos/TauxBdC/TauxBdC.xcodeproj
```

In Xcode: scheme **TauxBdC** → **My Mac** → ▶ Run.

Or from the repo root:

```bash
./scripts/build_macos.sh    # builds Release + copies Taux BdC.app to repo root
open "Taux BdC.app"
```

## Fonctions / Features

### Conversion
- Daily rate, **monthly average**, or **annual average** (Bank of Canada Valet)
- Direction: **foreign → CAD** or **CAD → foreign**
- Weekend/holiday dates → previous BoC business day
- Copy menu: full summary, converted amount only, tab-separated row (Excel/journal)
- Export CSV / Excel

### Lots (batch)
- Import: CSV, Excel (.xlsx), JSON, XML — **drag & drop** supported
- Process via BoC API (with local cache fallback)
- Export: CSV, JSON, XML

### Historique (audit)
- Read-only view of `data/historique_conversions.log`
- Search, export, show in Finder
- **Clear history** — creates a timestamped backup in `data/sauvegardes/` first

### General
- FR / EN (toolbar language picker)
- `Decimal` arithmetic throughout (no floating-point rounding issues)
- Local cache: `data/cache_taux.json`
- Preferences persisted (currency, direction, rate mode, language)

## Tests

```bash
./scripts/test_macos.sh
```

## Windows

Do not use this folder for Windows. See `python/gui_taux_bdc.py` and Releases.
