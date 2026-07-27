# Handoff: publish — Firebase Hosting Deployment

- **Date:** 2026-07-27
- **Author role:** agent:publish (tool: Antigravity)
- **Issue/PR:** Manual deploy setup (docs/deployment.md §1)

## What changed

- Created Firebase project `property-opportunity-map`.
- Updated `.firebaserc` to set `"default": "property-opportunity-map"`.
- Deployed `web/` site to Firebase Hosting via `firebase deploy --only hosting`.

## What was verified

- Deployed site is live at: `https://property-opportunity-map.web.app`
- Headless browser verification via Playwright confirmed:
  - Carto Positron basemap loads cleanly.
  - Fallback logic correctly fetches `data/opportunities.sample.geojson` when `data/opportunities.geojson` is not found (HTTP 404).
  - Status banner updates to: `Showing sample data until the first real scoring run is published.`
  - Both synthetic sample points ("SAMPLE Béziers corridor" and "SAMPLE Montpellier periphery") render on the circle layer.
  - Map feature clicks and canvas clicks trigger popups displaying correct properties (median price, 10y CAGR, excess return, annual transactions, opportunity score, known_as_of date, and formatted positive/risk drivers).

## Known-broken / unverified

- None. Map rendering and popups work as expected.

## Next role should

- `agent:publish`: Export real scoring outputs via `python -m pomap.publishing.export_geojson` to `web/data/opportunities.geojson` once `agent:model` completes the scoring pipeline.
