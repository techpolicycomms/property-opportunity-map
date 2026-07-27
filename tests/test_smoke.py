"""Smoke tests for the scaffold. Run with: pytest"""

from __future__ import annotations

import pandas as pd
import pytest

from pomap.ingestion.france_dvf import clean_dvf
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
        }
    )


def test_clean_dvf_filters_and_dedupes():
    out = clean_dvf(_dvf_fixture())
    # drops: zero value (c), non-residential (d), sub-9 m² (e), duplicate (a×2)
    assert len(out) == 2
    assert out["price_per_m2"].between(100, 100_000).all()
    assert set(out["type_local"]) == {"Maison", "Appartement"}


def test_clean_dvf_requires_core_columns():
    with pytest.raises(ValueError):
        clean_dvf(pd.DataFrame({"foo": [1]}))


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
