# Athens RE Intelligence Platform

A full-stack investment research tool built for the Athens, GA real estate market — Clarke and Oconee counties. Every active MLS listing is scored nightly across five weighted dimensions (cash flow, appreciation potential, entry price vs. comps, demand signals, and risk), enriched with rent estimates from multiple sources, and delivered to a map-based dashboard each morning.

This started as an economic study to understand the viability of investing in the Athens market. It turned into a platform that serves up real-time analytics for execution.

---

## Why This Exists

Evaluating a property in Athens means pulling from a half-dozen sources: Redfin for the listing, qPublic for the tax record, the ACC GIS portal for zoning, FEMA for flood risk, GDOT for traffic counts, HUD for rent benchmarks. That's before you run a single number.

The goal was to collapse that workflow into one place — pre-compute everything that can be pre-computed, surface it on a map, and make the decision-support fast enough to actually use every morning.

---

## What It Does

**Nightly Batch Pipeline**
- Scrapes active listings from Redfin (Clarke + Oconee counties via GIS CSV API)
- Runs distressed property intelligence: cross-references qPublic tax records, GSCCCA fi fa liens, ACC Tax Commissioner sale lists, and code enforcement cases
- Pre-computes rent estimates using a three-method chain: census tract ACS median gross rent (adjusted for UGA proximity and bedroom count), Redfin active rental listings (scraped and percentile-averaged by bed count), and HUD Fair Market Rents
- Calculates cash flow for every listing at standard assumptions (20% down, 7% rate, 8% vacancy, 8% management, 1% maintenance)
- Assigns a composite investment score (0–100) and global rank
- Classifies listing events: new, price drop, back on market, disappeared — enabling smart notifications rather than daily noise
- Sends an email digest covering only actionable events: new listings and price drops, sorted by rank

**Dashboard**
- Map-based UI with Leaflet, CartoDB tiles, and layered overlays
- Toggleable GIS overlays: ACC zoning (13 zone types), census tract demographics (6 ACS variables rendered as choropleth), distressed parcels (color-coded by distress score)
- Per-property sidebar: pre-computed score, rent estimate range, cash flow breakdown, cap rate, comparable sales, traffic corridor data, permit activity, flood zone risk
- Email deep-links: clicking a property address in the digest opens the app, flies the map to that property, and expands its card

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, Flask 3.0, Gunicorn |
| GIS | GeoPandas 0.14, Shapely 2.0, Fiona 1.9, PyProj 3.6 |
| Scraping | Requests, BeautifulSoup4, lxml |
| Analysis | NumPy, SciPy |
| Frontend | React 19.2, Vite 8.0 |
| Mapping | Leaflet 1.9.4, react-leaflet 5.0 |
| CI/CD | GitHub Actions |
| Hosting | Azure App Service (Python 3.11, Linux), Azure Static Web Apps |

---

## Architecture

```
GitHub Actions (cron 4am ET)
    │
    ▼
POST /api/internal/run-batch  ←─ protected by X-Batch-Secret header
    │
    ├── Redfin scraper (MLS listings, Clarke + Oconee)
    ├── Distressed pipeline (qPublic, GSCCCA, ACC Tax Commissioner)
    ├── Rent scraper pre-warm (ThreadPoolExecutor → module-level 1hr cache)
    │
    └── Sequential enrichment per listing:
            rent estimate (3-method chain)
            cash flow (30yr amortization, county-specific millage)
            composite score (5-factor weighted)
            global rank assignment
    │
    ▼
Write to /home/site/data/reference/ (Azure persistent storage)
    properties.json · distressed_parcels.json · data_freshness.json · last_run_state.json
    │
    ▼
Flask API reads from file cache (mtime-tracked, re-reads only on batch update)
    │
    ▼
React frontend (pre-built Vite SPA on Azure Static Web Apps)
```

**Why file-based over a database for listings:** The entire enriched dataset is ~350 listings at ~2MB of JSON. A file cache with mtime-tracking is simpler, faster on reads, and requires no database tier. The nightly batch is the only writer; the API is read-only at runtime.

**Why one gunicorn worker:** The batch job runs as a background thread inside the Flask process. With multiple workers, each worker has its own lock state — a second request to `/run-batch` could spawn a duplicate job. One worker + 600s timeout prevents both duplicate runs and the gunicorn heartbeat timeout that would otherwise kill the batch mid-run.

**Why the batch triggers after every deploy:** Azure's runtime directory changes on each deployment. The `workflow_run` trigger on the Deploy Backend workflow guarantees the site has fresh scored data within minutes of any deploy.

---

## Scoring Model

```
Composite Score (0–100)

  Cash Flow       35%   Monthly income after mortgage, taxes, insurance,
                        vacancy, management, maintenance
  Appreciation    25%   Proximity-weighted distance to UGA, downtown,
                        stadiums, greenways, health sciences campus
  Entry Price     20%   Price vs. comparable active listings (4mi radius,
                        same bed count, haversine distance)
  Demand          10%   Amenity proximity (60%) + traffic corridor AADT (40%)
  Risk            10%   Flood zone insurance requirement, building age
```

Clarke County millage: 33.95 mills. Oconee County: 27.0 mills. Tax is calculated on assessed value, not list price, and applied monthly in the cash flow model.

---

## Site Navigation

**Property Map** — Default view. Filter by property type (SFH, Multi-Family, Condo, All). Adjust the top-N slider to focus map pins on the highest-ranked properties. Click any marker to expand the property card with full scoring detail. Toggle zoning, census, or distressed overlays independently.

**Market Overview** — Market-level stats: median list price, absorption rate, active listings, days on market trend.

**Cash Flow Calculator** — Manually adjust down payment, rate, rent, vacancy, management, and maintenance assumptions for any property or hypothetical scenario.

**Development Intel** — Upcoming infrastructure projects, rezoning petitions, and development activity relevant to the Athens market.

**Documentation / FAQ** — Full methodology writeup: scoring weights, rent estimation logic, data sources, limitations.

---

## Data Sources

| Source | What It Provides |
|---|---|
| Redfin GIS CSV | Active MLS listings (semi-public API) |
| qPublic / Schneider Corp | Tax records, owner info, delinquency status |
| GSCCCA | Fi fa liens, lis pendens |
| ACC Tax Commissioner | Tax sale lists |
| HUD User API | Fair Market Rents by metro and bedroom count |
| Census Bureau ACS | Tract-level demographics (5-year estimates) |
| FEMA NFHL | Flood zone shapefiles (downloaded at setup) |
| ACC GIS Server | Zoning + parcel shapefiles (OGC WFS) |
| GDOT AADT | Annual Average Daily Traffic counts (static JSON) |

---

## Deployment

Backend deploys to Azure App Service on any push touching `backend/`, `requirements.txt`, or `startup.txt`. The nightly batch workflow fires on a cron at 4am ET and automatically re-triggers after every successful backend deploy, so the site always has scored data.

Frontend is a Vite-built SPA deployed to Azure Static Web Apps. It's fully static — the API URL is injected at build time via `VITE_API_URL`.

---

## Local Setup

```bash
# Backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in API keys
flask --app backend/api/app.py run --port 5000

# Frontend
cd frontend
npm install
VITE_API_URL=http://localhost:5000 npm run dev

# Run nightly batch locally
python -m backend.jobs.nightly_batch --dry-run
```

GIS shapefiles (zoning, parcels, flood zones) require a one-time download:
```bash
python backend/scripts/download_shapefiles.py
python backend/scripts/download_census_data.py
```

---

## What I'd Build Next

- **Live rent scraping per property:** Currently rent estimates use metro-level HUD FMR and Redfin rental percentiles by bedroom count. A per-address lookup would tighten the estimate considerably.
- **Oconee distressed pipeline:** The distressed property scraper currently covers Clarke County only. Oconee qPublic and lien data structures differ; that's the next county to add.

---

*Not financial advice. Data is algorithmic and assumption-based. Verify before underwriting.*
