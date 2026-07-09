#!/usr/bin/env python3
"""
CLI tool — Bank of Canada (Valet) exchange rates for journal entries.
Outil CLI — taux de change Banque du Canada (Valet) pour écritures comptables.

- Multi-currency → CAD / Multi-devises → CAD
- Decimal only (no float for amounts / rates)
- If no rate on the requested date (weekend / holiday), uses previous business day
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
from typing import Any, Literal, Optional

getcontext().prec = 28

VALET_BASE = "https://www.bankofcanada.ca/valet/observations"
LOOKBACK_DAYS = 14
TIMEOUT_SEC = 30

Lang = Literal["fr", "en"]
_lang: Lang = "fr"

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
        "arg_epilog": "Sans arguments : mode interactif guidé.",
        "arg_devise": "Code ISO de la devise (ex. USD, EUR)",
        "arg_date": "Date de la transaction (AAAA-MM-JJ ou JJ/MM/AAAA)",
        "arg_montant": "Montant en devise (ex. 1500.00)",
        "arg_lang": "Langue de l'interface (fr ou en). Défaut : fr",
        "arg_incomplet": (
            "En mode non-interactif, --devise, --date et --montant sont tous requis."
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
        "arg_epilog": "With no arguments: guided interactive mode.",
        "arg_devise": "ISO currency code (e.g. USD, EUR)",
        "arg_date": "Transaction date (YYYY-MM-DD or DD/MM/YYYY)",
        "arg_montant": "Amount in foreign currency (e.g. 1500.00)",
        "arg_lang": "Interface language (fr or en). Default: fr",
        "arg_incomplet": (
            "In non-interactive mode, --devise, --date and --montant are all required."
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

    @property
    def est_ajuste(self) -> bool:
        return self.date_demandee != self.date_taux


class TauxBdcError(Exception):
    """Erreur métier ou API pour l'outil taux BdC."""


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
    """
    devise = devise.strip().upper()
    serie, _libelle = serie_pour_devise(devise)
    debut = date_demande - timedelta(days=LOOKBACK_DAYS)
    url = (
        f"{VALET_BASE}/{serie}/json"
        f"?start_date={debut.isoformat()}"
        f"&end_date={date_demande.isoformat()}"
    )

    payload = _http_get_json(url)

    par_date: dict[date, Decimal] = {}
    for obs in payload.get("observations", []):
        raw_date = obs.get("d")
        cellule = obs.get(serie) or {}
        raw_valeur = cellule.get("v")
        if raw_date is None or raw_valeur is None:
            continue
        par_date[datetime.strptime(raw_date, "%Y-%m-%d").date()] = Decimal(str(raw_valeur))

    if not par_date:
        raise TauxBdcError(
            t(
                "err_aucun_taux_plage",
                serie=serie,
                debut=debut.isoformat(),
                fin=date_demande.isoformat(),
            )
        )

    curseur = date_demande
    while curseur >= debut:
        if curseur in par_date:
            return TauxChange(
                date_demandee=date_demande,
                date_taux=curseur,
                taux=par_date[curseur],
                serie=serie,
                devise=devise,
            )
        curseur -= timedelta(days=1)

    raise TauxBdcError(
        t("err_fenetre", date=date_demande.isoformat(), jours=LOOKBACK_DAYS)
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


def afficher_fiche(
    tx: TauxChange,
    montant_devise: Decimal,
    montant_cad: Decimal,
) -> None:
    """Affiche une fiche prête pour l'écriture comptable."""
    libelle = libelle_devise(tx.devise, tx.serie)
    note_ajustement = t("note_ajuste") if tx.est_ajuste else ""

    # Alignement simple des labels
    labels = [
        (t("fiche_devise"), f"{tx.devise} ({libelle})"),
        (t("fiche_date_tx"), tx.date_demandee.isoformat()),
        (t("fiche_date_taux"), f"{tx.date_taux.isoformat()}{note_ajustement}"),
        (t("fiche_taux", devise=tx.devise), formater_nombre(tx.taux)),
        (t("fiche_montant_devise"), f"{formater_nombre(montant_devise, 2)} {tx.devise}"),
        (t("fiche_montant_cad"), f"{formater_nombre(montant_cad, 2)} CAD"),
        (t("fiche_source"), t("fiche_source_val", serie=tx.serie)),
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
    print("\n".join(lignes))


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


def executer_conversion(devise: str, date_tx: date, montant: Decimal) -> None:
    print(t("recuperation"))
    tx = recuperer_taux(devise, date_tx)
    cad = convertir(montant, tx.taux)
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


def mode_cli(devise: str, date_texte: str, montant_texte: str) -> int:
    try:
        date_tx = _parse_date(date_texte)
        montant = _parse_montant(montant_texte)
        executer_conversion(devise, date_tx, montant)
        return 0
    except TauxBdcError as err:
        print(t("erreur_stderr", err=err), file=sys.stderr)
        return 1


def construire_parser() -> argparse.ArgumentParser:
    # Textes argparse en FR par défaut (avant set_lang) ; --lang documenté bilingue
    parser = argparse.ArgumentParser(
        description=MESSAGES["fr"]["arg_description"],
        epilog=MESSAGES["fr"]["arg_epilog"],
    )
    parser.add_argument("--devise", "-d", help=MESSAGES["fr"]["arg_devise"])
    parser.add_argument("--date", help=MESSAGES["fr"]["arg_date"])
    parser.add_argument("--montant", "-m", help=MESSAGES["fr"]["arg_montant"])
    parser.add_argument(
        "--lang",
        "-l",
        choices=("fr", "en"),
        default=None,
        help=MESSAGES["fr"]["arg_lang"],
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = construire_parser()
    args = parser.parse_args(argv)

    fournis = [args.devise, args.date, args.montant]
    if any(fournis) and not all(fournis):
        # Appliquer la langue si fournie avant le message d'erreur
        if args.lang:
            set_lang(args.lang)
        parser.error(t("arg_incomplet"))

    if args.lang:
        set_lang(args.lang)
    elif all(fournis):
        set_lang("fr")  # CLI sans --lang : français par défaut

    if all(fournis):
        return mode_cli(args.devise, args.date, args.montant)

    # Interactif : demander la langue sauf si --lang déjà fourni
    return mode_interactif(demander_langue=args.lang is None)


if __name__ == "__main__":
    sys.exit(main())
