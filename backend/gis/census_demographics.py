"""
Pull ACS 5-year estimates from the Census Bureau API for Clarke County, GA
and serve as GeoJSON for the map choropleth overlay.

Free API key: https://api.census.gov/data/key_signup.html
The key is optional — requests work without it, just rate-limited to 500/day.
"""
import os
import json
import logging

import requests
from backend.config import CENSUS_API_KEY

logger = logging.getLogger(__name__)

BASE_URL = "https://api.census.gov/data/2023/acs/acs5"

VARIABLES = {
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

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "shapefiles", "census_tracts")


def _build_params(for_clause: str, in_clause: str) -> dict:
    params = {
        "get": ",".join(VARIABLES.keys()),
        "for": for_clause,
        "in": in_clause,
    }
    if CENSUS_API_KEY:
        params["key"] = CENSUS_API_KEY
    return params


def _parse_row(headers: list, row: list) -> dict:
    raw = dict(zip(headers, row))
    result = {}
    for api_var, label in VARIABLES.items():
        v = raw.get(api_var)
        result[label] = int(v) if v and v not in ("-666666666", "-999999999") else None

    # Derived metrics
    renter = result.get("renter_occupied_units") or 0
    owner = result.get("owner_occupied_units") or 0
    total_occ = renter + owner
    result["renter_pct"] = round(renter / total_occ * 100, 1) if total_occ > 0 else None

    total_housing = result.get("total_housing_units") or 0
    vacant = result.get("vacant_units") or 0
    result["vacancy_rate"] = round(vacant / total_housing * 100, 1) if total_housing > 0 else None

    labor = result.get("labor_force") or 0
    unemployed = result.get("unemployed_count") or 0
    result["unemployment_rate"] = round(unemployed / labor * 100, 1) if labor > 0 else None

    return result


def get_tract_demographics(state_fips: str, county_fips: str, tract: str) -> dict:
    """Fetch demographics for a single census tract."""
    params = _build_params(
        for_clause=f"tract:{tract}",
        in_clause=f"state:{state_fips} county:{county_fips}",
    )
    resp = requests.get(BASE_URL, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return _parse_row(data[0], data[1])


def get_clarke_county_tracts() -> list[dict]:
    """Return demographics for all census tracts in Clarke County, GA (FIPS 13059)."""
    params = _build_params(
        for_clause="tract:*",
        in_clause="state:13 county:059",
    )
    resp = requests.get(BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    headers = data[0]
    results = []
    for row in data[1:]:
        raw = dict(zip(headers, row))
        tract_data = {"tract": raw["tract"], "county": raw["county"]}
        tract_data.update(_parse_row(headers, row))
        results.append(tract_data)
    return results


def get_census_overlay_path() -> str:
    """Return path to the merged census tract GeoJSON (boundaries + demographics)."""
    return os.path.join(_DATA_DIR, "clarke_tracts.geojson")


def load_census_geojson() -> dict | None:
    """Load the pre-built census GeoJSON from disk. Returns None if not yet downloaded."""
    path = get_census_overlay_path()
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    import pprint
    pprint.pprint(get_tract_demographics("13", "059", "000100"))
