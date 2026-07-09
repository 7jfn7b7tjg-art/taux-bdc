"""Tests du moteur Python (parsing, conversion, Valet simulé, IO CSV)."""

from datetime import date
from decimal import Decimal

import pytest

import taux_bdc as m
import io_ecritures as io_e


@pytest.fixture(autouse=True)
def isole_data_dir(tmp_path, monkeypatch):
    """Cache et journal d'audit isolés par test."""
    monkeypatch.setattr(m, "_data_dir_cache", tmp_path)
    yield


@pytest.fixture(autouse=True)
def lang_fr():
    m.set_lang("fr")
    yield


# --- Parsing ---------------------------------------------------------------

def test_parse_montant_formats():
    assert m._parse_montant("1500,50") == Decimal("1500.50")
    assert m._parse_montant("1500.50") == Decimal("1500.50")
    assert m._parse_montant("1 500,00") == Decimal("1500.00")


@pytest.mark.parametrize("mauvais", ["", "abc", "-5", "0"])
def test_parse_montant_rejets(mauvais):
    with pytest.raises(m.TauxBdcError):
        m._parse_montant(mauvais)


@pytest.mark.parametrize(
    "texte",
    ["2026-07-05", "05/07/2026", "05-07-2026", "2026/07/05"],
)
def test_parse_date_formats(texte):
    assert m._parse_date(texte) == date(2026, 7, 5)


def test_parse_date_invalide():
    with pytest.raises(m.TauxBdcError):
        m._parse_date("pas-une-date")


# --- Conversion Decimal ----------------------------------------------------

def test_convertir_half_up():
    assert m.convertir(Decimal("1500"), Decimal("1.4201")) == Decimal("2130.15")
    assert m.convertir(Decimal("1.005"), Decimal("1")) == Decimal("1.01")


def test_diviser_half_up():
    assert m.diviser(Decimal("2130.15"), Decimal("1.4201")) == Decimal("1500.00")
    assert m.diviser(Decimal("100"), Decimal("3")) == Decimal("33.33")


def test_moyenne_exacte():
    vals = [Decimal("1.40"), Decimal("1.41"), Decimal("1.42")]
    assert m.moyenne(vals) == Decimal("1.41")
    assert m.moyenne([Decimal("1.4201"), Decimal("1.4174")]) == Decimal("1.41875")


def test_formater_nombre():
    m.set_lang("fr")
    assert m.formater_nombre(Decimal("1500"), 2) == "1 500,00"
    m.set_lang("en")
    assert m.formater_nombre(Decimal("1500"), 2) == "1,500.00"


# --- Valet simulé : fallback week-end et cache hors-ligne -------------------

PAYLOAD_VENDREDI = {
    "observations": [
        {"d": "2026-07-02", "FXUSDCAD": {"v": "1.4181"}},
        {"d": "2026-07-03", "FXUSDCAD": {"v": "1.4201"}},
    ]
}


def test_fallback_jour_ouvre(monkeypatch):
    monkeypatch.setattr(m, "_http_get_json", lambda url: PAYLOAD_VENDREDI)
    tx = m.recuperer_taux("USD", date(2026, 7, 5))  # dimanche
    assert tx.date_taux == date(2026, 7, 3)
    assert tx.taux == Decimal("1.4201")
    assert tx.est_ajuste
    assert tx.source == "api"


def test_cache_hors_ligne(monkeypatch):
    # 1er appel : remplit le cache
    monkeypatch.setattr(m, "_http_get_json", lambda url: PAYLOAD_VENDREDI)
    m.recuperer_taux("USD", date(2026, 7, 5))

    # 2e appel : réseau coupé → cache
    def boom(url):
        raise m.TauxBdcError("réseau coupé (test)")

    monkeypatch.setattr(m, "_http_get_json", boom)
    tx = m.recuperer_taux("USD", date(2026, 7, 5))
    assert tx.source == "cache"
    assert tx.taux == Decimal("1.4201")


def test_journal_audit(monkeypatch):
    monkeypatch.setattr(m, "_http_get_json", lambda url: PAYLOAD_VENDREDI)
    tx = m.recuperer_taux("USD", date(2026, 7, 5))
    cad = m.convertir(Decimal("1500"), tx.taux)
    m.journaliser_conversion(tx, Decimal("1500"), cad, reference="10443")
    contenu = m.audit_log_path().read_text(encoding="utf-8")
    assert "10443" in contenu
    assert "1.4201" in contenu
    assert "2026-07-03" in contenu


def test_journal_bidirectionnel():
    m.journaliser_operation(
        reference="INV-9",
        libelle_demande="2026-06",
        detail_taux="2026-06-30",
        taux=Decimal("1.37"),
        from_amount=Decimal("1000"),
        from_currency="CAD",
        to_amount=Decimal("729.93"),
        to_currency="USD",
        source_label="Bank of Canada (Valet / FXUSDCAD)",
    )
    lignes = m.lire_journal()
    assert len(lignes) == 1
    assert "CAD" in lignes[0]
    assert "USD" in lignes[0]


def test_effacer_journal_avec_sauvegarde():
    m.audit_log_path().write_text("[test] ligne\n", encoding="utf-8")
    backup = m.effacer_journal_avec_sauvegarde()
    assert backup is not None
    assert backup.exists()
    assert not m.audit_log_path().exists()
    assert m.effacer_journal_avec_sauvegarde() is None


PAYLOAD_JUILLET = {
    "observations": [
        {"d": "2026-07-02", "FXUSDCAD": {"v": "1.4181"}},
        {"d": "2026-07-03", "FXUSDCAD": {"v": "1.4201"}},
        {"d": "2026-07-04", "FXUSDCAD": {"v": "1.4190"}},
    ]
}


def test_recuperer_taux_moyen_mensuel(monkeypatch):
    monkeypatch.setattr(m, "_http_get_json", lambda url: PAYLOAD_JUILLET)
    tm = m.recuperer_taux_moyen("USD", 2026, 7)
    assert tm.periode == "2026-07"
    assert tm.nb_observations == 3
    assert tm.taux == Decimal("1.419067")


def test_ligne_tsv():
    res = m.ResultatConversion(
        devise="USD",
        serie="FXUSDCAD",
        taux=Decimal("1.4201"),
        libelle_demande="2026-07-05",
        detail_taux="2026-07-03",
        montant_entree=Decimal("1500"),
        devise_entree="USD",
        montant_sortie=Decimal("2130.15"),
        devise_sortie="CAD",
        source_label="test",
        reference="FAC-1",
    )
    tsv = m.ligne_tsv(res)
    assert "FAC-1" in tsv
    assert "\t" in tsv


# --- IO CSV -----------------------------------------------------------------

def test_csv_aller_retour(tmp_path):
    src = tmp_path / "lot.csv"
    src.write_text(
        "date,devise,montant,reference\n"
        "2026-07-05,USD,1500.00,FAC-123\n"
        '08/07/2026,EUR,"1000,50",FAC-124\n',
        encoding="utf-8",
    )
    lignes = io_e.lire_csv(src)
    assert len(lignes) == 2
    assert lignes[0].devise == "USD"
    assert lignes[0].montant == Decimal("1500.00")
    assert lignes[1].montant == Decimal("1000.50")
    assert lignes[1].date_tx == date(2026, 7, 8)

    out = tmp_path / "out.csv"
    io_e.ecrire_csv(out, lignes)
    texte = out.read_text(encoding="utf-8")
    assert "date_taux" in texte
    assert "FAC-123" in texte
