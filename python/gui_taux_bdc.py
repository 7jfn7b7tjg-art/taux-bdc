#!/usr/bin/env python3
"""
Interface graphique — taux de change Banque du Canada (unitaire + lot + historique).
GUI — Bank of Canada FX rates, feature parity with macOS SwiftUI app.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import tkinter as tk
from datetime import date
from decimal import Decimal
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Optional

import taux_bdc as core
from io_ecritures import (
    LigneLot,
    creer_modele_csv,
    creer_modele_xlsx,
    ecrire_fichier,
    lire_fichier,
    traiter_ligne,
)

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    HAS_DND = True
except ImportError:
    HAS_DND = False

# Palette — teal / or (finance)
COLOR_BG = "#F4F7F7"
COLOR_HEADER = "#0B6E6E"
COLOR_HEADER_FG = "#F7F3E8"
COLOR_ACCENT = "#C4A35A"
COLOR_CARD = "#FFFFFF"
COLOR_TEXT = "#1A2B2B"
COLOR_MUTED = "#5A6F6F"
COLOR_RESULT_BG = "#0F2F2F"
COLOR_RESULT_FG = "#E8F2F2"

IMPORT_EXTENSIONS = {".csv", ".xlsx", ".xlsm", ".json", ".xml", ".txt"}


def _resource_path(*parts: str) -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(getattr(sys, "_MEIPASS"))
    else:
        base = Path(__file__).resolve().parent
    return base.joinpath(*parts)


def _prefs_path() -> Path:
    return core.data_dir() / "prefs_gui.json"


def _load_prefs() -> dict[str, str]:
    path = _prefs_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_prefs(prefs: dict[str, str]) -> None:
    try:
        _prefs_path().write_text(
            json.dumps(prefs, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass


def _open_data_folder() -> None:
    folder = str(core.data_dir())
    try:
        if sys.platform == "win32":
            os.startfile(folder)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", folder], check=False)
        else:
            subprocess.run(["xdg-open", folder], check=False)
    except OSError as exc:
        messagebox.showerror("Error", str(exc))


GUI_MSG = {
    "fr": {
        "window_title": "Taux BdC — Banque du Canada",
        "brand": "Taux BdC",
        "tagline": "Taux officiels · Écritures comptables",
        "lang": "Langue",
        "tab_single": "Conversion",
        "tab_batch": "Lots",
        "tab_history": "Historique",
        "currency": "Devise",
        "date": "Date transaction",
        "amount": "Montant",
        "reference": "Référence (opt.)",
        "convert": "Convertir",
        "copy": "Copier",
        "copy_full": "Fiche complète",
        "copy_amount": "Montant converti seul",
        "copy_tsv": "Ligne tabulée (Excel / journal)",
        "export_csv": "Exporter CSV",
        "export_xlsx": "Exporter Excel",
        "result": "Résultat",
        "import_file": "Importer un fichier…",
        "save_template": "Enregistrer un modèle…",
        "process": "Traiter le lot",
        "export_result": "Exporter le résultat…",
        "export_csv_btn": "CSV",
        "export_json_btn": "JSON",
        "export_xml_btn": "XML",
        "progress": "Progression",
        "ready": "Prêt.",
        "converting": "Récupération du taux…",
        "done": "Terminé.",
        "copied": "Copié dans le presse-papiers.",
        "exported": "Fichier enregistré :\n{path}",
        "no_result": "Aucune conversion à exporter.",
        "no_rows": "Importez ou glissez-déposez un fichier ici.",
        "confirm_process": "Traiter {n} ligne(s) ? (appel API Banque du Canada)",
        "batch_done": "Lot terminé : {ok} OK, {err} erreur(s).",
        "err_title": "Erreur",
        "info_title": "Information",
        "date_hint": "AAAA-MM-JJ ou JJ/MM/AAAA",
        "amount_hint": "ex. 1500,00",
        "direction": "Sens",
        "to_cad": "{ccy} → CAD",
        "from_cad": "CAD → {ccy}",
        "rate_mode": "Type de taux",
        "mode_daily": "Taux du jour",
        "mode_monthly": "Moyenne mensuelle",
        "mode_annual": "Moyenne annuelle",
        "month": "Mois",
        "year": "Année",
        "drop_hint": "Glissez-déposez un fichier CSV, Excel, JSON ou XML",
        "search_placeholder": "Rechercher…",
        "export_txt": "Exporter…",
        "show_folder": "Ouvrir dossier data",
        "clear_history": "Effacer l'historique…",
        "clear_confirm_title": "Effacer tout l'historique ?",
        "clear_confirm_message": (
            "Une sauvegarde horodatée sera créée dans data/sauvegardes/ avant l'effacement."
        ),
        "cleared_status": "Historique effacé — sauvegarde : {fichier}",
        "no_history": "Aucune conversion journalisée pour l'instant.",
        "history_count": "{n} entrée(s)",
        "dnd_unavailable": "Glisser-déposer indisponible — utilisez Importer.",
        "cols": (
            "date",
            "devise",
            "montant",
            "référence",
            "date_taux",
            "taux",
            "CAD",
            "ajusté",
            "erreur",
        ),
    },
    "en": {
        "window_title": "BoC Rates — Bank of Canada",
        "brand": "BoC Rates",
        "tagline": "Official rates · Journal entries",
        "lang": "Language",
        "tab_single": "Convert",
        "tab_batch": "Batches",
        "tab_history": "History",
        "currency": "Currency",
        "date": "Transaction date",
        "amount": "Amount",
        "reference": "Reference (opt.)",
        "convert": "Convert",
        "copy": "Copy",
        "copy_full": "Full summary",
        "copy_amount": "Converted amount only",
        "copy_tsv": "Tab-separated row (Excel / journal)",
        "export_csv": "Export CSV",
        "export_xlsx": "Export Excel",
        "result": "Result",
        "import_file": "Import file…",
        "save_template": "Save template…",
        "process": "Process batch",
        "export_result": "Export results…",
        "export_csv_btn": "CSV",
        "export_json_btn": "JSON",
        "export_xml_btn": "XML",
        "progress": "Progress",
        "ready": "Ready.",
        "converting": "Fetching rate…",
        "done": "Done.",
        "copied": "Copied to clipboard.",
        "exported": "File saved:\n{path}",
        "no_result": "Nothing to export yet.",
        "no_rows": "Import or drop a file here.",
        "confirm_process": "Process {n} row(s)? (Bank of Canada API calls)",
        "batch_done": "Batch done: {ok} OK, {err} error(s).",
        "err_title": "Error",
        "info_title": "Information",
        "date_hint": "YYYY-MM-DD or DD/MM/YYYY",
        "amount_hint": "e.g. 1500.00",
        "direction": "Direction",
        "to_cad": "{ccy} → CAD",
        "from_cad": "CAD → {ccy}",
        "rate_mode": "Rate type",
        "mode_daily": "Daily rate",
        "mode_monthly": "Monthly average",
        "mode_annual": "Annual average",
        "month": "Month",
        "year": "Year",
        "drop_hint": "Drag & drop CSV, Excel, JSON or XML",
        "search_placeholder": "Search…",
        "export_txt": "Export…",
        "show_folder": "Open data folder",
        "clear_history": "Clear history…",
        "clear_confirm_title": "Clear all history?",
        "clear_confirm_message": (
            "A timestamped backup will be saved to data/sauvegardes/ before clearing."
        ),
        "cleared_status": "History cleared — backup: {fichier}",
        "no_history": "No logged conversions yet.",
        "history_count": "{n} entry(ies)",
        "dnd_unavailable": "Drag & drop unavailable — use Import.",
        "cols": (
            "date",
            "currency",
            "amount",
            "reference",
            "rate_date",
            "rate",
            "CAD",
            "adjusted",
            "error",
        ),
    },
}


def g(cle: str, **kwargs: object) -> str:
    texte = GUI_MSG[core.get_lang()][cle]
    if kwargs:
        return str(texte).format(**kwargs)
    return str(texte)


_BaseTk = TkinterDnD.Tk if HAS_DND else tk.Tk


class App(_BaseTk):
    def __init__(self) -> None:
        super().__init__()
        self.resultat: Optional[core.ResultatConversion] = None
        self.lignes: list[LigneLot] = []
        self._busy = False
        self._logo_image: Optional[tk.PhotoImage] = None
        self._history_entries: list[str] = []

        prefs = _load_prefs()
        self.direction_var = tk.StringVar(value=prefs.get("direction", "to_cad"))
        self.rate_mode_var = tk.StringVar(value=prefs.get("rate_mode", "daily"))
        self.month_var = tk.StringVar(value=prefs.get("month", str(date.today().month)))
        self.year_var = tk.StringVar(value=prefs.get("year", str(date.today().year)))

        self.title(g("window_title"))
        self.minsize(820, 600)
        self.geometry("960x700")
        self.configure(bg=COLOR_BG)
        self._set_window_icon()
        self._setup_style()
        self._build()
        self._refresh_texts()
        self._update_rate_mode_ui()
        self._update_direction_labels()

    def _set_window_icon(self) -> None:
        for candidate in (
            _resource_path("packaging", "assets", "logo_128.png"),
            _resource_path("packaging", "assets", "app_icon.png"),
        ):
            if candidate.exists():
                try:
                    icon = tk.PhotoImage(file=str(candidate))
                    self.iconphoto(True, icon)
                    self._window_icon = icon
                except tk.TclError:
                    pass
                break

    def _setup_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", background=COLOR_BG, foreground=COLOR_TEXT, font=("Segoe UI", 11))
        style.configure("TFrame", background=COLOR_BG)
        style.configure("Card.TFrame", background=COLOR_CARD)
        style.configure("Header.TFrame", background=COLOR_HEADER)
        style.configure("Header.TLabel", background=COLOR_HEADER, foreground=COLOR_HEADER_FG)
        style.configure(
            "Brand.TLabel",
            background=COLOR_HEADER,
            foreground=COLOR_HEADER_FG,
            font=("Segoe UI", 18, "bold"),
        )
        style.configure(
            "Tag.TLabel",
            background=COLOR_HEADER,
            foreground=COLOR_ACCENT,
            font=("Segoe UI", 10),
        )
        style.configure("TLabel", background=COLOR_BG, foreground=COLOR_TEXT)
        style.configure("Muted.TLabel", background=COLOR_BG, foreground=COLOR_MUTED)
        style.configure("Card.TLabel", background=COLOR_CARD, foreground=COLOR_TEXT)
        style.configure("TButton", padding=(12, 6))
        style.configure("Accent.TButton", padding=(14, 8), font=("Segoe UI", 11, "bold"))
        style.configure("Danger.TButton", padding=(12, 6))
        style.configure("TNotebook", background=COLOR_BG, borderwidth=0)
        style.configure("TNotebook.Tab", padding=(14, 8))
        style.configure("Treeview", rowheight=26, font=("Segoe UI", 10), fieldbackground=COLOR_CARD)
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        style.configure("Horizontal.TProgressbar", troughcolor="#D9E4E4", background=COLOR_HEADER)
        style.configure("Status.TLabel", background="#E7EEEE", foreground=COLOR_MUTED, padding=(10, 6))

    def _build(self) -> None:
        header = ttk.Frame(self, style="Header.TFrame", padding=(16, 12))
        header.pack(fill=tk.X)

        brand_row = ttk.Frame(header, style="Header.TFrame")
        brand_row.pack(side=tk.LEFT, fill=tk.X, expand=True)
        titles = ttk.Frame(brand_row, style="Header.TFrame")
        titles.pack(side=tk.LEFT)
        self.lbl_brand = ttk.Label(titles, text="", style="Brand.TLabel")
        self.lbl_brand.pack(anchor=tk.W)
        self.lbl_tagline = ttk.Label(titles, text="", style="Tag.TLabel")
        self.lbl_tagline.pack(anchor=tk.W, pady=(2, 0))

        lang_box = ttk.Frame(header, style="Header.TFrame")
        lang_box.pack(side=tk.RIGHT)
        self.lbl_lang = ttk.Label(lang_box, text="", style="Header.TLabel")
        self.lbl_lang.pack(side=tk.LEFT, padx=(0, 6))
        self.lang_var = tk.StringVar(value="Français" if core.get_lang() == "fr" else "English")
        self.cmb_lang = ttk.Combobox(
            lang_box,
            textvariable=self.lang_var,
            values=("Français", "English"),
            state="readonly",
            width=12,
        )
        self.cmb_lang.pack(side=tk.LEFT)
        self.cmb_lang.bind("<<ComboboxSelected>>", self._on_lang)

        body = ttk.Frame(self, padding=12)
        body.pack(fill=tk.BOTH, expand=True)

        self.notebook = ttk.Notebook(body)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        self.tab_single = ttk.Frame(self.notebook, padding=14, style="Card.TFrame")
        self.tab_batch = ttk.Frame(self.notebook, padding=14, style="Card.TFrame")
        self.tab_history = ttk.Frame(self.notebook, padding=14, style="Card.TFrame")
        self.notebook.add(self.tab_single, text="")
        self.notebook.add(self.tab_batch, text="")
        self.notebook.add(self.tab_history, text="")

        self._build_single(self.tab_single)
        self._build_batch(self.tab_batch)
        self._build_history(self.tab_history)
        self._setup_dnd()

        self.status = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.status, style="Status.TLabel").pack(fill=tk.X, side=tk.BOTTOM)

    def _build_single(self, parent: ttk.Frame) -> None:
        form = ttk.Frame(parent, style="Card.TFrame")
        form.pack(fill=tk.X)
        row = 0

        self.lbl_ccy = ttk.Label(form, text="", style="Card.TLabel")
        self.lbl_ccy.grid(row=row, column=0, sticky=tk.W, pady=5)
        self.ccy_var = tk.StringVar(value="USD")
        self.cmb_ccy = ttk.Combobox(
            form, textvariable=self.ccy_var, values=list(core.DEVISES.keys()), width=12
        )
        self.cmb_ccy.grid(row=row, column=1, sticky=tk.W, padx=8)
        self.cmb_ccy.bind("<<ComboboxSelected>>", lambda _e: self._update_direction_labels())
        row += 1

        self.lbl_direction = ttk.Label(form, text="", style="Card.TLabel")
        self.lbl_direction.grid(row=row, column=0, sticky=tk.W, pady=5)
        dir_frame = ttk.Frame(form, style="Card.TFrame")
        dir_frame.grid(row=row, column=1, sticky=tk.W, padx=8)
        self.rb_to_cad = ttk.Radiobutton(
            dir_frame, variable=self.direction_var, value="to_cad", command=self._save_gui_prefs
        )
        self.rb_to_cad.pack(side=tk.LEFT, padx=(0, 12))
        self.rb_from_cad = ttk.Radiobutton(
            dir_frame, variable=self.direction_var, value="from_cad", command=self._save_gui_prefs
        )
        self.rb_from_cad.pack(side=tk.LEFT)
        row += 1

        self.lbl_rate_mode = ttk.Label(form, text="", style="Card.TLabel")
        self.lbl_rate_mode.grid(row=row, column=0, sticky=tk.W, pady=5)
        mode_frame = ttk.Frame(form, style="Card.TFrame")
        mode_frame.grid(row=row, column=1, sticky=tk.W, padx=8)
        for val, attr in (
            ("daily", "rb_daily"),
            ("monthly", "rb_monthly"),
            ("annual", "rb_annual"),
        ):
            rb = ttk.Radiobutton(
                mode_frame,
                variable=self.rate_mode_var,
                value=val,
                command=self._on_rate_mode_change,
            )
            rb.pack(side=tk.LEFT, padx=(0, 10))
            setattr(self, attr, rb)
        row += 1

        self.date_row = ttk.Frame(form, style="Card.TFrame")
        self.date_row.grid(row=row, column=0, columnspan=3, sticky=tk.W, pady=5)
        self.lbl_date = ttk.Label(self.date_row, text="", style="Card.TLabel")
        self.lbl_date.pack(side=tk.LEFT)
        self.date_var = tk.StringVar()
        ttk.Entry(self.date_row, textvariable=self.date_var, width=20).pack(side=tk.LEFT, padx=8)
        self.lbl_date_hint = ttk.Label(self.date_row, text="", style="Muted.TLabel")
        self.lbl_date_hint.configure(background=COLOR_CARD)
        self.lbl_date_hint.pack(side=tk.LEFT)
        row += 1

        self.period_row = ttk.Frame(form, style="Card.TFrame")
        self.period_row.grid(row=row, column=0, columnspan=3, sticky=tk.W, pady=5)
        self.lbl_month = ttk.Label(self.period_row, text="", style="Card.TLabel")
        self.lbl_month.pack(side=tk.LEFT)
        ttk.Spinbox(
            self.period_row, from_=1, to=12, textvariable=self.month_var, width=5
        ).pack(side=tk.LEFT, padx=8)
        self.lbl_year = ttk.Label(self.period_row, text="", style="Card.TLabel")
        self.lbl_year.pack(side=tk.LEFT, padx=(12, 0))
        ttk.Spinbox(
            self.period_row, from_=1990, to=2100, textvariable=self.year_var, width=7
        ).pack(side=tk.LEFT, padx=8)
        row += 1

        self.lbl_amt = ttk.Label(form, text="", style="Card.TLabel")
        self.lbl_amt.grid(row=row, column=0, sticky=tk.W, pady=5)
        self.amt_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.amt_var, width=20).grid(
            row=row, column=1, sticky=tk.W, padx=8
        )
        self.lbl_amt_hint = ttk.Label(form, text="", style="Muted.TLabel")
        self.lbl_amt_hint.configure(background=COLOR_CARD)
        self.lbl_amt_hint.grid(row=row, column=2, sticky=tk.W)
        row += 1

        self.lbl_ref = ttk.Label(form, text="", style="Card.TLabel")
        self.lbl_ref.grid(row=row, column=0, sticky=tk.W, pady=5)
        self.ref_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.ref_var, width=26).grid(
            row=row, column=1, sticky=tk.W, padx=8
        )

        btns = ttk.Frame(parent, style="Card.TFrame")
        btns.pack(fill=tk.X, pady=12)
        self.btn_convert = ttk.Button(
            btns, text="", style="Accent.TButton", command=self._convert_single
        )
        self.btn_convert.pack(side=tk.LEFT)

        self.copy_menu = tk.Menubutton(btns, text="", relief=tk.RAISED)
        self.copy_menu.pack(side=tk.LEFT, padx=6)
        self._copy_popup = tk.Menu(self.copy_menu, tearoff=0)
        self.copy_menu.configure(menu=self._copy_popup)
        self._copy_popup.add_command(label="", command=lambda: self._copy("full"))
        self._copy_popup.add_command(label="", command=lambda: self._copy("amount"))
        self._copy_popup.add_command(label="", command=lambda: self._copy("tsv"))

        self.btn_exp_csv = ttk.Button(btns, text="", command=lambda: self._export_fiche(".csv"))
        self.btn_exp_csv.pack(side=tk.LEFT, padx=6)
        self.btn_exp_xlsx = ttk.Button(btns, text="", command=lambda: self._export_fiche(".xlsx"))
        self.btn_exp_xlsx.pack(side=tk.LEFT, padx=6)

        self.lbl_result = ttk.Label(parent, text="", style="Card.TLabel")
        self.lbl_result.pack(anchor=tk.W)
        self.txt_result = tk.Text(
            parent,
            height=12,
            wrap=tk.WORD,
            font=("Consolas", 11),
            bg=COLOR_RESULT_BG,
            fg=COLOR_RESULT_FG,
            relief=tk.FLAT,
            padx=12,
            pady=10,
            highlightthickness=0,
        )
        self.txt_result.pack(fill=tk.BOTH, expand=True, pady=6)
        self.txt_result.configure(state=tk.DISABLED)

    def _build_batch(self, parent: ttk.Frame) -> None:
        bar = ttk.Frame(parent, style="Card.TFrame")
        bar.pack(fill=tk.X)
        self.btn_import = ttk.Button(
            bar, text="", style="Accent.TButton", command=self._import_batch
        )
        self.btn_import.pack(side=tk.LEFT)
        self.btn_template = ttk.Button(bar, text="", command=self._save_template)
        self.btn_template.pack(side=tk.LEFT, padx=6)
        self.btn_process = ttk.Button(bar, text="", command=self._process_batch)
        self.btn_process.pack(side=tk.LEFT, padx=6)

        self.export_menu = tk.Menubutton(bar, text="", relief=tk.RAISED)
        self.export_menu.pack(side=tk.LEFT, padx=6)
        self._export_popup = tk.Menu(self.export_menu, tearoff=0)
        self.export_menu.configure(menu=self._export_popup)
        self._export_popup.add_command(label="CSV", command=lambda: self._export_batch(".csv"))
        self._export_popup.add_command(label="JSON", command=lambda: self._export_batch(".json"))
        self._export_popup.add_command(label="XML", command=lambda: self._export_batch(".xml"))

        self.lbl_drop_hint = ttk.Label(parent, text="", style="Muted.TLabel")
        self.lbl_drop_hint.pack(anchor=tk.W, pady=(8, 0))

        self.lbl_progress = ttk.Label(parent, text="", style="Card.TLabel")
        self.lbl_progress.pack(anchor=tk.W, pady=(6, 0))
        self.progress = ttk.Progressbar(parent, mode="determinate")
        self.progress.pack(fill=tk.X, pady=6)

        tree_frame = ttk.Frame(parent, style="Card.TFrame")
        tree_frame.pack(fill=tk.BOTH, expand=True)
        cols = (
            "date",
            "devise",
            "montant",
            "reference",
            "date_taux",
            "taux",
            "cad",
            "ajuste",
            "erreur",
        )
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=14)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=90, stretch=True)
        scroll_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

    def _build_history(self, parent: ttk.Frame) -> None:
        bar = ttk.Frame(parent, style="Card.TFrame")
        bar.pack(fill=tk.X)
        self.history_search_var = tk.StringVar()
        self.history_search_var.trace_add("write", lambda *_: self._refresh_history_list())
        ttk.Entry(bar, textvariable=self.history_search_var, width=36).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        self.btn_hist_export = ttk.Button(bar, text="", command=self._export_history)
        self.btn_hist_export.pack(side=tk.LEFT, padx=4)
        self.btn_hist_folder = ttk.Button(bar, text="", command=_open_data_folder)
        self.btn_hist_folder.pack(side=tk.LEFT, padx=4)
        self.btn_hist_clear = ttk.Button(
            bar, text="", style="Danger.TButton", command=self._confirm_clear_history
        )
        self.btn_hist_clear.pack(side=tk.LEFT, padx=4)
        self.lbl_history_count = ttk.Label(bar, text="", style="Muted.TLabel")
        self.lbl_history_count.pack(side=tk.RIGHT)

        list_frame = ttk.Frame(parent, style="Card.TFrame")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=8)
        self.history_list = tk.Listbox(
            list_frame,
            font=("Consolas", 10),
            bg=COLOR_CARD,
            fg=COLOR_TEXT,
            selectbackground=COLOR_HEADER,
            activestyle="none",
        )
        scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.history_list.yview)
        self.history_list.configure(yscrollcommand=scroll.set)
        self.history_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.lbl_no_history = ttk.Label(parent, text="", style="Muted.TLabel")
        self.lbl_no_history.pack(anchor=tk.W)

    def _setup_dnd(self) -> None:
        if not HAS_DND:
            return
        try:
            self.tab_batch.drop_target_register(DND_FILES)
            self.tab_batch.dnd_bind("<<Drop>>", self._on_drop)
            self.tree.drop_target_register(DND_FILES)
            self.tree.dnd_bind("<<Drop>>", self._on_drop)
        except tk.TclError:
            pass

    def _on_drop(self, event: object) -> None:
        if not HAS_DND:
            return
        raw = str(getattr(event, "data", ""))
        paths = self.tk.splitlist(raw)
        for path in paths:
            p = Path(path.strip("{}"))
            if p.suffix.lower() in IMPORT_EXTENSIONS:
                self._load_batch_file(p)
                return

    def _save_gui_prefs(self) -> None:
        _save_prefs(
            {
                "direction": self.direction_var.get(),
                "rate_mode": self.rate_mode_var.get(),
                "month": self.month_var.get(),
                "year": self.year_var.get(),
            }
        )

    def _on_rate_mode_change(self) -> None:
        self._save_gui_prefs()
        self._update_rate_mode_ui()

    def _update_rate_mode_ui(self) -> None:
        mode = self.rate_mode_var.get()
        if mode == "daily":
            self.date_row.grid()
            self.period_row.grid_remove()
        else:
            self.date_row.grid_remove()
            self.period_row.grid()
            if mode == "monthly":
                self.lbl_month.grid()
            else:
                self.lbl_month.grid_remove()

    def _update_direction_labels(self) -> None:
        ccy = self.ccy_var.get().strip().upper() or "USD"
        self.rb_to_cad.configure(text=g("to_cad", ccy=ccy))
        self.rb_from_cad.configure(text=g("from_cad", ccy=ccy))

    def _refresh_texts(self) -> None:
        self.title(g("window_title"))
        self.lbl_brand.configure(text=g("brand"))
        self.lbl_tagline.configure(text=g("tagline"))
        self.lbl_lang.configure(text=g("lang"))
        self.notebook.tab(0, text=g("tab_single"))
        self.notebook.tab(1, text=g("tab_batch"))
        self.notebook.tab(2, text=g("tab_history"))
        self.lbl_ccy.configure(text=g("currency"))
        self.lbl_direction.configure(text=g("direction"))
        self.lbl_rate_mode.configure(text=g("rate_mode"))
        self.rb_daily.configure(text=g("mode_daily"))
        self.rb_monthly.configure(text=g("mode_monthly"))
        self.rb_annual.configure(text=g("mode_annual"))
        self.lbl_date.configure(text=g("date"))
        self.lbl_month.configure(text=g("month"))
        self.lbl_year.configure(text=g("year"))
        self.lbl_amt.configure(text=g("amount"))
        self.lbl_ref.configure(text=g("reference"))
        self.lbl_date_hint.configure(text=g("date_hint"))
        self.lbl_amt_hint.configure(text=g("amount_hint"))
        self.btn_convert.configure(text=g("convert"))
        self.copy_menu.configure(text=g("copy"))
        items = self._copy_popup.index("end")
        if items is not None:
            self._copy_popup.entryconfigure(0, label=g("copy_full"))
            self._copy_popup.entryconfigure(1, label=g("copy_amount"))
            self._copy_popup.entryconfigure(2, label=g("copy_tsv"))
        self.btn_exp_csv.configure(text=g("export_csv"))
        self.btn_exp_xlsx.configure(text=g("export_xlsx"))
        self.lbl_result.configure(text=g("result"))
        self.btn_import.configure(text=g("import_file"))
        self.btn_template.configure(text=g("save_template"))
        self.btn_process.configure(text=g("process"))
        self.export_menu.configure(text=g("export_result"))
        self.lbl_drop_hint.configure(
            text=g("drop_hint") if HAS_DND else g("dnd_unavailable")
        )
        self.lbl_progress.configure(text=g("progress"))
        self.btn_hist_export.configure(text=g("export_txt"))
        self.btn_hist_folder.configure(text=g("show_folder"))
        self.btn_hist_clear.configure(text=g("clear_history"))
        self.lbl_no_history.configure(text=g("no_history"))
        self.status.set(g("ready"))
        self._update_direction_labels()

        headers = g("cols")
        keys = ("date", "devise", "montant", "reference", "date_taux", "taux", "cad", "ajuste", "erreur")
        for key, title in zip(keys, headers):
            self.tree.heading(key, text=title)

        if self.resultat:
            self._show_result_text()

    def _on_lang(self, _event: object = None) -> None:
        core.set_lang("fr" if self.lang_var.get().startswith("F") else "en")
        self._refresh_texts()

    def _on_tab_changed(self, _event: object = None) -> None:
        if self.notebook.index(self.notebook.select()) == 2:
            self._reload_history()

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        state = tk.DISABLED if busy else tk.NORMAL
        for w in (
            self.btn_convert,
            self.copy_menu,
            self.btn_exp_csv,
            self.btn_exp_xlsx,
            self.btn_import,
            self.btn_template,
            self.btn_process,
            self.export_menu,
            self.btn_hist_export,
            self.btn_hist_folder,
            self.btn_hist_clear,
            self.cmb_lang,
        ):
            w.configure(state=state)

    def _convert_single(self) -> None:
        if self._busy:
            return
        try:
            montant = core.parse_montant(self.amt_var.get())
            devise = self.ccy_var.get().strip().upper()
            if not devise:
                raise core.TauxBdcError(core.t("devise_vide").replace("  → ", ""))
            direction = self.direction_var.get()
            rate_mode = self.rate_mode_var.get()
            date_tx: Optional[date] = None
            annee = int(self.year_var.get())
            mois = int(self.month_var.get())
            if rate_mode == "daily":
                date_tx = core.parse_date(self.date_var.get())
        except (core.TauxBdcError, ValueError) as err:
            messagebox.showerror(g("err_title"), str(err))
            return

        self._set_busy(True)
        self.status.set(g("converting"))

        def worker() -> None:
            try:
                res = self._run_conversion(
                    devise=devise,
                    montant=montant,
                    reference=self.ref_var.get().strip(),
                    direction=direction,
                    rate_mode=rate_mode,
                    date_tx=date_tx,
                    annee=annee,
                    mois=mois,
                )
                self.after(0, lambda: self._on_single_ok(res))
            except Exception as err:  # noqa: BLE001
                self.after(0, lambda: self._on_single_err(str(err)))

        threading.Thread(target=worker, daemon=True).start()

    @staticmethod
    def _run_conversion(
        devise: str,
        montant: Decimal,
        reference: str,
        direction: str,
        rate_mode: str,
        date_tx: Optional[date],
        annee: int,
        mois: int,
    ) -> core.ResultatConversion:
        if rate_mode == "daily":
            assert date_tx is not None
            tx = core.recuperer_taux(devise, date_tx)
            taux = tx.taux
            libelle = date_tx.isoformat()
            detail = tx.date_taux.isoformat()
            source = tx.libelle_source
            ajuste = tx.est_ajuste
            serie = tx.serie
        else:
            tm = core.recuperer_taux_moyen(
                devise, annee, mois if rate_mode == "monthly" else None
            )
            taux = tm.taux
            libelle = tm.periode
            detail = core.t("avg_detail", periode=tm.periode, nb=tm.nb_observations)
            source = (
                f"Banque du Canada (Valet) / {tm.serie}"
                if core.get_lang() == "fr"
                else f"Bank of Canada (Valet) / {tm.serie}"
            )
            ajuste = False
            serie = tm.serie

        if direction == "to_cad":
            entree, sortie = montant, core.convertir(montant, taux)
            dev_entree, dev_sortie = devise, "CAD"
        else:
            entree, sortie = montant, core.diviser(montant, taux)
            dev_entree, dev_sortie = "CAD", devise

        res = core.ResultatConversion(
            devise=devise,
            serie=serie,
            taux=taux,
            libelle_demande=libelle,
            detail_taux=detail,
            montant_entree=entree,
            devise_entree=dev_entree,
            montant_sortie=sortie,
            devise_sortie=dev_sortie,
            source_label=source,
            ajuste=ajuste,
            reference=reference,
            mode_taux=rate_mode,
        )
        core.journaliser_operation(
            reference=reference,
            libelle_demande=libelle,
            detail_taux=detail,
            taux=taux,
            from_amount=entree,
            from_currency=dev_entree,
            to_amount=sortie,
            to_currency=dev_sortie,
            source_label=source,
        )
        return res

    def _on_single_ok(self, res: core.ResultatConversion) -> None:
        self.resultat = res
        self._show_result_text()
        self._set_busy(False)
        self.status.set(g("done"))

    def _on_single_err(self, msg: str) -> None:
        self._set_busy(False)
        self.status.set(g("ready"))
        messagebox.showerror(g("err_title"), msg)

    def _show_result_text(self) -> None:
        if not self.resultat:
            return
        texte = core.texte_fiche_bidirectionnel(self.resultat)
        self.txt_result.configure(state=tk.NORMAL)
        self.txt_result.delete("1.0", tk.END)
        self.txt_result.insert(tk.END, texte)
        self.txt_result.configure(state=tk.DISABLED)

    def _copy(self, mode: str) -> None:
        if not self.resultat:
            messagebox.showinfo(g("info_title"), g("no_result"))
            return
        if mode == "full":
            texte = core.texte_fiche_bidirectionnel(self.resultat)
        elif mode == "amount":
            texte = format(self.resultat.montant_sortie, "f")
        else:
            texte = core.ligne_tsv(self.resultat)
        self.clipboard_clear()
        self.clipboard_append(texte)
        self.status.set(g("copied"))

    def _export_fiche(self, suffix: str) -> None:
        if not self.resultat:
            messagebox.showinfo(g("info_title"), g("no_result"))
            return
        path = filedialog.asksaveasfilename(defaultextension=suffix)
        if not path:
            return
        if not path.lower().endswith(suffix):
            path += suffix
        try:
            ligne = LigneLot(
                brut_date=self.resultat.libelle_demande,
                brut_devise=self.resultat.devise,
                brut_montant=format(self.resultat.montant_entree, "f"),
                devise=self.resultat.devise,
                montant=self.resultat.montant_entree,
                reference=self.resultat.reference,
                taux=self.resultat.taux,
                montant_cad=self.resultat.montant_sortie
                if self.resultat.devise_sortie == "CAD"
                else self.resultat.montant_entree,
                serie=self.resultat.serie,
            )
            ecrire_fichier(path, [ligne])
            messagebox.showinfo(g("info_title"), g("exported", path=path))
        except core.TauxBdcError as err:
            messagebox.showerror(g("err_title"), str(err))

    def _refresh_tree(self) -> None:
        self.tree.delete(*self.tree.get_children())
        lang = core.get_lang()
        oui = "oui" if lang == "fr" else "yes"
        non = "non" if lang == "fr" else "no"
        for ligne in self.lignes:
            montant = (
                core.formater_nombre(ligne.montant, 2)
                if ligne.montant is not None
                else ligne.brut_montant
            )
            self.tree.insert(
                "",
                tk.END,
                values=(
                    ligne.date_tx.isoformat() if ligne.date_tx else ligne.brut_date,
                    ligne.devise or ligne.brut_devise,
                    montant,
                    ligne.reference,
                    ligne.date_taux.isoformat() if ligne.date_taux else "",
                    core.formater_nombre(ligne.taux) if ligne.taux is not None else "",
                    (
                        core.formater_nombre(ligne.montant_cad, 2)
                        if ligne.montant_cad is not None
                        else ""
                    ),
                    (oui if ligne.ajuste else non) if ligne.taux is not None else "",
                    ligne.erreur,
                ),
            )

    def _load_batch_file(self, path: Path) -> None:
        try:
            self.lignes = lire_fichier(path)
            self._refresh_tree()
            self.progress["value"] = 0
            self.status.set(f"{len(self.lignes)} — {g('ready')}")
        except core.TauxBdcError as err:
            messagebox.showerror(g("err_title"), str(err))

    def _import_batch(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[
                ("Tous formats", "*.csv *.xlsx *.xlsm *.json *.xml"),
                ("CSV", "*.csv"),
                ("Excel", "*.xlsx"),
                ("JSON", "*.json"),
                ("XML", "*.xml"),
            ]
        )
        if path:
            self._load_batch_file(Path(path))

    def _save_template(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("Excel", "*.xlsx")],
            initialfile="modele_lot.csv",
        )
        if not path:
            return
        try:
            if path.lower().endswith(".xlsx"):
                creer_modele_xlsx(path)
            else:
                if not path.lower().endswith(".csv"):
                    path += ".csv"
                creer_modele_csv(path)
            messagebox.showinfo(g("info_title"), g("exported", path=path))
        except core.TauxBdcError as err:
            messagebox.showerror(g("err_title"), str(err))

    def _process_batch(self) -> None:
        if self._busy or not self.lignes:
            if not self.lignes:
                messagebox.showinfo(g("info_title"), g("no_rows"))
            return
        if not messagebox.askyesno(g("info_title"), g("confirm_process", n=len(self.lignes))):
            return
        self._set_busy(True)
        total = len(self.lignes)
        self.progress["maximum"] = total

        def worker() -> None:
            ok = err = 0
            for i, ligne in enumerate(self.lignes):
                traiter_ligne(ligne)
                if ligne.erreur:
                    err += 1
                else:
                    ok += 1
                self.after(0, lambda i=i: self._on_batch_progress(i + 1, total))
            self.after(0, lambda: self._on_batch_done(ok, err))

        threading.Thread(target=worker, daemon=True).start()

    def _on_batch_progress(self, current: int, total: int) -> None:
        self.progress["value"] = current
        self.status.set(f"{current} / {total}")
        self._refresh_tree()

    def _on_batch_done(self, ok: int, err: int) -> None:
        self._set_busy(False)
        self._refresh_tree()
        self.status.set(g("batch_done", ok=ok, err=err))
        messagebox.showinfo(g("info_title"), g("batch_done", ok=ok, err=err))

    def _export_batch(self, suffix: str) -> None:
        if not self.lignes:
            messagebox.showinfo(g("info_title"), g("no_rows"))
            return
        path = filedialog.asksaveasfilename(
            defaultextension=suffix,
            initialfile=f"conversions_bdc{suffix}",
        )
        if not path:
            return
        if not path.lower().endswith(suffix):
            path += suffix
        try:
            ecrire_fichier(path, self.lignes)
            messagebox.showinfo(g("info_title"), g("exported", path=path))
        except core.TauxBdcError as err:
            messagebox.showerror(g("err_title"), str(err))

    def _reload_history(self) -> None:
        self._history_entries = core.lire_journal()
        self._refresh_history_list()

    def _filtered_history(self) -> list[str]:
        q = self.history_search_var.get().strip().lower()
        if not q:
            return self._history_entries
        return [ln for ln in self._history_entries if q in ln.lower()]

    def _refresh_history_list(self) -> None:
        filtered = self._filtered_history()
        self.history_list.delete(0, tk.END)
        for line in filtered:
            self.history_list.insert(tk.END, line)
        self.lbl_history_count.configure(text=g("history_count", n=len(filtered)))
        if filtered:
            self.lbl_no_history.pack_forget()
        else:
            self.lbl_no_history.pack(anchor=tk.W)

    def _export_history(self) -> None:
        filtered = self._filtered_history()
        if not filtered:
            messagebox.showinfo(g("info_title"), g("no_history"))
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile="historique_conversions.txt",
        )
        if not path:
            return
        Path(path).write_text("\n".join(filtered) + "\n", encoding="utf-8")
        messagebox.showinfo(g("info_title"), g("exported", path=path))

    def _confirm_clear_history(self) -> None:
        if not self._history_entries:
            return
        if not messagebox.askyesno(
            g("clear_confirm_title"),
            g("clear_confirm_message"),
        ):
            return
        try:
            backup = core.effacer_journal_avec_sauvegarde()
            self._reload_history()
            if backup:
                self.status.set(g("cleared_status", fichier=backup.name))
            else:
                self.status.set(g("ready"))
        except OSError as err:
            messagebox.showerror(g("err_title"), str(err))


def main(argv: Optional[list[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    delegue = (
        "--cli" in argv
        or any(a in argv for a in ("--devise", "-d", "--date", "--montant", "-m", "--reference", "-r"))
        or (len(argv) >= 1 and not argv[0].startswith("-") and any(c.isdigit() for c in argv[0]))
    )
    if delegue:
        filtered = [a for a in argv if a != "--gui"]
        return core.main(filtered)

    if "--lang" in argv:
        i = argv.index("--lang")
        if i + 1 < len(argv) and argv[i + 1] in ("fr", "en"):
            core.set_lang(argv[i + 1])  # type: ignore[arg-type]
    elif "-l" in argv:
        i = argv.index("-l")
        if i + 1 < len(argv) and argv[i + 1] in ("fr", "en"):
            core.set_lang(argv[i + 1])  # type: ignore[arg-type]

    app = App()
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
