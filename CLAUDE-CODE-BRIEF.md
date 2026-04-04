# Athens GA Real Estate Investment Intelligence Platform
## Claude Code Project Brief — v2

**Project Path:** `C:\GitHubProjects\Real_Estate`
**New Conda Environment:** `real_estate`

---

## Vision

A full-stack investment intelligence tool that evaluates Athens-area rental properties the way a seasoned local investor would — not just listing price and rent estimates, but zoning context, demographic trajectories, infrastructure investment, traffic patterns, nearby development activity, and tax assessment history. Every property gets scored across these dimensions automatically so Jared can see at a glance what's worth pursuing and why a seller is charging what they're charging.

## Investment Criteria

- **Priority 1:** Cash flow (rent vs. mortgage/expenses)
- **Priority 2:** Appreciation potential (growth corridors, development proximity)
- **Priority 3:** Entry price / deal hunting
- **Priority 4:** Proximity to UGA / student rental demand
- **Scope:** Single-family + duplexes/small multifamily
- **Geography:** Clarke County + Oconee County (Watkinsville, Bogart)

---

## 1. Environment Setup

```bash
conda create -n real_estate python=3.11 -y
conda activate real_estate

# Core
pip install flask gunicorn  # or fastapi uvicorn
pip install requests beautifulsoup4 lxml
pip install pandas geopandas shapely fiona pyproj
pip install sqlalchemy alembic
pip install python-dotenv

# GIS / Mapping
pip install folium                  # Interactive Leaflet maps in Python
pip install contextily              # Basemap tiles for matplotlib/geopandas
pip install rasterstats             # Zonal statistics from rasters
pip install geocoder                # Address geocoding

# Data / Analysis
pip install scipy scikit-learn      # Scoring models
pip install openpyxl                # Excel export

# Frontend (npm — separate from conda)
# Run from project root:
# npm create vite@latest frontend -- --template react
# cd frontend && npm install leaflet react-leaflet

# Azure deployment
pip install azure-functions-core-tools  # If using Azure Functions
```

---

## 2. Project Structure

```
C:\GitHubProjects\Real_Estate\
│
├── frontend/                        # React dashboard (Vite)
│   ├── src/
│   │   ├── App.jsx                  # Main dashboard (ported from artifact)
│   │   ├── components/
│   │   │   ├── PropertyMap.jsx      # Leaflet map with GIS overlays
│   │   │   ├── CashFlowCalc.jsx
│   │   │   ├── PropertyCard.jsx
│   │   │   ├── DevelopmentIntel.jsx
│   │   │   └── DemographicOverlay.jsx
│   │   └── data/                    # JSON consumed by frontend
│   │       ├── properties.json
│   │       ├── market-stats.json
│   │       └── development-projects.json
│   └── package.json
│
├── backend/                         # Python analysis engine
│   ├── scrapers/
│   │   ├── redfin_scraper.py
│   │   ├── zillow_scraper.py
│   │   └── listing_normalizer.py    # Normalize data across sources
│   ├── analysis/
│   │   ├── cash_flow_engine.py      # Mortgage, tax, insurance, rent estimation
│   │   ├── property_scorer.py       # Multi-factor scoring algorithm
│   │   ├── rent_estimator.py        # Comp-based rent estimation
│   │   └── appreciation_model.py    # Growth corridor proximity scoring
│   ├── gis/
│   │   ├── zoning_lookup.py         # Query ACC/Oconee zoning shapefiles
│   │   ├── flood_zone.py            # FEMA NFHL overlay
│   │   ├── census_demographics.py   # Census API tract-level demographics
│   │   ├── traffic_counts.py        # GDOT AADT data
│   │   ├── proximity_scoring.py     # Distance to UGA, arena, greenway, 316
│   │   └── development_tracker.py   # Nearby permits, rezoning, projects
│   ├── data/
│   │   ├── shapefiles/              # Downloaded ESRI shapefiles
│   │   │   ├── acc_zoning/
│   │   │   ├── acc_parcels/
│   │   │   ├── oconee_zoning/
│   │   │   ├── fema_flood/
│   │   │   ├── census_tracts/
│   │   │   ├── greenway_network/
│   │   │   └── sr316_corridor/
│   │   └── reference/
│   │       ├── millage_rates.json
│   │       ├── rent_comps.json
│   │       └── development_projects.json
│   ├── db/
│   │   ├── models.py                # SQLAlchemy models
│   │   └── real_estate.db           # SQLite (or Azure SQL)
│   ├── alerts/
│   │   ├── alert_engine.py          # New listing detection + scoring
│   │   └── email_sender.py          # HTML email builder + SMTP
│   ├── api/
│   │   └── app.py                   # Flask/FastAPI serving data to frontend
│   └── config.py                    # All settings, criteria, API keys
│
├── azure/                           # Azure deployment configs
│   ├── function_app/                # Azure Functions for scheduled scraping
│   │   ├── function_app.py
│   │   ├── host.json
│   │   └── requirements.txt
│   └── app_service/                 # Azure App Service for web dashboard
│       ├── startup.sh
│       └── web.config
│
├── .env                             # API keys, email creds (gitignored)
├── environment.yml                  # Conda environment export
└── README.md
```

---

## 3. The Analysis Engine — What Actually Makes This Valuable

Every property gets scored across these dimensions. The goal: understand why a seller is charging what they're charging, and whether the numbers work for YOU.

### A. Cash Flow Analysis (cash_flow_engine.py)

```
Purchase price → Down payment → Loan amount → Monthly P&I
+ Property tax (auto-lookup: Clarke 33.95 mills, Oconee ~27 mills, on 40% assessed)
+ Insurance (estimate by construction type, age, flood zone)
+ Maintenance reserve (5% of rent)
+ Vacancy reserve (5% of rent, higher for student-heavy areas)
+ Property management (10% of rent)
= Total monthly expense
vs. Estimated monthly rent (from comp engine)
= Monthly cash flow, Cash-on-cash return, Cap rate
```

### B. Rent Estimation Engine (rent_estimator.py)

Don't guess — comp it:
- Pull active rental listings within 0.5mi radius, same bedroom count
- Pull recently leased comps (Zillow rental history, Rentometer API $30/mo)
- Weight by: distance, age similarity, sqft similarity, condition
- Adjust for: student demand premium (within 1mi of UGA), school district premium (Oconee), furnished vs unfurnished
- Output: estimated rent range (low/mid/high) with confidence score

### C. Seller Price Intelligence — Why It Costs What It Costs

This is what separates amateur analysis from professional. For each listing, auto-generate a "seller's pricing thesis":

**Tax Assessment History**
- Source: ACC Tax Assessor (public records, scrapeable)
- Pull 5-year assessed value history
- Flag: if assessed value << list price, seller pricing aggressively
- Flag: if assessed value recently jumped, tax bill about to increase for buyer

**Days on Market + Price History**
- Source: Redfin/Zillow price history
- Days listed, number of price reductions, original vs current price
- Flag: 30+ DOM with reductions = motivated seller, negotiate hard

**Comparable Recent Sales**
- Sold comps within 0.5mi, last 6 months, similar type
- Price per sqft vs listing price per sqft
- Flag: listing priced >10% above comp average = overpriced

**Property Condition Signals**
- Year built, last renovation date (from listing text NLP)
- Roof age, HVAC age (if mentioned in description)
- Flag: pre-1980 construction = possible lead paint, older systems
- Flag: "as-is" in listing text = deferred maintenance likely

**Lot & Zoning Value**
- Lot size vs building footprint = ADU potential?
- Current zoning = what COULD this property become?
- Adjacent parcel zoning changes (from ACC rezoning records)
- Flag: RS-15 with large lot = potential subdivision or ADU opportunity

### D. GIS & Spatial Intelligence

**Zoning Analysis (zoning_lookup.py)**
- Source: ACC Open Data Portal (ArcGIS Hub)
  - URL: https://data-athensclarke.opendata.arcgis.com/
  - Layers: Parcels (updated nightly), Zoning, Historic Districts
- Source: Oconee County GIS
- For each property: current zone, permitted uses, setbacks, density
- Flag: properties in zones allowing multifamily or mixed-use
- Flag: properties adjacent to recently rezoned parcels (upzone trend)

**Flood Zone (flood_zone.py)**
- Source: FEMA National Flood Hazard Layer (NFHL)
  - Download: https://msc.fema.gov/portal/advanceSearch
  - Or: FEMA's ArcGIS REST services
- For each property: flood zone designation (X, AE, A, etc.)
- Impact: Zone AE/A = flood insurance required ($1,500-3,000/yr) — kills cash flow
- Flag: any property in a flood zone with insurance cost estimate

**Census Demographics (census_demographics.py)**
- Source: US Census Bureau API (free, key required from census.gov)
  - ACS 5-year estimates at census tract level
  - API: https://api.census.gov/data/2023/acs/acs5
- Variables to pull per tract:
  - B19013_001E: Median household income
  - B01003_001E: Total population
  - B25064_001E: Median gross rent
  - B25077_001E: Median home value
  - B25003_003E: Renter-occupied units (demand signal)
  - B25002_003E: Vacant units (oversupply signal)
  - B01002_001E: Median age
  - B15003_022E+: Educational attainment (bachelor's+)
  - B23025_005E: Unemployment
  - B25035_001E: Median year structure built
- Population growth: compare 2019 vs 2023 ACS for growth rate by tract
- Income trajectory: same comparison for median HH income trend

**Traffic Counts (traffic_counts.py)**
- Source: GDOT Traffic Data Application
  - Interactive: https://gdottrafficdata.drakewell.com/publicmultinodemap.asp
  - Downloadable: http://geocounts.com/gdot
  - Also: GDOT's STARS reports
- Pull: Annual Average Daily Traffic (AADT) for roads adjacent to property
- Why it matters: high traffic = commercial potential, visibility for businesses; low traffic on residential street = quality of life for tenants
- Flag: properties on or near high-AADT corridors (commercial upside)

**Proximity Scoring (proximity_scoring.py)**

Calculate straight-line and driving distance to key value drivers:

| Target | Why It Matters |
|--------|---------------|
| UGA Campus (centroid) | Student/grad rental demand |
| Sanford Stadium | Game day premium |
| Akins Ford Arena | Event economy, district development |
| Downtown Athens (center) | Walkability, nightlife, employment |
| Planned Greenway segments | Amenity premium, appreciation |
| SR 316 interchanges (new) | Commuter access to Atlanta jobs |
| Oconee County school boundary | School district premium |
| Epps Bridge shopping | Retail convenience |
| UGA Health Sciences Campus | Medical school expansion |

Score: weighted proximity index (closer to more targets = higher score)

**Building Permit Activity (development_tracker.py)**
- Source: ACC Building Permits (check open data portal, or FOIA)
- Pull: new construction permits, renovation permits within 0.5mi radius
- Rising permit activity = neighborhood investment trend = appreciation signal
- Flag: clusters of new permits near a listing

### E. Composite Property Score (property_scorer.py)

Roll everything into a single 0-100 score:

```
Score = (
    cash_flow_score x 0.35        # Monthly CF, CoC return, cap rate
  + appreciation_score x 0.25     # Proximity to development, permit activity, corridor
  + entry_price_score x 0.20      # Price vs comps, price per sqft, DOM leverage
  + demand_score x 0.10           # Renter %, UGA proximity, vacancy rate
  + risk_score x 0.10             # Flood zone, age, condition, tax trajectory
)
```

Each sub-score 0-100 based on percentile rank within current listings.

### F. Additional Factors to Consider

Things not yet mentioned but will materially impact returns:

- **School district boundary precision** — A property at the Clarke/Oconee line could be in either school district. North Oconee schools command a 15-20% rent premium. Verify with GIS parcel overlay, not just address.
- **Section 8 / Housing Choice Voucher demand** — Clarke County has significant voucher demand. Properties meeting HUD Fair Market Rent standards can have guaranteed income streams. Athens Housing Authority publishes FMR rates.
- **HOA and special assessment risk** — For condos/townhomes, HOA financial health matters. Check reserves, pending special assessments, litigation.
- **Utility structure** — Some Athens rentals have tenant-paid utilities, some don't. ACC water bills can be $80-120/mo. Verify who pays.
- **Landlord registration** — ACC requires annual landlord registration. Minor cost but compliance required.
- **Lead paint disclosure** — Pre-1978 properties require EPA disclosure. Remediation can cost $5-20K.
- **Radon levels** — Georgia has moderate radon risk. Basement units (like the Creekwood triplex) should be tested. Mitigation ~$1,000-1,500.
- **Homeowner insurance trends** — Georgia insurers increasing rates 8-15% annually. Get quotes BEFORE making offers.
- **1031 exchange pipeline** — Some sellers are selling for 1031 exchanges (motivated, on a deadline). Listing text clues: "1031", "tax deferred", seller timeline.
- **Cap rate benchmarks** — Athens investment market typically trades at 5-7% cap rates. Above 7% = deal. Below 5% = paying for appreciation.
- **Athens short-term rental ban context** — ACC banned non-owner-occupied STRs in residential zones (Feb 2024). Properties with legal non-conforming STR status (grandfathered until Mar 2027) have premium value. After Mar 2027, long-term rental is the only option in residential zones.

---

## 4. GIS Data Sources — Where to Get the Shapefiles

| Dataset | Source | Format | URL |
|---------|--------|--------|-----|
| ACC Parcels | ACC Open Data | Shapefile/GeoJSON | https://data-athensclarke.opendata.arcgis.com/ (search "Parcels") |
| ACC Zoning | ACC Open Data | Shapefile/GeoJSON | Same portal (search "Zoning") |
| ACC Zoning Viewer | ACC ArcGIS | Interactive | https://www.arcgis.com/apps/instant/interactivelegend/index.html?appid=548118de1d454cebbbdf52acbd2da5a9 |
| ACC Historic Districts | ACC Open Data | Shapefile | Same portal |
| Oconee County Parcels | Oconee Tax Assessor / Regrid | Shapefile | https://qpublic.schneidercorp.com/ or Regrid.com |
| FEMA Flood Zones | FEMA MSC | Shapefile | https://msc.fema.gov/portal/advanceSearch |
| Census Tract Boundaries | Census TIGER/Line | Shapefile | https://www.census.gov/cgi-bin/geo/shapefiles/index.php |
| Greenway Network Plan | ACC Leisure Services | PDF/GIS | https://www.accgov.com/7143/Greenway-Network-Master-Plan |
| SR 316 Project Areas | GDOT ArcGIS Hub | GIS layers | https://transformingsr316-gdot.hub.arcgis.com/ |
| GDOT Traffic Counts | GDOT OTD | CSV/Interactive | https://gdottrafficdata.drakewell.com/ |
| Census Demographics | Census Bureau API | JSON | https://api.census.gov/data.html (free key required) |
| Census TIGERweb Boundaries | Census | REST API | https://tigerweb.geo.census.gov/arcgis/rest/services/ |
| Building Permits | ACC (check portal) | CSV/API | Open data portal or FOIA |

---

## 5. Azure Deployment Architecture

### Web Dashboard — Azure App Service

```
Frontend (React build) + Backend API (Flask/FastAPI)
→ Deploy as a single Azure App Service
→ Serves the dashboard at https://your-app.azurewebsites.net
→ Reads from Azure SQL or SQLite in blob storage
```

Estimated cost: Free tier works for personal use. B1 (~$13/mo) for always-on.

### Scheduled Scraping — Azure Functions (Timer Trigger)

```python
# azure/function_app/function_app.py
import azure.functions as func

app = func.FunctionApp()

@app.timer_trigger(schedule="0 0 11 * * *",   # 7am ET daily (UTC 11:00)
                   arg_name="myTimer",
                   run_on_startup=False)
def daily_listing_scan(myTimer: func.TimerRequest) -> None:
    # 1. Scrape new listings from Redfin/Zillow
    # 2. Run through full analysis engine (cash flow, GIS, demographics)
    # 3. Score each property (composite 0-100)
    # 4. Compare against seen_listings table → identify new ones
    # 5. Store scored listings in database
    # 6. Send email alert if new matches above threshold
    pass
```

Azure Functions consumption plan: first 1M executions/month free. ~$0/mo for a daily timer.

### Email Alerts — Options

1. **SendGrid** (Azure integrated, 100 emails/day free tier)
2. **Azure Communication Services** (native email)
3. **Gmail SMTP** (works from Azure Functions, use app password)

### Database — Recommended Path

Start with **SQLite locally** during development. Migrate to **Azure SQL Free Tier** (32GB) when deploying. Schema supports both identically via SQLAlchemy.

### Alternative to Email: Just Check the App

Since this will be on Azure App Service, the dashboard itself becomes the "alert" — new high-scoring properties appear at the top of the Property Map tab with a "NEW" badge. Check it over morning coffee. Email alerts are a nice-to-have addition, not the core workflow.

---

## 6. Search Criteria Config

```python
# backend/config.py
SEARCH_CRITERIA = {
    "locations": ["Athens-Clarke County, GA", "Oconee County, GA"],
    "property_types": ["single-family", "duplex", "triplex", "quadplex"],
    "min_bedrooms": 2,
    "down_payment_pct": 25,
    "interest_rate": 6.5,
    "tax_millage": {"clarke": 33.95, "oconee": 27.0},
    "insurance_monthly_est": 120,
    "maintenance_pct": 5,
    "vacancy_pct": 5,
    "management_pct": 10,
    "min_monthly_cashflow": -200,    # Allow slightly negative for appreciation plays
    "min_composite_score": 50,       # Only alert above this threshold
    "score_weights": {
        "cash_flow": 0.35,
        "appreciation": 0.25,
        "entry_price": 0.20,
        "demand": 0.10,
        "risk": 0.10,
    },
}
```

---

## 7. Files Included

1. **athens-investment-dashboard.jsx** — Full React dashboard (5 tabs, 9 properties, Leaflet map, cash flow calc)
2. **CLAUDE-CODE-BRIEF.md** — This document

---

## 8. Claude Code Kickoff Prompt

```
I'm building a real estate investment intelligence platform for Athens, GA.
Project lives at C:\GitHubProjects\Real_Estate. I need you to:

1. Create a conda environment called `real_estate` with Python 3.11
2. Scaffold the full project structure from my brief
3. Set up a Vite + React frontend with Leaflet + react-leaflet
4. Port my dashboard artifact into src/App.jsx with CARTO dark map tiles
5. Get the frontend running with `npm run dev`
6. Then we'll build the Python analysis engine starting with GIS/shapefile layer

Here's my project brief: [paste this document]
Here's my dashboard artifact: [paste or reference the JSX file]
```

---

## 9. Build Priority Order

| Phase | What | Effort |
|-------|------|--------|
| 1 | Frontend + Leaflet map working locally | 1 hour |
| 2 | GIS overlays (zoning, parcels, flood zones on map) | 3-4 hours |
| 3 | Census demographic layer per tract | 2 hours |
| 4 | Listing scraper (Redfin CSV approach) | 2-3 hours |
| 5 | Cash flow engine + rent estimator | 2 hours |
| 6 | Seller price intelligence (tax history, DOM, comps) | 3-4 hours |
| 7 | Composite property scorer (0-100) | 2 hours |
| 8 | Traffic counts + permit data | 2 hours |
| 9 | Azure App Service deployment | 2 hours |
| 10 | Azure Functions (daily scrape + optional email) | 2-3 hours |
| **Total** | | **~20-25 hours** |
