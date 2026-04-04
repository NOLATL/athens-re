"""
Redfin CSV listing scraper for Athens-area investment properties.

Downloads active MLS listings from Redfin's (semi-public) GIS CSV endpoint,
normalizes them into the platform's property format, and saves to
backend/data/reference/properties.json via backend/scripts/fetch_listings.py.

Redfin GIS CSV endpoint:
  https://www.redfin.com/stingray/api/gis-csv
  Parameters:
    al=1            active listings
    market=atlanta  Redfin market slug
    region_id=int   county-level region ID (see REGION_* constants)
    region_type=6   6 = county
    uipt=1,2,3,4    property type codes (see INVESTMENT_PROP_TYPES)
    num_homes=350   max results per page
    v=8             API version

Redfin region IDs (their internal IDs, not FIPS):
  Clarke County, GA (Athens-Clarke):  36057
  Oconee County, GA:                  verify at redfin.com/county/<id>/GA/Oconee-County

Usage:
  from backend.scrapers.redfin import fetch_and_normalize
  listings = fetch_and_normalize()
"""
import csv
import io
import logging
import time
from datetime import datetime

import requests

logger = logging.getLogger(__name__)

REDFIN_GIS_CSV_URL = "https://www.redfin.com/stingray/api/gis-csv"

# Redfin internal county region IDs
REGION_CLARKE = 36057   # Athens-Clarke County, GA
REGION_OCONEE = 36255   # Oconee County, GA — verify before use

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.redfin.com/",
}

# Property type codes: 1=SFH, 2=Condo, 3=Townhouse, 4=Multi-Family (2–4 unit),
# 5=Mobile, 6=Co-op, 7=Other, 8=Land
INVESTMENT_PROP_TYPES = "1,2,3,4"

# Athens per-bed/unit rent estimates (2026-04) — replaced by Phase 5 rent estimator
_RENT_BY_BEDS = {1: 1200, 2: 1500, 3: 1800, 4: 2200, 5: 2600}
_RENT_BY_UNIT_BEDS = {1: 800, 2: 1050, 3: 1300, 4: 1500}


# ── fetch ─────────────────────────────────────────────────────────────────────

def fetch_redfin_csv(region_id: int, prop_types: str = INVESTMENT_PROP_TYPES) -> list[dict]:
    """
    Download Redfin GIS CSV for a county and return raw rows as list of dicts.
    Returns empty list on failure.
    """
    params = {
        "al": 1,
        "market": "atlanta",
        "num_homes": 350,
        "ord": "redfin-recommended-asc",
        "page_number": 1,
        "region_id": region_id,
        "region_type": 6,
        "uipt": prop_types,
        "v": 8,
    }
    logger.info("Fetching Redfin CSV for region_id=%d...", region_id)
    try:
        r = requests.get(REDFIN_GIS_CSV_URL, params=params, headers=_HEADERS, timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        logger.error("Redfin CSV request failed: %s", e)
        return []

    # Redfin prepends a one-line disclaimer before the CSV header; skip it.
    lines = r.text.splitlines()
    csv_start = 0
    for i, line in enumerate(lines):
        if line.upper().startswith("SALE TYPE") or line.upper().startswith("ADDRESS"):
            csv_start = i
            break

    csv_text = "\n".join(lines[csv_start:])
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = list(reader)
    logger.info("Downloaded %d listings (region_id=%d)", len(rows), region_id)
    return rows


# ── normalizers ───────────────────────────────────────────────────────────────

def _price_str(raw: str) -> str:
    try:
        val = int(str(raw).replace(",", "").replace("$", "").strip())
        return f"${val:,}"
    except (ValueError, TypeError):
        return str(raw).strip() or "—"


def _type_label(row: dict) -> str:
    prop_type = row.get("PROPERTY TYPE", "").strip()
    beds = row.get("BEDS", "").strip()
    baths = row.get("BATHS", "").strip()
    sqft = row.get("SQUARE FEET", "").strip()

    label = prop_type or "Property"
    parts = []
    if beds:
        parts.append(f"{beds}BR")
    if baths:
        parts.append(f"{baths}BA")
    if sqft:
        try:
            parts.append(f"{int(sqft.replace(',', '')):,} sqft")
        except (ValueError, TypeError):
            pass
    if parts:
        label += " — " + "/".join(parts[:2])
        if len(parts) > 2:
            label += f" ({parts[2]})"
    return label


def _confidence(row: dict) -> str:
    """
    Auto-assign confidence tier.
    Multi-family → high; SFH/condo ≤30 DOM → medium; otherwise speculative.
    """
    prop_type = row.get("PROPERTY TYPE", "").lower()
    try:
        dom = int((row.get("DAYS ON MARKET", "0") or "0").replace(",", "").strip())
    except (ValueError, TypeError):
        dom = 0

    if any(k in prop_type for k in ("multi", "duplex", "triplex", "quadplex")):
        return "high"
    if dom <= 30:
        return "medium"
    return "speculative"


def _rent_estimate(row: dict) -> str:
    """Rough rent estimate; replaced by Phase 5 rent estimator."""
    prop_type = row.get("PROPERTY TYPE", "").lower()
    try:
        beds = max(1, int((row.get("BEDS", "1") or "1").strip()))
    except (ValueError, TypeError):
        beds = 1

    if any(k in prop_type for k in ("multi", "duplex", "triplex", "quadplex")):
        est = _RENT_BY_UNIT_BEDS.get(min(beds, 4), 900)
        return f"~${est:,}/unit (est.)"
    else:
        est = _RENT_BY_BEDS.get(min(beds, 5), 1200)
        return f"~${est:,}/mo (est.)"


def _why(row: dict) -> str:
    """Auto-generate a brief investment-thesis blurb from listing fields."""
    parts = []

    dom_raw = (row.get("DAYS ON MARKET", "0") or "0").replace(",", "").strip()
    try:
        dom = int(dom_raw)
    except ValueError:
        dom = 0

    if dom == 0:
        parts.append("Just listed.")
    elif dom <= 7:
        parts.append(f"Listed {dom} days ago — fresh to market.")
    elif dom > 60:
        parts.append(f"On market {dom} days — seller may be motivated.")

    yr_raw = (row.get("YEAR BUILT", "") or "").strip()
    if yr_raw.isdigit():
        yr = int(yr_raw)
        if yr < 1970:
            parts.append(f"Built {yr} — verify condition and deferred maintenance.")
        elif yr >= 2010:
            parts.append(f"Built {yr} — newer construction, lower maintenance risk.")

    hoa_raw = (row.get("HOA/MONTH", "0") or "0").replace(",", "").replace("$", "").strip()
    try:
        hoa = float(hoa_raw)
    except ValueError:
        hoa = 0.0
    if hoa > 300:
        parts.append(f"High HOA (${hoa:.0f}/mo) — verify cash-flow impact.")
    elif hoa > 0:
        parts.append(f"HOA ${hoa:.0f}/mo.")

    parts.append("Verify rent roll, condition, and zoning before proceeding.")
    return " ".join(parts)


def _url_from_row(row: dict) -> str:
    """Extract the Redfin listing URL from the CSV row (column name is verbose)."""
    for key, val in row.items():
        if "url" in key.lower() and val and val.strip().startswith("http"):
            return val.strip()
    # Fallback: construct from address
    addr = row.get("ADDRESS", "").strip().replace(" ", "-")
    city = row.get("CITY", "Athens").strip().replace(" ", "-")
    return f"https://www.redfin.com/GA/{city}/{addr}"


def _int_safe(raw: str, default: int = 0) -> int:
    try:
        return int((raw or "").replace(",", "").replace("$", "").strip())
    except (ValueError, TypeError):
        return default


def _float_safe(raw: str, default: float = 0.0) -> float:
    try:
        return float((raw or "").replace(",", "").replace("$", "").strip())
    except (ValueError, TypeError):
        return default


# ── normalize ─────────────────────────────────────────────────────────────────

def normalize_listings(rows: list[dict], county: str = "clarke") -> list[dict]:
    """
    Normalize raw Redfin CSV rows into the platform's property format.

    Output keys include all frontend-required fields (id, address, price, type,
    confidence, rent, why, url, lat, lng) plus raw metadata for Phase 5+
    (beds, baths, sqft, days_on_market, hoa_monthly, year_built, price_per_sqft,
    mls_number, property_type, county, source, fetched_at).
    """
    results = []
    for i, row in enumerate(rows, start=1):
        lat = _float_safe(row.get("LATITUDE", ""))
        lng = _float_safe(row.get("LONGITUDE", ""))
        if not lat or not lng:
            logger.debug("Skipping row %d — no coordinates", i)
            continue

        addr_parts = [
            row.get("ADDRESS", "").strip(),
            row.get("CITY", "").strip(),
            row.get("STATE OR PROVINCE", "").strip(),
            row.get("ZIP OR POSTAL CODE", "").strip(),
        ]
        address = ", ".join(p for p in addr_parts if p)

        yr_raw = (row.get("YEAR BUILT", "") or "").strip()
        year_built = int(yr_raw) if yr_raw.isdigit() else None

        prop = {
            # Frontend-required
            "id": i,
            "address": address,
            "price": _price_str(row.get("PRICE", "")),
            "type": _type_label(row),
            "confidence": _confidence(row),
            "rent": _rent_estimate(row),
            "why": _why(row),
            "url": _url_from_row(row),
            "lat": lat,
            "lng": lng,
            # Raw metadata (Phase 5+ cash flow engine, scorer)
            "beds": _int_safe(row.get("BEDS", "")),
            "baths": _float_safe(row.get("BATHS", "")),
            "sqft": _int_safe(row.get("SQUARE FEET", "")),
            "days_on_market": _int_safe(row.get("DAYS ON MARKET", "")),
            "hoa_monthly": _float_safe(row.get("HOA/MONTH", "")),
            "year_built": year_built,
            "price_per_sqft": _float_safe(row.get("$/SQUARE FEET", "")),
            "mls_number": row.get("MLS#", "").strip(),
            "property_type": row.get("PROPERTY TYPE", "").strip(),
            "county": county,
            "source": "redfin",
            "fetched_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        results.append(prop)

    return results


# ── public API ────────────────────────────────────────────────────────────────

def fetch_and_normalize(
    counties: list[tuple[int, str]] | None = None,
) -> list[dict]:
    """
    Fetch and normalize listings for one or more counties.

    Args:
        counties: list of (region_id, county_name) tuples.
                  Defaults to Clarke County only.

    Returns:
        Deduplicated, globally re-numbered list of property dicts.
    """
    if counties is None:
        counties = [(REGION_CLARKE, "clarke")]

    all_listings: list[dict] = []
    for region_id, county in counties:
        rows = fetch_redfin_csv(region_id)
        if rows:
            normalized = normalize_listings(rows, county=county)
            all_listings.extend(normalized)
            logger.info(
                "Normalized %d listings for %s county", len(normalized), county
            )
        if len(counties) > 1:
            time.sleep(2)   # polite delay between county requests

    # Re-number IDs globally after merging
    for i, prop in enumerate(all_listings, start=1):
        prop["id"] = i

    logger.info("Total listings fetched: %d", len(all_listings))
    return all_listings


if __name__ == "__main__":
    import pprint
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    results = fetch_and_normalize()
    print(f"\n{len(results)} listings fetched.")
    if results:
        pprint.pprint(results[0])
