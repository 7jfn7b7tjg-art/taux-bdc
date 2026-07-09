# Taux BdC — Bank of Canada exchange rates / Taux de change Banque du Canada

Desktop tools for Canadian accountants: official Bank of Canada (Valet) FX rates → CAD.

- **macOS** : native **SwiftUI** app (recommended) — see [`macos/`](macos/)
- **Windows** : Python GUI + PyInstaller (lighter feature set) — see Releases
- **CLI** : Flash mode + interactive terminal (`./taux …`)
- FR/EN, `Decimal` arithmetic, weekend/holiday fallback
- Local cache + audit log in `data/`

**Not affiliated with the Bank of Canada.** Rates are indicative only.  
**Non affilié à la Banque du Canada.** Les taux sont indicatifs seulement.

---

## Repository layout / Arborescence

```
taux-bdc/
├── README.md                 # This file
├── LICENSE
├── Taux BdC.command          # macOS double-click launcher (GUI)
├── Taux BdC.bat              # Windows double-click launcher (GUI)
├── taux / taux.bat           # Flash CLI launchers
│
├── macos/                    # Native SwiftUI app (recommended on Mac)
│   ├── README.md
│   ├── TauxBdC/              # Xcode project
│   └── tests/                # Swift test harness
│
├── python/                   # Windows GUI + CLI engine
│   ├── taux_bdc.py           # Core logic + Flash CLI
│   ├── gui_taux_bdc.py       # Tkinter GUI
│   ├── io_ecritures.py       # CSV / Excel batch I/O
│   ├── requirements.txt
│   └── tests/                # pytest suite
│
├── packaging/                # Release assets (icons, LISEZ-MOI, template)
├── scripts/                  # build_macos.sh, build_windows.bat, test_macos.sh
└── .github/workflows/        # CI: tests + release ZIPs
```

Runtime data (not in git): `data/cache_taux.json`, `data/historique_conversions.log`, `data/sauvegardes/`

---

## Download / Téléchargement

Latest **Release** assets:

1. Open **Releases** on GitHub
2. Download **one** of:
   - `Taux-BdC-macOS.zip` — Mac (SwiftUI `.app`)
   - `Taux-BdC-Windows.zip` — Windows (`.exe`, no Python required)

### macOS

1. Unzip and double-click **Taux BdC.app**
2. If macOS blocks the app: right-click → **Open** → **Open**
3. No Terminal, no Python

To build from source: [`macos/README.md`](macos/README.md) (requires Xcode).

### Windows

1. Unzip and double-click **Taux-BdC.exe**
2. If SmartScreen: **More info** → **Run anyway**

Each ZIP includes `modele_lot.csv`.

---

## Flash CLI (fastest / le plus rapide)

Works on Mac and Windows (with Python installed, or from the repo):

```bash
# Rate only / taux seul
./taux 2026-07-05 usd

# Convert amount / convertir un montant (+ optional invoice ref)
./taux 2026-07-05 usd 1500.00
./taux 2026-07-05 usd 1500.00 FAC-10443
```

Windows: `taux.bat 2026-07-05 usd 1500`

---

## App features / Fonctions (Mac & Windows)

Both desktop apps offer the same accounting features (SwiftUI on Mac, Tkinter on Windows):

| Tab | What it does |
|-----|----------------|
| **Conversion** | Daily, monthly or annual average rate; **foreign ↔ CAD**; copy formats (full summary, amount only, TSV row) |
| **Lots** | Batch import (CSV, Excel, JSON, XML) — drag & drop on Windows — process — export CSV/JSON/XML |
| **Historique** | Audit log viewer, search, export, open data folder, **clear history** (auto-backup to `data/sauvegardes/`) |

Weekend or holiday dates automatically use the **previous BoC business day**.

### Batch columns

| date | devise | montant | reference (optional) |
|------|--------|---------|----------------------|

Output adds: `date_taux`, `taux`, `montant_cad`, `serie`, `ajuste`, `erreur`.

> **Note:** macOS uses a native SwiftUI interface; Windows uses Tkinter — same features, different look.

---

## Cache & audit / Cache et piste d'audit

Stored next to the program in `data/` (preferred). Falls back to `~/.taux_bdc/` if not writable.

| File | Role |
|------|------|
| `data/cache_taux.json` | Rates already fetched (offline fallback) |
| `data/historique_conversions.log` | Timestamped audit lines for auditors |
| `data/sauvegardes/` | Backups created before clearing history |

---

## Develop from source / Développement

### macOS (SwiftUI)

```bash
open macos/TauxBdC/TauxBdC.xcodeproj
# or:
./scripts/build_macos.sh
./scripts/test_macos.sh
```

### Windows / CLI (Python)

All Python code lives in [`python/`](python/):

```bash
pip install -r python/requirements.txt
python3 python/gui_taux_bdc.py
python3 python/taux_bdc.py
python -m pytest python/tests/ -q
```

### Build Windows with PyInstaller

```bat
scripts\build_windows.bat
```

---

## Automated releases (GitHub Actions)

```bash
git tag v0.4.0
git push origin v0.4.0
```

Or **Actions** → **Release builds** → **Run workflow**.

> **Note:** macOS builds are ad-hoc signed. Recipients may need right-click → Open the first time.

---

## LinkedIn post (template)

> Free tool for Canadian accountants: official Bank of Canada FX → CAD.  
> Mac (native app) + Windows, FR/EN, single + batch, audit trail. No Python on Mac/Windows releases.  
>  
> macOS → [Taux-BdC-macOS.zip]  
> Windows → [Taux-BdC-Windows.zip]  

---

## License

MIT — see [LICENSE](LICENSE). Data via [Bank of Canada Valet](https://www.bankofcanada.ca/valet/).
