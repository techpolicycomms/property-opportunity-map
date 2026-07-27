"""Tests for DVF ingestion (agent:data)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from pomap.ingestion.france_dvf import (
    CANONICAL_COLUMNS,
    clean_dvf,
    geo_dvf_url,
    read_raw_dvf_file,
)
from pomap.scoring.opportunity import budget_eligible, combine_scores


def _dvf_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id_mutation": ["a", "b", "c", "d", "e", "a"],
            "date_mutation": ["2023-01-10"] * 6,
            "nature_mutation": ["Vente"] * 5 + ["Vente"],
            "valeur_fonciere": [150000, 200000, 0, 300000, 250000, 150000],
            "type_local": ["Maison", "Appartement", "Maison", "Local industriel", "Maison", "Maison"],
            "surface_reelle_bati": [90, 55, 80, 200, 5, 90],
            "nombre_pieces_principales": [4, 2, 3, 0, 1, 4],
            "surface_terrain": [400, None, 200, 1000, 50, 400],
            "code_commune": ["34001"] * 6,
            "code_departement": ["34"] * 6,
            "longitude": [3.8, 3.9, 3.8, 3.7, 3.8, 3.8],
            "latitude": [43.6, 43.6, 43.6, 43.5, 43.6, 43.6],
        }
    )


def test_geo_dvf_url_pattern():
    assert (
        geo_dvf_url(2024, "34")
        == "https://files.data.gouv.fr/geo-dvf/latest/csv/2024/departements/34.csv.gz"
    )
    assert geo_dvf_url(2021, 34).endswith("/2021/departements/34.csv.gz")


def test_clean_dvf_filters_and_dedupes():
    out = clean_dvf(_dvf_fixture(), known_as_of=date(2026, 5, 18))
    # drops: zero value (c), non-residential (d), sub-9 m² (e), duplicate (a×2)
    assert len(out) == 2
    assert list(out.columns) == CANONICAL_COLUMNS
    assert out["price_per_m2"].between(100, 100_000).all()
    assert set(out["type_local"]) == {"Maison", "Appartement"}
    assert out["mutation_id"].tolist() == ["a", "b"]
    assert out["lon"].notna().all()
    assert (out["known_as_of"] == date(2026, 5, 18)).all()


def test_clean_dvf_requires_core_columns():
    with pytest.raises(ValueError):
        clean_dvf(pd.DataFrame({"foo": [1]}))


def test_read_raw_dvf_file_maps_columns(tmp_path: Path):
    raw = tmp_path / "dvf_raw_34_2019.txt"
    raw.write_text(
        "Identifiant de document|Reference document|1 Articles CGI|2 Articles CGI|"
        "3 Articles CGI|4 Articles CGI|5 Articles CGI|No disposition|Date mutation|"
        "Nature mutation|Valeur fonciere|No voie|B/T/Q|Type de voie|Code voie|Voie|"
        "Code postal|Commune|Code departement|Code commune|Prefixe de section|Section|"
        "No plan|No Volume|1er lot|Surface Carrez du 1er lot|2eme lot|"
        "Surface Carrez du 2eme lot|3eme lot|Surface Carrez du 3eme lot|4eme lot|"
        "Surface Carrez du 4eme lot|5eme lot|Surface Carrez du 5eme lot|Nombre de lots|"
        "Code type local|Type local|Identifiant local|Surface reelle bati|"
        "Nombre pieces principales|Nature culture|Nature culture speciale|Surface terrain\n"
        "|||||||000001|15/03/2019|Vente|250000,00|10||RUE|0001|TEST|34000|MONTPELLIER|34|186||"
        "AB|12||||||||||||0|1|Maison||95|4|S||300\n"
        "|||||||000001|15/03/2019|Vente|180000,00|2||AV|0002|DEMO|34100|SETE|34|308||"
        "AC|3||||||||||||0|2|Appartement||55|2|||\n"
        "|||||||000001|20/03/2019|Vente|90000,00|1||RUE|0003|OTHER|11000|NARBONNE|11|269||"
        "AD|1||||||||||||0|1|Maison||80|3|S||200\n",
        encoding="utf-8",
    )
    df = read_raw_dvf_file(raw, "34")
    assert len(df) == 2
    assert set(df["code_departement"].astype(str)) == {"34"}
    assert "34186" in set(df["code_commune"])
    assert "34308" in set(df["code_commune"])
    assert df["id_mutation"].notna().all()

    cleaned = clean_dvf(df, known_as_of=date(2024, 4, 5))
    assert len(cleaned) == 2
    assert cleaned["lon"].isna().all()
    assert cleaned["lat"].isna().all()
    assert (cleaned["known_as_of"] == date(2024, 4, 5)).all()


def test_combine_scores_formula():
    s = combine_scores(
        expected_excess_return=pd.Series([0.5, 0.5, 0.5]),
        forecast_confidence=pd.Series([1.0, 0.5, 1.0]),
        investability=pd.Series([1.0, 1.0, 1.0]),
        risk_penalty=pd.Series([0.0, 0.0, 30.0]),
    )
    assert s.iloc[0] == pytest.approx(50.0)
    assert s.iloc[1] == pytest.approx(25.0)
    assert s.iloc[2] == pytest.approx(20.0)
    assert (s.between(0, 100)).all()


def test_budget_eligible():
    assert budget_eligible(pd.Series([2000.0, 4000.0]), 80, 200_000).tolist() == [True, False]
