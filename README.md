# Taux BdC — Bank of Canada exchange rates / Taux de change Banque du Canada

Desktop tools for Canadian accountants: official Bank of Canada (Valet) FX rates → CAD.

- **macOS** : native **SwiftUI** app (see [`macos/`](macos/))  
- **Windows** : Python GUI + PyInstaller (see Releases)  
- Flash CLI + batch CSV, FR/EN, `Decimal`, weekend/holiday fallback  
- Local cache + audit log in `data/`  

**Not affiliated with the Bank of Canada.** Rates are indicative only.  
**Non affilié à la Banque du Canada.** Les taux sont indicatifs seulement.

---

## Download / Téléchargement

Latest **Release** assets:

1. Open **Releases**  
2. Download **one** of:
   - `Taux-BdC-macOS.zip` — Mac (SwiftUI `.app` when published; until then build from `macos/`)  
   - `Taux-BdC-Windows.zip` — Windows (Python / PyInstaller)

### macOS (SwiftUI — recommended)

1. Install **Xcode** from the App Store  
2. Open the project:

```bash
open macos/TauxBdC/TauxBdC.xcodeproj
```

3. Run ▶ on **My Mac**  

Full instructions: [`macos/README.md`](macos/README.md)

### Windows

1. Unzip the Windows release  
2. Double-click **Taux-BdC.exe**  
3. If SmartScreen: **More info** → **Run anyway**

Each ZIP includes `modele_lot.csv` when packaged.

---

## Flash CLI (fastest / le plus rapide)

```bash
# Rate only / taux seul
./taux 2026-07-05 usd
# or: python3 taux_bdc.py 2026-07-05 usd

# Convert amount / convertir un montant (+ optional invoice ref)
./taux 2026-07-05 usd 1500.00
./taux 2026-07-05 usd 1500.00 FAC-10443
```

Windows: `taux.bat 2026-07-05 usd 1500`

Add this folder to your `PATH` to type `taux …` from anywhere.

---

## App features / Fonctions

**Convert tab** — currency, date, amount → summary → Copy / Export CSV / Export Excel  

**Batch tab** — Import CSV or Excel → Process → Export results  

### Batch columns

| date | devise | montant | reference (optional) |
|------|--------|---------|----------------------|

Output adds: `date_taux`, `taux`, `montant_cad`, `serie`, `ajuste`, `erreur`.

### Cache & audit / Cache et piste d'audit

Stored next to the program in `data/` (preferred). If that folder is not writable (e.g. protected install), falls back to `~/.taux_bdc/`.

| File | Role |
|------|------|
| `data/cache_taux.json` | Rates already fetched (offline fallback) |
| `data/historique_conversions.log` | Timestamped audit lines for auditors |

---

## Develop from source / Développement

### macOS (SwiftUI)

See [`macos/README.md`](macos/README.md) — requires full **Xcode**.

```bash
open macos/TauxBdC/TauxBdC.xcodeproj
```

### Windows / CLI (Python)

Requires Python 3.10+ and `openpyxl`:

```bash
pip install -r requirements.txt
python3 gui_taux_bdc.py                    # GUI (Windows / fallback Mac)
python3 taux_bdc.py                        # terminal interactive
./taux 2026-07-05 usd 1500.00              # Flash CLI
```

### Build Windows with PyInstaller

```bat
scripts\build_windows.bat
```

(The GitHub Actions release still builds the Windows ZIP automatically.)

---

## Automated releases (GitHub Actions)

```bash
git tag v0.2.0
git push origin v0.2.0
```

Or **Actions** → **Release builds** → **Run workflow**.

---

## LinkedIn post (template)

> Free tool for Canadian accountants: official Bank of Canada FX → CAD.  
> Desktop app (Mac/Windows), FR/EN, single + batch CSV/Excel. No Python.  
>  
> macOS → [Taux-BdC-macOS.zip]  
> Windows → [Taux-BdC-Windows.zip]  

---

## License

MIT — see [LICENSE](LICENSE). Data via [Bank of Canada Valet](https://www.bankofcanada.ca/valet/).
