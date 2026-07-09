# Taux BdC — Bank of Canada exchange rates / Taux de change Banque du Canada

CLI tool for Canadian accountants: official Bank of Canada (Valet) FX rates → CAD for journal entries.

Outil CLI pour comptables au Canada : taux officiels Banque du Canada (Valet) → CAD pour les écritures.

- Multi-currency / Multi-devises → CAD  
- French & English / Français et anglais  
- `Decimal` only (no binary float rounding)  
- If no rate on the date (weekend / holiday), uses the previous published business day  

**Not affiliated with the Bank of Canada.** Rates are indicative only.  
**Non affilié à la Banque du Canada.** Les taux sont indicatifs seulement.

---

## Download for LinkedIn followers / Téléchargement

Get the latest **Release** assets (no Python required):

1. Open **Releases** on this repository  
2. Download **one** of:
   - `Taux-BdC-macOS.zip` — for Mac  
   - `Taux-BdC-Windows.zip` — for Windows  

### macOS

1. Unzip  
2. Double-click **Ouvrir Taux BdC.command**  
3. If Gatekeeper blocks: right-click → **Open** → **Open**

### Windows

1. Unzip  
2. Double-click **Taux-BdC.exe**  
3. If SmartScreen appears: **More info** → **Run anyway**

---

## Usage / Utilisation

Interactive (recommended):

```text
Language: 1) Français  2) English
→ currency → date → amount → journal-entry style summary
```

Command line:

```bash
# French (default)
./Taux-BdC --devise USD --date 2026-07-05 --montant 1500.00

# English
./Taux-BdC --lang en --devise USD --date 2026-07-05 --montant 1500.00
```

On Windows, use `Taux-BdC.exe` with the same flags.

---

## Develop from source / Développement

Requires Python 3.10+.

```bash
python3 taux_bdc.py
# or
python3 taux_bdc.py --lang en --devise EUR --date 2026-07-08 --montant 1000.50
```

Local launchers (need Python installed): `Taux BdC.command` (macOS), `Taux BdC.bat` (Windows).

### Build locally with PyInstaller

```bash
pip install pyinstaller
# macOS / Linux
./scripts/build_macos.sh
# Windows (Command Prompt)
scripts\build_windows.bat
```

---

## Automated releases (GitHub Actions)

Push a version tag to build both ZIPs and attach them to a GitHub Release:

```bash
git tag v0.1.0
git push origin v0.1.0
```

Or run the workflow manually: **Actions** → **Release builds** → **Run workflow**.

---

## LinkedIn post (template)

> Free tool for Canadian accountants: official Bank of Canada FX rates → CAD for journal entries.  
> Multi-currency, FR/EN, handles weekends/holidays automatically. No Python install.  
>  
> Download:  
> macOS → [link to Taux-BdC-macOS.zip on Releases]  
> Windows → [link to Taux-BdC-Windows.zip on Releases]  
>  
> Unzip → double-click.  

---

## License

MIT — see [LICENSE](LICENSE). Data via [Bank of Canada Valet](https://www.bankofcanada.ca/valet/).
