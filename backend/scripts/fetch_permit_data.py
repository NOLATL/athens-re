"""
Download ACC building permit data from the Athens-Clarke County Open Data Portal
and cache it to backend/data/reference/acc_permits.json.

Source: ACC Open Data Portal (ArcGIS REST API)
  https://data-athensclarke.opendata.arcgis.com/

To find the current service URL:
  1. Go to https://data-athensclarke.opendata.arcgis.com/
  2. Search "Building Permits" or "Permits"
  3. Open the dataset → click "View Full Details" → copy the FeatureServer URL
  4. Set ACC_PERMITS_URL below or export it as ACC_PERMITS_URL env variable

The cached output is a list of permit dicts with at minimum:
    permit_number, permit_type, issued_date, address, lat, lng, status, value

Usage:
    python -m backend.scripts.fetch_permit_data
    python -m backend.scripts.fetch_permit_data --years 3   # last N years
    python -m backend.scripts.fetch_permit_data --dry-run
"""
import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── Update this URL if it changes. Find via data-athensclarke.opendata.arcgis.com ──
ACC_PERMITS_URL = os.getenv(
    "ACC_PERMITS_URL",
    # Common pattern for ACC ArcGIS services — verify dataset ID at the portal
    "https://services1.arcgis.com/c8R9E7aWITAz7Mk8/arcgis/rest/services/BuildingPermits/FeatureServer/0",
)

OUT_FILE = os.path.join(
    os.path.dirname(__file__), "..", "data", "reference", "acc_permits.json"
)


def fetch_permits(base_url: str, years_back: int = 3) -> list[dict]:
    """
    Pull permit records from ArcGIS FeatureServer.
    Returns normalized list of permit dicts.
    """
    try:
        import requests
    except ImportError:
        logger.error("requests not installed. Run: pip install requests")
        sys.exit(1)

    # Filter: permits issued in the last N years
    cutoff_ms = int(
        (datetime.now(timezone.utc).timestamp() - years_back * 365.25 * 86400) * 1000
    )

    params = {
        "where": f"ISSUED_DATE >= {cutoff_ms}",
        "outFields": "*",
        "returnGeometry": "true",
        "geometryType": "esriGeometryPoint",
        "spatialRel": "esriSpatialRelIntersects",
        "f": "json",
        "resultRecordCount": 2000,
        "orderByFields": "ISSUED_DATE DESC",
    }

    url = f"{base_url}/query"
    logger.info("Fetching permits from %s", url)

    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if "error" in data:
        raise RuntimeError(f"ArcGIS error: {data['error']}")

    features = data.get("features", [])
    logger.info("Retrieved %d permit features", len(features))

    permits = []
    for feat in features:
        attrs = feat.get("attributes") or {}
        geo = feat.get("geometry") or {}

        # Normalize field names — ACC field names may vary; adjust if needed
        permit = {
            "permit_number":  attrs.get("PERMIT_NO") or attrs.get("permit_no") or attrs.get("PERMITNUMBER", ""),
            "permit_type":    attrs.get("PERMIT_TYPE") or attrs.get("permit_type") or attrs.get("WORK_DESC", ""),
            "status":         attrs.get("STATUS") or attrs.get("status") or "",
            "address":        attrs.get("ADDRESS") or attrs.get("address") or attrs.get("SITE_ADDRESS", ""),
            "issued_date":    attrs.get("ISSUED_DATE") or attrs.get("issued_date"),
            "value":          attrs.get("TOTAL_VALUE") or attrs.get("value") or attrs.get("VALUATION") or 0,
            "lat":            geo.get("y"),
            "lng":            geo.get("x"),
        }

        # Skip records without geometry
        if permit["lat"] is None or permit["lng"] is None:
            continue

        # Convert epoch ms to ISO date string if numeric
        if isinstance(permit["issued_date"], (int, float)) and permit["issued_date"] > 0:
            permit["issued_date"] = datetime.fromtimestamp(
                permit["issued_date"] / 1000, tz=timezone.utc
            ).strftime("%Y-%m-%d")

        permits.append(permit)

    return permits


def main():
    parser = argparse.ArgumentParser(description="Fetch ACC building permit data")
    parser.add_argument("--years", type=int, default=3, help="Years of permit history (default 3)")
    parser.add_argument("--dry-run", action="store_true", help="Print sample without saving")
    args = parser.parse_args()

    try:
        permits = fetch_permits(ACC_PERMITS_URL, years_back=args.years)
    except Exception as e:
        logger.error(
            "Failed to fetch permits: %s\n\n"
            "Possible causes:\n"
            "  1. The ACC_PERMITS_URL is wrong — find the current URL at:\n"
            "     https://data-athensclarke.opendata.arcgis.com/\n"
            "  2. The ArcGIS service is temporarily unavailable\n"
            "  3. The where-clause date field name differs — inspect field names at:\n"
            "     %s?f=json\n",
            e, ACC_PERMITS_URL,
        )
        sys.exit(1)

    if not permits:
        logger.warning("No permits returned — check service URL and field names")
        sys.exit(1)

    if args.dry_run:
        print(json.dumps(permits[:3], indent=2))
        print(f"\n[dry-run] {len(permits)} permits would be saved to {OUT_FILE}")
        return

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(permits, f, indent=2)

    logger.info("Saved %d permits → %s", len(permits), OUT_FILE)
    size_kb = os.path.getsize(OUT_FILE) / 1024
    logger.info("File size: %.1f KB", size_kb)

    # Quick stats
    types = {}
    for p in permits:
        t = (p.get("permit_type") or "unknown").split()[0].upper()
        types[t] = types.get(t, 0) + 1
    top = sorted(types.items(), key=lambda x: -x[1])[:5]
    logger.info("Top permit types: %s", top)


if __name__ == "__main__":
    main()
