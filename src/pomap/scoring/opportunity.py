"""Opportunity scoring — combines model outputs into the published score.

Formula (docs/methodology.md):

    opportunity = expected_excess_return × confidence × investability − risk_penalty

All knobs come from config/model.yml; nothing is hard-coded here.
"""

from __future__ import annotations

import pandas as pd


def combine_scores(
    expected_excess_return: pd.Series,
    forecast_confidence: pd.Series,
    investability: pd.Series,
    risk_penalty: pd.Series,
    scale: tuple[float, float] = (0.0, 100.0),
) -> pd.Series:
    """Combine sub-scores into the 0–100 opportunity score.

    Parameters
    ----------
    expected_excess_return:
        Forecast excess return vs national market, normalised to 0–1 by the
        caller (negative excess returns must already be floored at 0).
    forecast_confidence, investability:
        0–1 multipliers.
    risk_penalty:
        0–100 penalty subtracted after multiplicative combination.
    """
    lo, hi = scale
    raw = expected_excess_return * forecast_confidence * investability * hi
    return (raw - risk_penalty).clip(lower=lo, upper=hi)


def budget_eligible(median_price_m2: pd.Series, typical_surface_m2: float, budget_max_eur: float) -> pd.Series:
    """True where a typical dwelling is purchasable within the budget band."""
    return (median_price_m2 * typical_surface_m2) <= budget_max_eur
