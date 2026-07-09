#!/usr/bin/env python3
"""
Interface graphique — taux de change Banque du Canada (unitaire + lot).
GUI — Bank of Canada FX rates (single + batch), CSV/Excel import-export.
"""

from __future__ import annotations

import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Optional

import taux_bdc as core
from io_ecritures import (
    FicheUnitaire,
    LigneLot,
    creer_modele_csv,
    creer_modele_xlsx,
    ecrire_fichier,
    lire_fichier,
    traiter_ligne,
)

# Palette — teal / or (finance, pas le violet générique)
COLOR_BG = "#F4F7F7"
COLOR_HEADER = "#0B6E6E"
COLOR_HEADER_FG = "#F7F3E8"
COLOR_ACCENT = "#C4A35A"
COLOR_CARD = "#FFFFFF"
COLOR_TEXT = "#1A2B2B"
COLOR_MUTED = "#5A6F6F"
COLOR_RESULT_BG = "#0F2F2F"
COLOR_RESULT_FG = "#E8F2F2"


def _resource_path(*parts: str) -> Path:
    """Chemin ressource (dev ou PyInstaller)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(getattr(sys, "_MEIPASS"))
    else:
        base = Path(__file__).resolve().parent
    return base.joinpath(*parts)

GUI_MSG = {
    "fr": {
        "window_title": "Taux BdC — Banque du Canada",
        "brand": "Taux BdC",
        "tagline": "Taux officiels · Écritures comptables",
        "lang": "Langue",
        "tab_single": "Conversion",
        "tab_batch": "Lot (CSV / Excel)",
        "currency": "Devise",
        "date": "Date transaction",
        "amount": "Montant",
        "reference": "Référence (opt.)",
        "convert": "Convertir",
        "copy": "Copier la fiche",
        "export_csv": "Exporter CSV",
        "export_xlsx": "Exporter Excel",
        "result": "Résultat",
        "import_file": "Importer CSV / Excel…",
        "save_template": "Enregistrer un modèle…",
        "process": "Traiter le lot",
        "export_result": "Exporter le résultat…",
        "progress": "Progression",
        "ready": "Prêt.",
        "converting": "Récupération du taux…",
        "done": "Terminé.",
        "copied": "Fiche copiée dans le presse-papiers.",
        "exported": "Fichier enregistré :\n{path}",
        "no_result": "Aucune conversion à exporter.",
        "no_rows": "Importez d'abord un fichier.",
        "confirm_process": "Traiter {n} ligne(s) ? (appel API Banque du Canada)",
        "batch_done": "Lot terminé : {ok} OK, {err} erreur(s).",
        "err_title": "Erreur",
        "info_title": "Information",
        "date_hint": "AAAA-MM-JJ ou JJ/MM/AAAA",
        "amount_hint": "ex. 1500,00",
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
        "tab_batch": "Batch (CSV / Excel)",
        "currency": "Currency",
        "date": "Transaction date",
        "amount": "Amount",
        "reference": "Reference (opt.)",
        "convert": "Convert",
        "copy": "Copy summary",
        "export_csv": "Export CSV",
        "export_xlsx": "Export Excel",
        "result": "Result",
        "import_file": "Import CSV / Excel…",
        "save_template": "Save template…",
        "process": "Process batch",
        "export_result": "Export results…",
        "progress": "Progress",
        "ready": "Ready.",
        "converting": "Fetching rate…",
        "done": "Done.",
        "copied": "Summary copied to clipboard.",
        "exported": "File saved:\n{path}",
        "no_result": "Nothing to export yet.",
        "no_rows": "Import a file first.",
        "confirm_process": "Process {n} row(s)? (Bank of Canada API calls)",
        "batch_done": "Batch done: {ok} OK, {err} error(s).",
        "err_title": "Error",
        "info_title": "Information",
        "date_hint": "YYYY-MM-DD or DD/MM/YYYY",
        "amount_hint": "e.g. 1500.00",
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


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.fiche: Optional[FicheUnitaire] = None
        self.lignes: list[LigneLot] = []
        self._busy = False
        self._logo_image: Optional[tk.PhotoImage] = None

        self.title(g("window_title"))
        self.minsize(780, 560)
        self.geometry("900x640")
        self.configure(bg=COLOR_BG)
        self._set_window_icon()
        self._setup_style()

        self._build()
        self._refresh_texts()

    def _set_window_icon(self) -> None:
        for candidate in (
            _resource_path("packaging", "assets", "logo_128.png"),
            _resource_path("packaging", "assets", "app_icon.png"),
            _resource_path("assets", "logo_128.png"),
        ):
            if candidate.exists():
                try:
                    icon = tk.PhotoImage(file=str(candidate))
                    self.iconphoto(True, icon)
                    self._window_icon = icon  # garder une référence
                except tk.TclError:
                    pass
                break

    def _setup_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", background=COLOR_BG, foreground=COLOR_TEXT, font=("Helvetica Neue", 11))
        style.configure("TFrame", background=COLOR_BG)
        style.configure("Card.TFrame", background=COLOR_CARD)
        style.configure("Header.TFrame", background=COLOR_HEADER)
        style.configure("Header.TLabel", background=COLOR_HEADER, foreground=COLOR_HEADER_FG)
        style.configure("Brand.TLabel", background=COLOR_HEADER, foreground=COLOR_HEADER_FG, font=("Helvetica Neue", 18, "bold"))
        style.configure("Tag.TLabel", background=COLOR_HEADER, foreground=COLOR_ACCENT, font=("Helvetica Neue", 10))
        style.configure("TLabel", background=COLOR_BG, foreground=COLOR_TEXT)
        style.configure("Muted.TLabel", background=COLOR_BG, foreground=COLOR_MUTED)
        style.configure("Card.TLabel", background=COLOR_CARD, foreground=COLOR_TEXT)
        style.configure("TButton", padding=(12, 6), font=("Helvetica Neue", 11))
        style.configure("Accent.TButton", padding=(14, 8), font=("Helvetica Neue", 11, "bold"))
        style.configure("TNotebook", background=COLOR_BG, borderwidth=0)
        style.configure("TNotebook.Tab", padding=(14, 8), font=("Helvetica Neue", 11))
        style.configure("Treeview", rowheight=26, font=("Helvetica Neue", 10), fieldbackground=COLOR_CARD)
        style.configure("Treeview.Heading", font=("Helvetica Neue", 10, "bold"))
        style.configure("Horizontal.TProgressbar", troughcolor="#D9E4E4", background=COLOR_HEADER)
        style.configure("Status.TLabel", background="#E7EEEE", foreground=COLOR_MUTED, padding=(10, 6))

    def _build(self) -> None:
        header = ttk.Frame(self, style="Header.TFrame", padding=(16, 12))
        header.pack(fill=tk.X)

        brand_row = ttk.Frame(header, style="Header.TFrame")
        brand_row.pack(side=tk.LEFT, fill=tk.X, expand=True)

        logo_path = _resource_path("packaging", "assets", "logo_64.png")
        if logo_path.exists():
            try:
                self._logo_image = tk.PhotoImage(file=str(logo_path))
                ttk.Label(brand_row, image=self._logo_image, style="Header.TLabel").pack(
                    side=tk.LEFT, padx=(0, 12)
                )
            except tk.TclError:
                self._logo_image = None

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

        self.tab_single = ttk.Frame(self.notebook, padding=14, style="Card.TFrame")
        self.tab_batch = ttk.Frame(self.notebook, padding=14, style="Card.TFrame")
        self.notebook.add(self.tab_single, text="")
        self.notebook.add(self.tab_batch, text="")

        self._build_single(self.tab_single)
        self._build_batch(self.tab_batch)

        self.status = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.status, style="Status.TLabel").pack(fill=tk.X, side=tk.BOTTOM)

    def _build_single(self, parent: ttk.Frame) -> None:
        form = ttk.Frame(parent, style="Card.TFrame")
        form.pack(fill=tk.X)

        self.lbl_ccy = ttk.Label(form, text="", style="Card.TLabel")
        self.lbl_ccy.grid(row=0, column=0, sticky=tk.W, pady=5)
        codes = list(core.DEVISES.keys())
        self.ccy_var = tk.StringVar(value="USD")
        self.cmb_ccy = ttk.Combobox(form, textvariable=self.ccy_var, values=codes, width=12)
        self.cmb_ccy.grid(row=0, column=1, sticky=tk.W, padx=8)

        self.lbl_date = ttk.Label(form, text="", style="Card.TLabel")
        self.lbl_date.grid(row=1, column=0, sticky=tk.W, pady=5)
        self.date_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.date_var, width=20).grid(
            row=1, column=1, sticky=tk.W, padx=8
        )
        self.lbl_date_hint = ttk.Label(form, text="", style="Muted.TLabel")
        self.lbl_date_hint.configure(background=COLOR_CARD)
        self.lbl_date_hint.grid(row=1, column=2, sticky=tk.W)

        self.lbl_amt = ttk.Label(form, text="", style="Card.TLabel")
        self.lbl_amt.grid(row=2, column=0, sticky=tk.W, pady=5)
        self.amt_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.amt_var, width=20).grid(
            row=2, column=1, sticky=tk.W, padx=8
        )
        self.lbl_amt_hint = ttk.Label(form, text="", style="Muted.TLabel")
        self.lbl_amt_hint.configure(background=COLOR_CARD)
        self.lbl_amt_hint.grid(row=2, column=2, sticky=tk.W)

        self.lbl_ref = ttk.Label(form, text="", style="Card.TLabel")
        self.lbl_ref.grid(row=3, column=0, sticky=tk.W, pady=5)
        self.ref_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.ref_var, width=26).grid(
            row=3, column=1, sticky=tk.W, padx=8
        )

        btns = ttk.Frame(parent, style="Card.TFrame")
        btns.pack(fill=tk.X, pady=12)
        self.btn_convert = ttk.Button(btns, text="", style="Accent.TButton", command=self._convert_single)
        self.btn_convert.pack(side=tk.LEFT)
        self.btn_copy = ttk.Button(btns, text="", command=self._copy_fiche)
        self.btn_copy.pack(side=tk.LEFT, padx=6)
        self.btn_exp_csv = ttk.Button(btns, text="", command=lambda: self._export_fiche(".csv"))
        self.btn_exp_csv.pack(side=tk.LEFT, padx=6)
        self.btn_exp_xlsx = ttk.Button(btns, text="", command=lambda: self._export_fiche(".xlsx"))
        self.btn_exp_xlsx.pack(side=tk.LEFT, padx=6)

        self.lbl_result = ttk.Label(parent, text="", style="Card.TLabel")
        self.lbl_result.pack(anchor=tk.W)
        self.txt_result = tk.Text(
            parent,
            height=14,
            wrap=tk.WORD,
            font=("Menlo", 11),
            bg=COLOR_RESULT_BG,
            fg=COLOR_RESULT_FG,
            insertbackground=COLOR_RESULT_FG,
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
        self.btn_import = ttk.Button(bar, text="", style="Accent.TButton", command=self._import_batch)
        self.btn_import.pack(side=tk.LEFT)
        self.btn_template = ttk.Button(bar, text="", command=self._save_template)
        self.btn_template.pack(side=tk.LEFT, padx=6)
        self.btn_process = ttk.Button(bar, text="", command=self._process_batch)
        self.btn_process.pack(side=tk.LEFT, padx=6)
        self.btn_export_batch = ttk.Button(bar, text="", command=self._export_batch)
        self.btn_export_batch.pack(side=tk.LEFT, padx=6)

        self.lbl_progress = ttk.Label(parent, text="", style="Card.TLabel")
        self.lbl_progress.pack(anchor=tk.W, pady=(10, 0))
        self.progress = ttk.Progressbar(parent, mode="determinate")
        self.progress.pack(fill=tk.X, pady=6)

        tree_frame = ttk.Frame(parent, style="Card.TFrame")
        tree_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("date", "devise", "montant", "reference", "date_taux", "taux", "cad", "ajuste", "erreur")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=16)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=90, stretch=True)
        scroll_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

    def _refresh_texts(self) -> None:
        self.title(g("window_title"))
        self.lbl_brand.configure(text=g("brand"))
        self.lbl_tagline.configure(text=g("tagline"))
        self.lbl_lang.configure(text=g("lang"))
        self.notebook.tab(0, text=g("tab_single"))
        self.notebook.tab(1, text=g("tab_batch"))
        self.lbl_ccy.configure(text=g("currency"))
        self.lbl_date.configure(text=g("date"))
        self.lbl_amt.configure(text=g("amount"))
        self.lbl_ref.configure(text=g("reference"))
        self.lbl_date_hint.configure(text=g("date_hint"))
        self.lbl_amt_hint.configure(text=g("amount_hint"))
        self.btn_convert.configure(text=g("convert"))
        self.btn_copy.configure(text=g("copy"))
        self.btn_exp_csv.configure(text=g("export_csv"))
        self.btn_exp_xlsx.configure(text=g("export_xlsx"))
        self.lbl_result.configure(text=g("result"))
        self.btn_import.configure(text=g("import_file"))
        self.btn_template.configure(text=g("save_template"))
        self.btn_process.configure(text=g("process"))
        self.btn_export_batch.configure(text=g("export_result"))
        self.lbl_progress.configure(text=g("progress"))
        self.status.set(g("ready"))

        headers = g("cols")
        keys = ("date", "devise", "montant", "reference", "date_taux", "taux", "cad", "ajuste", "erreur")
        for key, title in zip(keys, headers):
            self.tree.heading(key, text=title)

    def _on_lang(self, _event: object = None) -> None:
        core.set_lang("fr" if self.lang_var.get().startswith("F") else "en")
        self._refresh_texts()
        if self.fiche:
            self._show_fiche_text()

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        state = tk.DISABLED if busy else tk.NORMAL
        for w in (
            self.btn_convert,
            self.btn_copy,
            self.btn_exp_csv,
            self.btn_exp_xlsx,
            self.btn_import,
            self.btn_template,
            self.btn_process,
            self.btn_export_batch,
            self.cmb_lang,
        ):
            w.configure(state=state)

    def _convert_single(self) -> None:
        if self._busy:
            return
        try:
            date_tx = core.parse_date(self.date_var.get())
            montant = core.parse_montant(self.amt_var.get())
            devise = self.ccy_var.get().strip().upper()
            if not devise:
                raise core.TauxBdcError(core.t("devise_vide").replace("  → ", ""))
        except core.TauxBdcError as err:
            messagebox.showerror(g("err_title"), str(err))
            return

        self._set_busy(True)
        self.status.set(g("converting"))

        def worker() -> None:
            try:
                tx = core.recuperer_taux(devise, date_tx)
                cad = core.convertir(montant, tx.taux)
                fiche = FicheUnitaire(
                    tx=tx,
                    montant_devise=montant,
                    montant_cad=cad,
                    reference=self.ref_var.get().strip(),
                )
                core.journaliser_conversion(
                    tx, montant, cad, reference=fiche.reference
                )
                self.after(0, lambda: self._on_single_ok(fiche))
            except Exception as err:  # noqa: BLE001 — surface to UI
                self.after(0, lambda: self._on_single_err(str(err)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_single_ok(self, fiche: FicheUnitaire) -> None:
        self.fiche = fiche
        self._show_fiche_text()
        self._set_busy(False)
        self.status.set(g("done"))

    def _on_single_err(self, msg: str) -> None:
        self._set_busy(False)
        self.status.set(g("ready"))
        messagebox.showerror(g("err_title"), msg)

    def _show_fiche_text(self) -> None:
        if not self.fiche:
            return
        texte = core.texte_fiche(
            self.fiche.tx, self.fiche.montant_devise, self.fiche.montant_cad
        )
        self.txt_result.configure(state=tk.NORMAL)
        self.txt_result.delete("1.0", tk.END)
        self.txt_result.insert(tk.END, texte)
        self.txt_result.configure(state=tk.DISABLED)

    def _copy_fiche(self) -> None:
        if not self.fiche:
            messagebox.showinfo(g("info_title"), g("no_result"))
            return
        texte = core.texte_fiche(
            self.fiche.tx, self.fiche.montant_devise, self.fiche.montant_cad
        )
        self.clipboard_clear()
        self.clipboard_append(texte)
        self.status.set(g("copied"))

    def _export_fiche(self, suffix: str) -> None:
        if not self.fiche:
            messagebox.showinfo(g("info_title"), g("no_result"))
            return
        path = filedialog.asksaveasfilename(
            defaultextension=suffix,
            filetypes=[
                ("CSV", "*.csv"),
                ("Excel", "*.xlsx"),
                ("All", "*.*"),
            ],
        )
        if not path:
            return
        if not path.lower().endswith(suffix):
            path = path + suffix
        try:
            ecrire_fichier(path, [self.fiche.vers_ligne_lot()])
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

    def _import_batch(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[
                ("CSV / Excel", "*.csv *.xlsx"),
                ("CSV", "*.csv"),
                ("Excel", "*.xlsx"),
                ("All", "*.*"),
            ]
        )
        if not path:
            return
        try:
            self.lignes = lire_fichier(path)
            self._refresh_tree()
            self.progress["value"] = 0
            self.status.set(f"{len(self.lignes)} — {g('ready')}")
        except core.TauxBdcError as err:
            messagebox.showerror(g("err_title"), str(err))

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
        if self._busy:
            return
        if not self.lignes:
            messagebox.showinfo(g("info_title"), g("no_rows"))
            return
        if not messagebox.askyesno(g("info_title"), g("confirm_process", n=len(self.lignes))):
            return

        self._set_busy(True)
        total = len(self.lignes)
        self.progress["maximum"] = total
        self.progress["value"] = 0

        def worker() -> None:
            ok = 0
            err = 0
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

    def _export_batch(self) -> None:
        if not self.lignes:
            messagebox.showinfo(g("info_title"), g("no_rows"))
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx"), ("CSV", "*.csv")],
            initialfile="conversions_bdc.xlsx",
        )
        if not path:
            return
        try:
            ecrire_fichier(path, self.lignes)
            messagebox.showinfo(g("info_title"), g("exported", path=path))
        except core.TauxBdcError as err:
            messagebox.showerror(g("err_title"), str(err))


def main(argv: Optional[list[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    # Délégation CLI : flags classiques, --cli, ou mode Flash (1er arg = date)
    delegue = (
        "--cli" in argv
        or any(a in argv for a in ("--devise", "-d", "--date", "--montant", "-m", "--reference", "-r"))
        or (len(argv) >= 1 and not argv[0].startswith("-") and any(c.isdigit() for c in argv[0]))
    )
    if delegue:
        filtered = [a for a in argv if a != "--gui"]
        return core.main(filtered)

    lang = "fr"
    if "--lang" in argv:
        i = argv.index("--lang")
        if i + 1 < len(argv) and argv[i + 1] in ("fr", "en"):
            lang = argv[i + 1]
    elif "-l" in argv:
        i = argv.index("-l")
        if i + 1 < len(argv) and argv[i + 1] in ("fr", "en"):
            lang = argv[i + 1]
    core.set_lang(lang)  # type: ignore[arg-type]

    app = App()
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
