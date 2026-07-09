#!/usr/bin/env python3
"""
CLI tool — Bank of Canada (Valet) exchange rates for journal entries.
Outil CLI — taux de change Banque du Canada (Valet) pour écritures comptables.

- Multi-currency → CAD / Multi-devises → CAD
- Decimal only (no float for amounts / rates)
- If no rate on the requested date (weekend / holiday), uses previous business day
- Local rate cache + audit log in ./data/ (fallback: ~/.taux_bdc/)
"""

from __future__ import annotations

import argparse
import json
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, getcontext
from pathlib import Path
from typing import Any, Literal, Optional

getcontext().prec = 28

VALET_BASE = "https://www.bankofcanada.ca/valet/observations"
LOOKBACK_DAYS = 14
TIMEOUT_SEC = 30

Lang = Literal["fr", "en"]
SourceTaux = Literal["api", "cache"]
_lang: Lang = "fr"
_data_dir_cache: Optional[Path] = None


def _install_root() -> Path:
    """Dossier où vit le programme (script ou binaire PyInstaller)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    ici = Path(__file__).resolve().parent
    # Le code vit dans <projet>/python/ — data/ reste à la racine du projet
    if ici.name == "python":
        return ici.parent
    return ici


def _dossier_inscriptible(chemin: Path) -> bool:
    """Crée le dossier et vérifie qu'on peut y écrire."""
    try:
        chemin.mkdir(parents=True, exist_ok=True)
        sonde = chemin / ".write_test"
        sonde.write_text("ok", encoding="utf-8")
        sonde.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def data_dir() -> Path:
    """
    Cache + journal d'audit :
    1. <dossier_du_programme>/data/  (priorité — visible avec l'outil)
    2. ~/.taux_bdc/                 (repli si non inscriptible)
    """
    global _data_dir_cache
    if _data_dir_cache is not None:
        return _data_dir_cache

    local = _install_root() / "data"
    if _dossier_inscriptible(local):
        _data_dir_cache = local
        return local

    fallback = Path.home() / ".taux_bdc"
    fallback.mkdir(parents=True, exist_ok=True)
    _data_dir_cache = fallback
    return fallback


def cache_path() -> Path:
    return data_dir() / "cache_taux.json"


def audit_log_path() -> Path:
    return data_dir() / "historique_conversions.log"

# Code ISO → (série Valet, libellé FR, libellé EN)
DEVISES: dict[str, tuple[str, str, str]] = {
    "USD": ("FXUSDCAD", "Dollar américain", "US dollar"),
    "EUR": ("FXEURCAD", "Euro", "Euro"),
    "GBP": ("FXGBPCAD", "Livre sterling", "Pound sterling"),
    "CHF": ("FXCHFCAD", "Franc suisse", "Swiss franc"),
    "JPY": ("FXJPYCAD", "Yen japonais", "Japanese yen"),
    "AUD": ("FXAUDCAD", "Dollar australien", "Australian dollar"),
    "NZD": ("FXNZDCAD", "Dollar néo-zélandais", "New Zealand dollar"),
    "CNY": ("FXCNYCAD", "Renminbi chinois", "Chinese renminbi"),
    "HKD": ("FXHKDCAD", "Dollar de Hong Kong", "Hong Kong dollar"),
    "MXN": ("FXMXNCAD", "Peso mexicain", "Mexican peso"),
    "INR": ("FXINRCAD", "Roupie indienne", "Indian rupee"),
    "KRW": ("FXKRWCAD", "Won sud-coréen", "South Korean won"),
    "SGD": ("FXSGDCAD", "Dollar de Singapour", "Singapore dollar"),
    "SEK": ("FXSEKCAD", "Couronne suédoise", "Swedish krona"),
    "NOK": ("FXNOKCAD", "Couronne norvégienne", "Norwegian krone"),
    "BRL": ("FXBRLCAD", "Real brésilien", "Brazilian real"),
    "ZAR": ("FXZARCAD", "Rand sud-africain", "South African rand"),
    "TRY": ("FXTRYCAD", "Livre turque", "Turkish lira"),
    "THB": ("FXTHBCAD", "Baht thaïlandais", "Thai baht"),
    "TWD": ("FXTWDCAD", "Dollar taïwanais", "Taiwan dollar"),
    "MYR": ("FXMYRCAD", "Ringgit malaisien", "Malaysian ringgit"),
    "IDR": ("FXIDRCAD", "Roupie indonésienne", "Indonesian rupiah"),
    "VND": ("FXVNDCAD", "Dong vietnamien", "Vietnamese dong"),
    "PEN": ("FXPENCAD", "Sol péruvien", "Peruvian sol"),
    "SAR": ("FXSARCAD", "Riyal saoudien", "Saudi riyal"),
    "RUB": ("FXRUBCAD", "Rouble russe", "Russian ruble"),
}

MESSAGES: dict[Lang, dict[str, str]] = {
    "fr": {
        "titre": "Taux de change — Banque du Canada",
        "sous_titre": "Conversion devise → CAD (écritures)",
        "choix_langue": "Langue / Language : 1) Français  2) English : ",
        "langue_invalide": "  → Entrez 1 ou 2 / Enter 1 or 2.",
        "devises_courantes": "\nDevises courantes :",
        "autre_iso": "  (ou saisissez un autre code ISO à 3 lettres)",
        "prompt_devise": "\nDevise (ex. USD) : ",
        "devise_vide": "  → Veuillez indiquer un code devise.",
        "prompt_date": "Date de la transaction (AAAA-MM-JJ ou JJ/MM/AAAA) : ",
        "date_vide": "  → Veuillez indiquer une date.",
        "prompt_montant": "Montant en devise (ex. 1500,00) : ",
        "montant_vide": "  → Veuillez indiquer un montant.",
        "oui_non_invalide": "  → Répondez par oui ou non (yes/no).",
        "autre_conversion": "\nAutre conversion ? (oui/non) : ",
        "recuperation": "\n  Récupération du taux Banque du Canada…",
        "au_revoir": "Au revoir.",
        "interrompu": "\n\nInterrompu. Au revoir.",
        "erreur_prefixe": "\nErreur : {err}\n",
        "erreur_stderr": "Erreur : {err}",
        "fiche_titre": "ÉCRITURE — CONVERSION DEVISE",
        "fiche_devise": "Devise",
        "fiche_date_tx": "Date transaction",
        "fiche_date_taux": "Date taux BdC",
        "fiche_taux": "Taux (1 {devise} = CAD)",
        "fiche_montant_devise": "Montant devise",
        "fiche_montant_cad": "Montant CAD",
        "fiche_source": "Source",
        "fiche_source_val": "Banque du Canada (Valet / {serie})",
        "note_ajuste": "  ← ajustée (week-end/férié)",
        "libelle_generique": "Devise {code}",
        "err_cad": "CAD est déjà la devise de référence — aucune conversion nécessaire.",
        "err_code_invalide": "Code devise invalide : « {code} ». Utilisez un code ISO à 3 lettres (ex. USD).",
        "err_date_invalide": "Date invalide : « {texte} ». Formats acceptés : AAAA-MM-JJ ou JJ/MM/AAAA.",
        "err_montant_vide": "Le montant ne peut pas être vide.",
        "err_montant_invalide": "Montant invalide : « {texte} ».",
        "err_montant_positif": "Le montant doit être strictement positif.",
        "err_saisie": "Saisie interrompue.",
        "err_serie_404": (
            "Série Valet introuvable (HTTP 404). "
            "Vérifiez le code ISO auprès de la Banque du Canada."
        ),
        "err_json": "Réponse Valet illisible (JSON invalide).",
        "err_reseau": "Impossible de joindre l'API Valet : {detail}",
        "err_aucun_taux_plage": "Aucun taux {serie} publié entre {debut} et {fin}.",
        "err_fenetre": "Aucun taux publié pour {date} (fenêtre de {jours} jours épuisée).",
        "arg_description": (
            "Récupère un taux de change officiel Banque du Canada (Valet) "
            "et convertit un montant devise → CAD pour une écriture comptable."
        ),
        "arg_epilog": (
            "Sans arguments : mode interactif. "
            "Flash : python3 taux_bdc.py 2026-06-15 usd [montant] [référence]"
        ),
        "arg_devise": "Code ISO de la devise (ex. USD, EUR)",
        "arg_date": "Date de la transaction (AAAA-MM-JJ ou JJ/MM/AAAA)",
        "arg_montant": "Montant en devise (ex. 1500.00)",
        "arg_lang": "Langue de l'interface (fr ou en). Défaut : fr",
        "arg_reference": "Référence facture (optionnel, journal d'audit)",
        "arg_flash": "Mode Flash : DATE DEVISE [MONTANT] [REFERENCE]",
        "arg_incomplet": (
            "Fournissez --devise, --date et --montant, "
            "ou le mode Flash : DATE DEVISE [MONTANT]."
        ),
        "flash_taux_seul": (
            "  {devise}/CAD  date {date_tx} → taux BdC {date_taux} : {taux}"
            "{note}\n  Source : {source}"
        ),
    },
    "en": {
        "titre": "Exchange rates — Bank of Canada",
        "sous_titre": "Foreign currency → CAD (journal entries)",
        "choix_langue": "Langue / Language : 1) Français  2) English : ",
        "langue_invalide": "  → Entrez 1 ou 2 / Enter 1 or 2.",
        "devises_courantes": "\nCommon currencies:",
        "autre_iso": "  (or enter another 3-letter ISO code)",
        "prompt_devise": "\nCurrency (e.g. USD) : ",
        "devise_vide": "  → Please enter a currency code.",
        "prompt_date": "Transaction date (YYYY-MM-DD or DD/MM/YYYY) : ",
        "date_vide": "  → Please enter a date.",
        "prompt_montant": "Amount in foreign currency (e.g. 1500.00) : ",
        "montant_vide": "  → Please enter an amount.",
        "oui_non_invalide": "  → Please answer yes or no (oui/non).",
        "autre_conversion": "\nAnother conversion? (yes/no) : ",
        "recuperation": "\n  Fetching Bank of Canada rate…",
        "au_revoir": "Goodbye.",
        "interrompu": "\n\nInterrupted. Goodbye.",
        "erreur_prefixe": "\nError: {err}\n",
        "erreur_stderr": "Error: {err}",
        "fiche_titre": "JOURNAL ENTRY — FX CONVERSION",
        "fiche_devise": "Currency",
        "fiche_date_tx": "Transaction date",
        "fiche_date_taux": "BoC rate date",
        "fiche_taux": "Rate (1 {devise} = CAD)",
        "fiche_montant_devise": "Foreign amount",
        "fiche_montant_cad": "CAD amount",
        "fiche_source": "Source",
        "fiche_source_val": "Bank of Canada (Valet / {serie})",
        "note_ajuste": "  ← adjusted (weekend/holiday)",
        "libelle_generique": "Currency {code}",
        "err_cad": "CAD is already the base currency — no conversion needed.",
        "err_code_invalide": "Invalid currency code: '{code}'. Use a 3-letter ISO code (e.g. USD).",
        "err_date_invalide": "Invalid date: '{texte}'. Accepted formats: YYYY-MM-DD or DD/MM/YYYY.",
        "err_montant_vide": "Amount cannot be empty.",
        "err_montant_invalide": "Invalid amount: '{texte}'.",
        "err_montant_positif": "Amount must be strictly positive.",
        "err_saisie": "Input interrupted.",
        "err_serie_404": (
            "Valet series not found (HTTP 404). "
            "Check the ISO code with the Bank of Canada."
        ),
        "err_json": "Unreadable Valet response (invalid JSON).",
        "err_reseau": "Unable to reach the Valet API: {detail}",
        "err_aucun_taux_plage": "No {serie} rate published between {debut} and {fin}.",
        "err_fenetre": "No rate published for {date} ({jours}-day lookback exhausted).",
        "arg_description": (
            "Fetches an official Bank of Canada (Valet) exchange rate "
            "and converts a foreign amount to CAD for a journal entry."
        ),
        "arg_epilog": (
            "With no arguments: interactive mode. "
            "Flash: python3 taux_bdc.py 2026-06-15 usd [amount] [reference]"
        ),
        "arg_devise": "ISO currency code (e.g. USD, EUR)",
        "arg_date": "Transaction date (YYYY-MM-DD or DD/MM/YYYY)",
        "arg_montant": "Amount in foreign currency (e.g. 1500.00)",
        "arg_lang": "Interface language (fr or en). Default: fr",
        "arg_reference": "Invoice reference (optional, for audit log)",
        "arg_flash": "Flash mode: DATE CURRENCY [AMOUNT] [REFERENCE]",
        "arg_incomplet": (
            "Provide --devise, --date and --montant, "
            "or Flash mode: DATE CURRENCY [AMOUNT]."
        ),
        "flash_taux_seul": (
            "  {devise}/CAD  date {date_tx} → BoC rate {date_taux} : {taux}"
            "{note}\n  Source: {source}"
        ),
    },
}


def set_lang(lang: Lang) -> None:
    global _lang
    _lang = lang


def get_lang() -> Lang:
    return _lang


def t(cle: str, **kwargs: Any) -> str:
    texte = MESSAGES[_lang][cle]
    if kwargs:
        return texte.format(**kwargs)
    return texte


def libelle_devise(code: str, serie: str) -> str:
    if code in DEVISES:
        _serie, fr, en = DEVISES[code]
        return fr if _lang == "fr" else en
    return t("libelle_generique", code=code)


@dataclass(frozen=True)
class TauxChange:
    date_demandee: date
    date_taux: date
    taux: Decimal
    serie: str
    devise: str
    source: SourceTaux = "api"

    @property
    def est_ajuste(self) -> bool:
        return self.date_demandee != self.date_taux

    @property
    def libelle_source(self) -> str:
        if self.source == "cache":
            if _lang == "en":
                return f"Local cache (Valet / {self.serie})"
            return f"Cache local (Valet / {self.serie})"
        if _lang == "en":
            return f"Bank of Canada (Valet / {self.serie})"
        return f"Banque du Canada (Valet / {self.serie})"


class TauxBdcError(Exception):
    """Erreur métier ou API pour l'outil taux BdC."""


def _charger_cache() -> dict[str, dict[str, str]]:
    chemin = cache_path()
    if not chemin.exists():
        return {}
    try:
        data = json.loads(chemin.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {}


def _sauver_cache(cache: dict[str, dict[str, str]]) -> None:
    chemin = cache_path()
    tmp = chemin.with_suffix(".tmp")
    tmp.write_text(json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(chemin)


def _fusionner_cache(serie: str, observations: dict[date, Decimal]) -> None:
    if not observations:
        return
    cache = _charger_cache()
    bucket = cache.setdefault(serie, {})
    for d, taux in observations.items():
        bucket[d.isoformat()] = format(taux, "f")
    _sauver_cache(cache)


def _observations_depuis_cache(serie: str) -> dict[date, Decimal]:
    cache = _charger_cache()
    brut = cache.get(serie) or {}
    resultat: dict[date, Decimal] = {}
    for cle, val in brut.items():
        try:
            resultat[datetime.strptime(cle, "%Y-%m-%d").date()] = Decimal(str(val))
        except (ValueError, InvalidOperation):
            continue
    return resultat


def _resoudre_dans_carte(
    par_date: dict[date, Decimal],
    date_demande: date,
    debut: date,
) -> Optional[tuple[date, Decimal]]:
    curseur = date_demande
    while curseur >= debut:
        if curseur in par_date:
            return curseur, par_date[curseur]
        curseur -= timedelta(days=1)
    return None


def journaliser_conversion(
    tx: TauxChange,
    montant_devise: Decimal,
    montant_cad: Decimal,
    reference: str = "",
) -> None:
    """Ajoute une ligne horodatée dans historique_conversions.log (piste d'audit)."""
    horodatage = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ref = reference.strip()
    if ref:
        sujet = f"Facture n° {ref}" if _lang == "fr" else f"Invoice #{ref}"
    else:
        sujet = "Conversion" if _lang == "en" else "Conversion"
    if _lang == "en":
        ligne = (
            f"[{horodatage}] {sujet} converted. "
            f"Requested date: {tx.date_demandee.isoformat()}. "
            f"Rate applied: {format(tx.taux, 'f')} "
            f"(BoC date: {tx.date_taux.isoformat()}). "
            f"Amount: {format(montant_devise, 'f')} {tx.devise} → "
            f"{format(montant_cad, 'f')} CAD. "
            f"Source: {tx.libelle_source}."
        )
    else:
        ligne = (
            f"[{horodatage}] {sujet} convertie. "
            f"Date demandée: {tx.date_demandee.isoformat()}. "
            f"Taux appliqué: {format(tx.taux, 'f')} "
            f"(Date BdC: {tx.date_taux.isoformat()}). "
            f"Montant: {format(montant_devise, 'f')} {tx.devise} → "
            f"{format(montant_cad, 'f')} CAD. "
            f"Source: {tx.libelle_source}."
        )
    try:
        with audit_log_path().open("a", encoding="utf-8") as f:
            f.write(ligne + "\n")
    except OSError:
        # Ne jamais faire échouer une conversion à cause du journal
        pass


def serie_pour_devise(code: str) -> tuple[str, str]:
    """Retourne (série Valet, libellé localisé) pour un code ISO."""
    code = code.strip().upper()
    if code == "CAD":
        raise TauxBdcError(t("err_cad"))
    if code in DEVISES:
        serie, fr, en = DEVISES[code]
        return serie, (fr if _lang == "fr" else en)
    if len(code) == 3 and code.isalpha():
        serie = f"FX{code}CAD"
        return serie, t("libelle_generique", code=code)
    raise TauxBdcError(t("err_code_invalide", code=code))


def _parse_date(texte: str) -> date:
    """Accepte AAAA-MM-JJ, JJ/MM/AAAA, JJ-MM-AAAA."""
    texte = texte.strip()
    formats = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d")
    for fmt in formats:
        try:
            return datetime.strptime(texte, fmt).date()
        except ValueError:
            continue
    raise TauxBdcError(t("err_date_invalide", texte=texte))


def _parse_montant(texte: str) -> Decimal:
    """Parse un montant saisi (virgule ou point décimal, espaces ignorés)."""
    nettoye = (
        texte.strip()
        .replace(" ", "")
        .replace("\u00a0", "")
        .replace(",", ".")
    )
    if not nettoye:
        raise TauxBdcError(t("err_montant_vide"))
    try:
        montant = Decimal(nettoye)
    except InvalidOperation as exc:
        raise TauxBdcError(t("err_montant_invalide", texte=texte)) from exc
    if montant <= 0:
        raise TauxBdcError(t("err_montant_positif"))
    return montant


def _ssl_contexts() -> list[ssl.SSLContext]:
    """Contextes SSL à essayer (défaut Python, puis certifi si dispo)."""
    contexts = [ssl.create_default_context()]
    try:
        import certifi  # type: ignore

        contexts.append(ssl.create_default_context(cafile=certifi.where()))
    except Exception:
        pass
    return contexts


def _http_get_json(url: str) -> dict[str, Any]:
    """
    GET JSON depuis Valet.
    Essaie urllib (plusieurs contextes SSL), puis curl en secours (macOS / proxy).
    """
    headers = {"User-Agent": "taux-bdc-comptable/1.0"}
    last_error: Optional[Exception] = None

    for ctx in _ssl_contexts():
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=TIMEOUT_SEC, context=ctx) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise TauxBdcError(t("err_serie_404")) from exc
            last_error = exc
        except (urllib.error.URLError, ssl.SSLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc

    try:
        result = subprocess.run(
            [
                "curl",
                "-fsS",
                "--max-time",
                str(TIMEOUT_SEC),
                "-H",
                "User-Agent: taux-bdc-comptable/1.0",
                url,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout:
            return json.loads(result.stdout)
        detail = (result.stderr or result.stdout or "").strip()
        if "404" in detail:
            raise TauxBdcError(t("err_serie_404"))
        last_error = RuntimeError(detail or f"curl exit {result.returncode}")
    except FileNotFoundError as exc:
        last_error = exc
    except json.JSONDecodeError as exc:
        raise TauxBdcError(t("err_json")) from exc

    raise TauxBdcError(t("err_reseau", detail=last_error))


def recuperer_taux(devise: str, date_demande: date) -> TauxChange:
    """
    Récupère le taux BdC pour 1 unité de devise → CAD.
    Si absent à la date demandée, remonte au dernier jour ouvré publié.
    Essaie le cache local si l'API est indisponible.
    """
    devise = devise.strip().upper()
    serie, _libelle = serie_pour_devise(devise)
    debut = date_demande - timedelta(days=LOOKBACK_DAYS)
    url = (
        f"{VALET_BASE}/{serie}/json"
        f"?start_date={debut.isoformat()}"
        f"&end_date={date_demande.isoformat()}"
    )

    erreur_api: Optional[Exception] = None
    try:
        payload = _http_get_json(url)
        par_date: dict[date, Decimal] = {}
        for obs in payload.get("observations", []):
            raw_date = obs.get("d")
            cellule = obs.get(serie) or {}
            raw_valeur = cellule.get("v")
            if raw_date is None or raw_valeur is None:
                continue
            par_date[datetime.strptime(raw_date, "%Y-%m-%d").date()] = Decimal(str(raw_valeur))

        if par_date:
            _fusionner_cache(serie, par_date)
            resolu = _resoudre_dans_carte(par_date, date_demande, debut)
            if resolu is not None:
                date_taux, taux = resolu
                return TauxChange(
                    date_demandee=date_demande,
                    date_taux=date_taux,
                    taux=taux,
                    serie=serie,
                    devise=devise,
                    source="api",
                )
    except TauxBdcError as exc:
        erreur_api = exc

    # Secours : cache local (réseau coupé / API en panne)
    cache_obs = _observations_depuis_cache(serie)
    resolu_cache = _resoudre_dans_carte(cache_obs, date_demande, debut)
    if resolu_cache is not None:
        date_taux, taux = resolu_cache
        return TauxChange(
            date_demandee=date_demande,
            date_taux=date_taux,
            taux=taux,
            serie=serie,
            devise=devise,
            source="cache",
        )

    if erreur_api is not None:
        raise erreur_api

    raise TauxBdcError(
        t(
            "err_aucun_taux_plage",
            serie=serie,
            debut=debut.isoformat(),
            fin=date_demande.isoformat(),
        )
    )


def convertir(montant: Decimal, taux: Decimal, decimales: int = 2) -> Decimal:
    """Convertit un montant devise → CAD avec arrondi HALF_UP."""
    quantize = Decimal("1").scaleb(-decimales)
    return (montant * taux).quantize(quantize, rounding=ROUND_HALF_UP)


def formater_nombre(valeur: Decimal, decimales: Optional[int] = None) -> str:
    """Format selon la langue : FR 1 500,00 / EN 1,500.00."""
    if decimales is not None:
        quantize = Decimal("1").scaleb(-decimales)
        valeur = valeur.quantize(quantize, rounding=ROUND_HALF_UP)
    texte = format(valeur, "f")
    if "." in texte:
        entier, frac = texte.split(".", 1)
    else:
        entier, frac = texte, ""
    signe = ""
    if entier.startswith("-"):
        signe = "-"
        entier = entier[1:]
    groupes: list[str] = []
    while entier:
        groupes.append(entier[-3:])
        entier = entier[:-3]
    if _lang == "en":
        sep_milliers = ","
        sep_decimal = "."
    else:
        sep_milliers = " "
        sep_decimal = ","
    entier_fmt = sep_milliers.join(reversed(groupes))
    if frac:
        return f"{signe}{entier_fmt}{sep_decimal}{frac}"
    return f"{signe}{entier_fmt}"


def texte_fiche(
    tx: TauxChange,
    montant_devise: Decimal,
    montant_cad: Decimal,
) -> str:
    """Retourne le texte de fiche prêt pour écriture / copie / export."""
    libelle = libelle_devise(tx.devise, tx.serie)
    note_ajustement = t("note_ajuste") if tx.est_ajuste else ""

    labels = [
        (t("fiche_devise"), f"{tx.devise} ({libelle})"),
        (t("fiche_date_tx"), tx.date_demandee.isoformat()),
        (t("fiche_date_taux"), f"{tx.date_taux.isoformat()}{note_ajustement}"),
        (t("fiche_taux", devise=tx.devise), formater_nombre(tx.taux)),
        (t("fiche_montant_devise"), f"{formater_nombre(montant_devise, 2)} {tx.devise}"),
        (t("fiche_montant_cad"), f"{formater_nombre(montant_cad, 2)} CAD"),
        (t("fiche_source"), tx.libelle_source),
    ]
    largeur = max(len(lab) for lab, _ in labels)

    lignes = [
        "────────────────────────────────",
        f"  {t('fiche_titre')}",
        "────────────────────────────────",
    ]
    for lab, val in labels:
        lignes.append(f"  {lab:<{largeur}} : {val}")
    lignes.append("────────────────────────────────")
    return "\n".join(lignes)


def afficher_fiche(
    tx: TauxChange,
    montant_devise: Decimal,
    montant_cad: Decimal,
) -> None:
    """Affiche une fiche prête pour l'écriture comptable."""
    print(texte_fiche(tx, montant_devise, montant_cad))


# Alias publics pour GUI / import lot
parse_date = _parse_date
parse_montant = _parse_montant


def _demander(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError as exc:
        raise TauxBdcError(t("err_saisie")) from exc


def _choisir_langue() -> Lang:
    while True:
        brut = _demander(t("choix_langue"))
        if brut in ("1", "fr", "FR", "f", "F"):
            return "fr"
        if brut in ("2", "en", "EN", "e", "E"):
            return "en"
        print(t("langue_invalide"))


def _choisir_devise() -> str:
    print(t("devises_courantes"))
    codes = list(DEVISES.keys())
    for i in range(0, len(codes), 4):
        groupe = codes[i : i + 4]
        print("  " + "  ".join(f"{c:<6}" for c in groupe))
    print(t("autre_iso"))
    while True:
        brut = _demander(t("prompt_devise"))
        if not brut:
            print(t("devise_vide"))
            continue
        try:
            serie_pour_devise(brut)
            return brut.strip().upper()
        except TauxBdcError as err:
            print(f"  → {err}")


def _demander_date() -> date:
    while True:
        brut = _demander(t("prompt_date"))
        if not brut:
            print(t("date_vide"))
            continue
        try:
            return _parse_date(brut)
        except TauxBdcError as err:
            print(f"  → {err}")


def _demander_montant() -> Decimal:
    while True:
        brut = _demander(t("prompt_montant"))
        if not brut:
            print(t("montant_vide"))
            continue
        try:
            return _parse_montant(brut)
        except TauxBdcError as err:
            print(f"  → {err}")


def _oui_non(prompt: str) -> bool:
    while True:
        brut = _demander(prompt).lower()
        if brut in ("o", "oui", "y", "yes"):
            return True
        if brut in ("n", "non", "no"):
            return False
        print(t("oui_non_invalide"))


def executer_conversion(
    devise: str,
    date_tx: date,
    montant: Decimal,
    reference: str = "",
) -> None:
    print(t("recuperation"))
    tx = recuperer_taux(devise, date_tx)
    cad = convertir(montant, tx.taux)
    journaliser_conversion(tx, montant, cad, reference=reference)
    print()
    afficher_fiche(tx, montant, cad)


def mode_interactif(demander_langue: bool = True) -> int:
    if demander_langue:
        set_lang(_choisir_langue())

    print("=" * 40)
    print(f"  {t('titre')}")
    print(f"  {t('sous_titre')}")
    print("=" * 40)

    while True:
        try:
            devise = _choisir_devise()
            date_tx = _demander_date()
            montant = _demander_montant()
            executer_conversion(devise, date_tx, montant)
        except TauxBdcError as err:
            print(t("erreur_prefixe", err=err))
        except KeyboardInterrupt:
            print(t("interrompu"))
            return 0

        if not _oui_non(t("autre_conversion")):
            print(t("au_revoir"))
            return 0


def mode_cli(
    devise: str,
    date_texte: str,
    montant_texte: Optional[str] = None,
    reference: str = "",
) -> int:
    """Mode non-interactif / Flash. Sans montant : affiche seulement le taux."""
    try:
        date_tx = _parse_date(date_texte)
        if montant_texte is None or str(montant_texte).strip() == "":
            print(t("recuperation"))
            tx = recuperer_taux(devise, date_tx)
            note = t("note_ajuste") if tx.est_ajuste else ""
            print(
                t(
                    "flash_taux_seul",
                    devise=tx.devise,
                    date_tx=tx.date_demandee.isoformat(),
                    date_taux=tx.date_taux.isoformat(),
                    taux=formater_nombre(tx.taux),
                    note=note,
                    source=tx.libelle_source,
                )
            )
            # Journal audit même pour une consultation de taux (montant 0 non journalisé)
            return 0
        montant = _parse_montant(montant_texte)
        executer_conversion(devise, date_tx, montant, reference=reference)
        return 0
    except TauxBdcError as err:
        print(t("erreur_stderr", err=err), file=sys.stderr)
        return 1


def construire_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=MESSAGES["fr"]["arg_description"],
        epilog=MESSAGES["fr"]["arg_epilog"],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "flash",
        nargs="*",
        metavar="ARG",
        help=MESSAGES["fr"]["arg_flash"],
    )
    parser.add_argument("--devise", "-d", help=MESSAGES["fr"]["arg_devise"])
    parser.add_argument("--date", help=MESSAGES["fr"]["arg_date"])
    parser.add_argument("--montant", "-m", help=MESSAGES["fr"]["arg_montant"])
    parser.add_argument("--reference", "-r", default="", help=MESSAGES["fr"]["arg_reference"])
    parser.add_argument(
        "--lang",
        "-l",
        choices=("fr", "en"),
        default=None,
        help=MESSAGES["fr"]["arg_lang"],
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Force le mode terminal interactif.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = construire_parser()
    args = parser.parse_args(argv)

    if args.lang:
        set_lang(args.lang)

    # Mode Flash positionnel : DATE DEVISE [MONTANT] [REFERENCE]
    flash = list(args.flash or [])
    if flash:
        if len(flash) < 2:
            parser.error(t("arg_incomplet"))
        if args.lang is None:
            set_lang("fr")
        date_texte = flash[0]
        devise = flash[1]
        montant_texte = flash[2] if len(flash) >= 3 else None
        reference = flash[3] if len(flash) >= 4 else (args.reference or "")
        return mode_cli(devise, date_texte, montant_texte, reference=reference)

    fournis = [args.devise, args.date, args.montant]
    if any(fournis) and not all(fournis):
        if args.lang is None:
            set_lang("fr")
        parser.error(t("arg_incomplet"))

    if all(fournis):
        if args.lang is None:
            set_lang("fr")
        return mode_cli(args.devise, args.date, args.montant, reference=args.reference or "")

    # Interactif terminal
    return mode_interactif(demander_langue=args.lang is None)


if __name__ == "__main__":
    sys.exit(main())
