# Deployment — Namecheap + Firebase (+ optional OpenShift later)

The site is static (MapLibre + GeoJSON/PMTiles), so the stack is simple.
**Do not add a backend until the data volume forces it** — see §4.

## 1. Firebase Hosting (serves the map)

One-time setup (human, ~10 min):

```bash
npm install -g firebase-tools
firebase login
# Create a project at https://console.firebase.google.com (free Spark plan is enough)
# then, in the repo root:
firebase use --add          # select your project; writes the real id into .firebaserc
firebase deploy --only hosting   # manual first deploy to prove it works
```

`firebase.json` already points Hosting at `web/` and sets CORS + caching for
GeoJSON/PMTiles. After this, the site is live at
`https://<project-id>.web.app`.

Auto-deploy on push (`.github/workflows/firebase-deploy.yml`):

1. In the Firebase console: Project settings → Service accounts → generate a
   private key (or run `firebase init hosting:github` which does this for you).
2. Add the key as repo secret `FIREBASE_SERVICE_ACCOUNT`, and the project id
   as repo variable `FIREBASE_PROJECT_ID`.
3. Pushes to `main` touching `web/` then deploy automatically.

GitHub Pages (`pages.yml`) stays active as a free mirror at
`https://techpolicycomms.github.io/property-opportunity-map/`. Once the custom
domain works on Firebase you can delete `pages.yml` or keep both.

## 2. Namecheap (custom domain)

1. Buy the domain in Namecheap.
2. In the Firebase console: Hosting → Add custom domain → enter the domain.
   Firebase shows you the exact records to create (a TXT verification record
   and A records — **copy the values from the console**, they change over
   time; do not rely on IPs from old blog posts).
3. In Namecheap: Domain List → Manage → Advanced DNS:
   - `TXT` record: host `@`, value = the verification string from Firebase.
   - `A` records: host `@`, values = the IPs Firebase shows.
   - `CNAME` record: host `www`, value = `<project-id>.web.app.`
   - Remove Namecheap's default parking/redirect records if they conflict.
4. Wait for verification + SSL provisioning (minutes to a few hours).
   Firebase provisions the certificate automatically.

## 3. Where the data files live

`web/data/opportunities.geojson` is written by
`python -m pomap.publishing.export_geojson` and committed when small. Once
outputs grow past a few MB, switch to PMTiles in `outputs/pmtiles/` and
either commit them (fine up to ~50 MB) or host them in Firebase Storage /
Cloud Storage and point the viewer at the URL. That decision belongs to the
Publisher role (Gate C, `AGENTS.md`).

## 4. OpenShift (later, optional, only if a backend is needed)

You do **not** need OpenShift today. It becomes relevant only if you outgrow
static files — e.g. on-the-fly spatial queries over the full feature store:

```text
Static now:        MapLibre → GeoJSON/PMTiles (Firebase Hosting) — done
Backend later:     MapLibre → API (DuckDB/PostGIS in a container on OpenShift)
                            → Parquet feature store (object storage)
```

If/when that happens: add a `Dockerfile` + `src/pomap/api/` (FastAPI serving
DuckDB queries), deploy to OpenShift as a container, and keep Firebase for
the front end. That is a Phase 2+ decision — filing it as an issue labelled
`agent:publish` is the right way to park it.

## 5. Costs

| Piece | Cost |
|---|---|
| GitHub repo + Pages + Actions | free (public repo) |
| Firebase Spark (hosting) | free within 10 GB stored / 360 MB/day transfer |
| Namecheap domain | ~$10–15/yr |
| OpenShift | $0 until/unless the backend phase starts |
