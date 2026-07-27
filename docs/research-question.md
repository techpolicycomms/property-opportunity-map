# Research question

> **Which currently affordable European locations have the highest probability
> of materially outperforming their national housing market over the next
> 10–20 years?**

This is deliberately **not** "what is this property worth?" — that is an
automated valuation model (AVM), a solved problem with many incumbents. Our
contribution is an open, reproducible, **point-in-time** spatial forecasting
system combining valuation, future infrastructure, demographic change, supply
constraints and risk.

## Three distinct outputs

| Output | Question |
|---|---|
| Present-value model | Is this location currently expensive or inexpensive relative to comparable places? |
| Appreciation model | What real and nominal price growth is plausible over 5, 10 and 20 years? |
| Investability filter | Can someone actually purchase, maintain, insure, rent and resell here? |

A €60,000 house in a depopulating municipality is cheap but not undervalued.
The target signature is:

```text
Low current valuation
+ rising future demand
+ constrained future supply
+ credible infrastructure catalyst
+ manageable physical and regulatory risk
+ sufficient market liquidity
```

## Return calibration

| Goal | Required nominal CAGR |
|---|---|
| 4× over 20 years | ~7.2%/yr |
| 10× over 20 years | ~12.2%/yr |
| 4× over 10 years | ~14.9%/yr |
| 10× over 10 years | ~25.9%/yr |

These are pre-cost figures (before acquisition costs, taxes, maintenance,
inflation, selling costs). The model therefore reports expected CAGR
**distributions** (10th/50th/90th percentile), never labels like "high
potential".

## Scope decision: France first

France is the pilot because DVF/DVF+ publishes completed, geolocated
**transaction** data — enabling transaction-level modelling, repeat-sales
analysis, infrastructure event studies and honest historical backtesting.
Italy (OMI zone intervals) and Spain (less harmonised completed-sale data)
follow in later phases via national adapters, with harmonised EU sources
(Eurostat HPI, GISCO, GEOSTAT, TENtec, EEA) providing cross-country context.

## What counts as an opportunity (initial filter)

```text
Budget eligibility:   median purchasable property ≤ €200,000
Historical evidence:  sufficient transaction count
Fundamentals:         positive population/employment/accessibility trajectory
Valuation:            discount relative to matched peers
Supply:               limited or slow supply response
Catalyst:             funded or credible future infrastructure
Risk:                 no severe unresolved physical or regulatory penalty
Forecast:             positive expected excess return with acceptable uncertainty
```
