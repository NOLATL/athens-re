"""
Central configuration for the Athens RE investment platform.
Load secrets from .env — never commit .env to git.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Search criteria ──────────────────────────────────────────────────────────
SEARCH_CRITERIA = {
    "locations": ["Athens-Clarke County, GA", "Oconee County, GA"],
    "property_types": ["single-family", "duplex", "triplex", "quadplex"],
    "min_bedrooms": 2,
    "down_payment_pct": 10,
    "interest_rate": 6.5,
    "tax_millage": {"clarke": 33.95, "oconee": 27.0},
    "insurance_monthly_est": 120,
    "maintenance_pct": 5,
    "vacancy_pct": 5,
    "management_pct": 10,
    "min_monthly_cashflow": -200,
    "min_composite_score": 50,
    "score_weights": {
        "cash_flow": 0.35,
        "appreciation": 0.25,
        "entry_price": 0.20,
        "demand": 0.10,
        "risk": 0.10,
    },
}

# ── Database ─────────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///backend/db/real_estate.db")

# ── API keys ─────────────────────────────────────────────────────────────────
CENSUS_API_KEY = os.getenv("CENSUS_API_KEY", "")
RENTOMETER_API_KEY = os.getenv("RENTOMETER_API_KEY", "")

# ── Key Athens coordinates ────────────────────────────────────────────────────
LOCATIONS = {
    "uga_campus": (33.9480, -83.3774),
    "sanford_stadium": (33.9499, -83.3733),
    "akins_ford_arena": (33.9601, -83.3775),
    "downtown_athens": (33.9601, -83.3774),
    "epps_bridge": (33.9297, -83.4444),
    "uga_health_sciences": (33.9426, -83.3620),
}

# ── Distressed property intelligence ─────────────────────────────────────────
DISTRESS_WEIGHTS = {
    "tax_sale_list":           40,
    "tax_delinquent_1yr":      30,
    "fi_fa_lien":              25,
    "code_violation_active":   20,
    "water_disconnected_6mo":  20,   # FOIA-only, deferred
    "code_violations_3yr":     15,
    "absentee_owner":          15,
    "probate_filing":          15,
    "assessed_value_declining": 10,
    "pre1970_no_permits":      10,
}
DISTRESS_TIERS = {"high": 50, "medium": 25, "low": 0}

QPUBLIC_CLARKE_URL = "https://qpublic.schneidercorp.com/Application.aspx?AppID=830&LayerID=14971&PageTypeID=4&PageID=7071"
GSCCCA_BASE_URL = "https://search.gsccca.org/RealEstate"
ACC_TAX_SALE_URL = "https://www.accgov.com/1703"
ACC_OPENDATA_URL = "https://data-athensclarke.opendata.arcgis.com"

# ── Email / notifications ─────────────────────────────────────────────────────
EMAIL_PROVIDER    = os.getenv("EMAIL_PROVIDER", "smtp")   # "smtp" | "sendgrid"
SMTP_HOST         = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT         = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER         = os.getenv("SMTP_USER", "")
SMTP_PASS         = os.getenv("SMTP_PASS", "")
SENDGRID_API_KEY  = os.getenv("SENDGRID_API_KEY", "")
NOTIFY_EMAIL      = os.getenv("NOTIFY_EMAIL", "")         # recipient
FROM_EMAIL        = os.getenv("FROM_EMAIL", "noreply@athens-re.app")

# ── Shapefile paths ───────────────────────────────────────────────────────────
# On Azure App Service set GIS_DATA_DIR=/home/site/data (persistent, survives deploys).
# Locally defaults to backend/data/ relative to this file.
DATA_DIR = os.getenv("GIS_DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))
SHAPEFILES = {
    "acc_zoning": os.path.join(DATA_DIR, "shapefiles", "acc_zoning"),
    "acc_parcels": os.path.join(DATA_DIR, "shapefiles", "acc_parcels"),
    "oconee_zoning": os.path.join(DATA_DIR, "shapefiles", "oconee_zoning"),
    "fema_flood": os.path.join(DATA_DIR, "shapefiles", "fema_flood"),
    "census_tracts": os.path.join(DATA_DIR, "shapefiles", "census_tracts"),
    "greenway_network": os.path.join(DATA_DIR, "shapefiles", "greenway_network"),
    "sr316_corridor": os.path.join(DATA_DIR, "shapefiles", "sr316_corridor"),
}
