"""
Download Clarke County census tract boundaries and ACS 5-year demographic data,
then merge into a single GeoJSON for the map overlay.

Sources:
  Boundaries: Census TIGER/Line cartographic boundary files (2022, public domain)
  Demographics: Census Bureau ACS 5-year estimates API (2023, free)

Output:
  backend/data/shapefiles/census_tracts/clarke_tracts.geojson

Usage:
  python -m backend.scripts.download_census_data
"""
import json
import logging
import os
import sys

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── constants ─────────────────────────────────────────────────────────────────
# Clarke County, GA — FIPS state=13, county=059
STATE_FIPS = "13"
COUNTY_FIPS = "059"
GEOID_PREFIX = STATE_FIPS + COUNTY_FIPS  # "13059"

# Census TIGER/Line ArcGIS REST API — current census tracts layer
TIGER_TRACTS_URL = (
    "https://tigerweb.geo.census.gov/arcgis/rest/services/"
    "TIGERweb/Tracts_Blocks/MapServer/0/query"
)

# Census ACS 5-year 2023 endpoint
ACS_URL = "https://api.census.gov/data/2023/acs/acs5"

ACS_VARIABLES = {
    "B19013_001E": "median_household_income",
    "B01003_001E": "total_population",
    "B25064_001E": "median_gross_rent",
    "B25077_001E": "median_home_value",
    "B25003_002E": "owner_occupied_units",
    "B25003_003E": "renter_occupied_units",
    "B25002_001E": "total_housing_units",
    "B25002_003E": "vacant_units",
    "B01002_001E": "median_age",
    "B23025_005E": "unemployed_count",
    "B23025_003E": "labor_force",
    "B25035_001E": "median_year_structure_built",
}

OUT_DIR = os.path.join(
    os.getenv("GIS_DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "data")),
    "shapefiles", "census_tracts",
)
OUT_FILE = os.path.join(OUT_DIR, "clarke_tracts.geojson")


# ── helpers ───────────────────────────────────────────────────────────────────

def fetch_tract_boundaries() -> dict:
    """Download Clarke County census tract boundaries from Census TIGER/Line ArcGIS REST."""
    logger.info("Downloading Clarke County census tract boundaries from TIGER/Line...")
    params = {
        "where": f"STATE='{STATE_FIPS}' AND COUNTY='{COUNTY_FIPS}'",
        "outFields": "GEOID,TRACT,NAME",
        "outSR": "4326",
        "f": "geojson",
        "resultRecordCount": 200,   # Clarke County has ~34 tracts
    }
    r = requests.get(TIGER_TRACTS_URL, params=params, timeout=60)
    r.raise_for_status()
    data = r.json()
    features = data.get("features", [])
    logger.info("Downloaded %d Clarke County tract features", len(features))
    return {"type": "FeatureCollection", "features": features}


def fetch_acs_demographics(api_key: str = "") -> dict:
    """
    Fetch ACS 5-year estimates for all Clarke County tracts.
    Returns dict keyed by GEOID ('13059XXXXXX').
    """
    logger.info("Fetching ACS 5-year demographics for Clarke County tracts...")
    vars_str = ",".join(ACS_VARIABLES.keys())
    params = {
        "get": vars_str,
        "for": "tract:*",
        "in": f"state:{STATE_FIPS} county:{COUNTY_FIPS}",
    }
    if api_key:
        params["key"] = api_key

    r = requests.get(ACS_URL, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()

    headers = data[0]
    demo_by_geoid = {}
    for row in data[1:]:
        raw = dict(zip(headers, row))
        tract_code = raw.get("tract", "")
        geoid = STATE_FIPS + COUNTY_FIPS + tract_code.zfill(6)

        demo = {"geoid": geoid, "tract_code": tract_code}
        for api_var, label in ACS_VARIABLES.items():
            v = raw.get(api_var)
            if not v or v in ("-666666666", "-999999999"):
                demo[label] = None
            else:
                # Some ACS fields are floats (e.g. median_age)
                try:
                    demo[label] = float(v) if "." in str(v) else int(v)
                except (ValueError, TypeError):
                    demo[label] = None

        # Derived metrics
        renter = demo.get("renter_occupied_units") or 0
        owner = demo.get("owner_occupied_units") or 0
        total_occ = renter + owner
        demo["renter_pct"] = round(renter / total_occ * 100, 1) if total_occ > 0 else None

        total_housing = demo.get("total_housing_units") or 0
        vacant = demo.get("vacant_units") or 0
        demo["vacancy_rate"] = round(vacant / total_housing * 100, 1) if total_housing > 0 else None

        labor = demo.get("labor_force") or 0
        unemployed = demo.get("unemployed_count") or 0
        demo["unemployment_rate"] = round(unemployed / labor * 100, 1) if labor > 0 else None

        demo_by_geoid[geoid] = demo

    logger.info("Fetched demographics for %d tracts", len(demo_by_geoid))
    return demo_by_geoid


def merge_and_save(boundaries: dict, demographics: dict) -> str:
    """Merge demographic properties into tract boundary features and write GeoJSON."""
    matched = 0
    for feature in boundaries["features"]:
        props = feature.setdefault("properties", {})
        geoid = props.get("GEOID", "")
        demo = demographics.get(geoid)
        if demo:
            props.update(demo)
            matched += 1
        else:
            logger.warning("No ACS data for tract GEOID %s", geoid)

    logger.info("Merged %d / %d tracts with ACS data", matched, len(boundaries["features"]))

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(boundaries, f, separators=(",", ":"))

    size_kb = os.path.getsize(OUT_FILE) / 1024
    logger.info("Saved → %s (%.1f KB)", OUT_FILE, size_kb)
    return OUT_FILE


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    import argparse
    from backend.config import CENSUS_API_KEY

    parser = argparse.ArgumentParser(description="Download Clarke County census tract data")
    parser.add_argument("--api-key", default=CENSUS_API_KEY, help="Census API key (optional)")
    args = parser.parse_args()

    if not args.api_key:
        logger.warning(
            "No Census API key set — requests will be rate-limited. "
            "Get a free key at https://api.census.gov/data/key_signup.html "
            "and add it to .env as CENSUS_API_KEY=..."
        )

    boundaries = fetch_tract_boundaries()
    demographics = fetch_acs_demographics(args.api_key)
    merge_and_save(boundaries, demographics)
    logger.info("Census data download complete.")


if __name__ == "__main__":
    main()
