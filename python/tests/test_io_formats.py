"""Tests import/export JSON et XML."""

import json
from datetime import date
from decimal import Decimal

import io_ecritures as io_e


def test_json_aller_retour(tmp_path):
    src = tmp_path / "lot.json"
    src.write_text(
        json.dumps(
            [
                {"date": "2026-07-05", "devise": "USD", "montant": "1500.00", "reference": "A"},
                {"date": "08/07/2026", "devise": "EUR", "montant": "1000,50", "reference": "B"},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    lignes = io_e.lire_json(src)
    assert len(lignes) == 2
    assert lignes[0].montant == Decimal("1500.00")
    assert lignes[1].date_tx == date(2026, 7, 8)

    out = tmp_path / "out.json"
    io_e.ecrire_json(out, lignes)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data[0]["devise"] == "USD"
    assert "date_taux" in data[0]


def test_xml_aller_retour(tmp_path):
    src = tmp_path / "lot.xml"
    src.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<lot>
  <ecriture date="2026-07-05" devise="USD" montant="1500" reference="X"/>
  <ecriture date="2026-07-06" devise="EUR" montant="900.50" reference="Y"/>
</lot>
""",
        encoding="utf-8",
    )
    lignes = io_e.lire_xml(src)
    assert len(lignes) == 2
    assert lignes[0].devise == "USD"

    out = tmp_path / "out.xml"
    io_e.ecrire_xml(out, lignes)
    texte = out.read_text(encoding="utf-8")
    assert "<ecriture" in texte
    assert 'devise="USD"' in texte


def test_lire_fichier_json_xml(tmp_path):
    j = tmp_path / "a.json"
    j.write_text('[{"date":"2026-01-01","devise":"USD","montant":"100"}]', encoding="utf-8")
    x = tmp_path / "b.xml"
    x.write_text(
        '<lot><ecriture date="2026-01-02" devise="EUR" montant="200"/></lot>',
        encoding="utf-8",
    )
    assert len(io_e.lire_fichier(j)) == 1
    assert len(io_e.lire_fichier(x)) == 1
