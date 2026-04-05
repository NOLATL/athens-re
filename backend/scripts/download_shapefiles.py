"""
Download ACC zoning and parcel data from the Athens-Clarke County GIS server
into backend/data/shapefiles/ as GeoJSON files.

Sources (ACC enigma GIS server — CC BY 4.0, updated nightly):
  Zoning:  https://enigma.accgov.com/server/rest/services/Parcel_Zoning_Types/FeatureServer/0
  Parcels: https://enigma.accgov.com/server/rest/services/ACC_Parcels/FeatureServer/0

Usage:
  python -m backend.scripts.download_shapefiles
  python -m backend.scripts.download_shapefiles --layers zoning parcels
  python -m backend.scripts.download_shapefiles --layers zoning  (skip parcels)
"""
import argparse
import json
import logging
import os
import sys
import time

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── Layer registry ────────────────────────────────────────────────────────────
LAYERS = {
    "zoning": {
        "url": "https://enigma.accgov.com/server/rest/services/Parcel_Zoning_Types/FeatureServer/0/query",
        "out_file": "acc_zoning/acc_zoning.geojson",
        "fields": "PARCEL_NO,CurrentZn,CombinedZn,RGProperty,SplitZoned,PIN,Acres",
        "description": "ACC parcel zoning types",
    },
    "parcels": {
        "url": "https://enigma.accgov.com/server/rest/services/ACC_Parcels/FeatureServer/0/query",
        "out_file": "acc_parcels/acc_parcels.geojson",
        "fields": "PARCEL_NO,PAR_ADD,OWNER_NAME,OWNER_ADD,ACRES,REALKEY,LEGAL_DESC,FTR_CODE",
        "description": "ACC full parcel dataset",
    },
}

DATA_DIR = os.path.join(
    os.getenv("GIS_DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "data")),
    "shapefiles",
)
PAGE_SIZE = 2000
RETRY_DELAY = 3


# ── paginated downloader ──────────────────────────────────────────────────────

def fetch_all_features(url: str, fields: str) -> list[dict]:
    """
    Download all features from an ArcGIS FeatureServer layer using
    resultOffset pagination (2000 records per page).
    """
    features = []
    offset = 0
    session = requests.Session()
    session.headers.update({"User-Agent": "AthensREPlatform/1.0 (+github.com)"})

    while True:
        params = {
            "where": "1=1",
            "outFields": fields,
            "geometryPrecision": 6,
            "outSR": "4326",           # WGS84 lat/lng
            "f": "geojson",
            "resultOffset": offset,
            "resultRecordCount": PAGE_SIZE,
        }

        for attempt in range(3):
            try:
                r = session.get(url, params=params, timeout=60)
                r.raise_for_status()
                data = r.json()
                break
            except (requests.RequestException, ValueError) as e:
                logger.warning("Page offset=%d attempt %d failed: %s", offset, attempt + 1, e)
                if attempt == 2:
                    raise
                time.sleep(RETRY_DELAY)

        page_features = data.get("features", [])
        features.extend(page_features)

        logger.info("  offset=%d fetched=%d total_so_far=%d", offset, len(page_features), len(features))

        # Stop if fewer records returned than page size (last page)
        if len(page_features) < PAGE_SIZE:
            break

        offset += PAGE_SIZE
        time.sleep(0.5)   # polite delay between pages

    return features


def download_layer(name: str, cfg: dict) -> str:
    """Download a single layer and write to GeoJSON. Returns the output path."""
    out_path = os.path.join(DATA_DIR, cfg["out_file"])
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    logger.info("Downloading %s (%s)...", name, cfg["description"])
    features = fetch_all_features(cfg["url"], cfg["fields"])
    logger.info("Downloaded %d features for %s", len(features), name)

    geojson = {
        "type": "FeatureCollection",
        "name": name,
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": features,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(geojson, f, separators=(",", ":"))   # compact — no pretty print

    size_mb = os.path.getsize(out_path) / 1_048_576
    logger.info("Saved %s → %s (%.1f MB)", name, out_path, size_mb)
    return out_path


# ── simplified zoning for map overlay ────────────────────────────────────────

def build_simplified_zoning(full_path: str) -> str:
    """
    Read the full zoning GeoJSON, dissolve by zone type, simplify geometry,
    and write a lightweight version for the map overlay API.

    The simplified file lives alongside the full file as acc_zoning_simplified.geojson.
    Requires geopandas + shapely.
    """
    try:
        import geopandas as gpd
    except ImportError:
        logger.warning("geopandas not available — skipping simplified overlay build")
        return ""

    logger.info("Building simplified zoning overlay...")
    gdf = gpd.read_file(full_path)

    # Use CurrentZn as the zone column; fall back to CombinedZn
    zone_col = "CurrentZn" if "CurrentZn" in gdf.columns else "CombinedZn"
    if zone_col not in gdf.columns:
        logger.warning("No zone column found in zoning data — skipping simplification")
        return ""

    # Drop rows with no geometry or no zone
    gdf = gdf[gdf.geometry.notna() & gdf[zone_col].notna()].copy()

    # Simplify individual polygon geometry (tolerance in degrees ~= 5m)
    gdf["geometry"] = gdf.geometry.simplify(0.00005, preserve_topology=True)

    # Keep only parcel_no + zone fields for the overlay (drop owner data)
    keep = [c for c in ["PARCEL_NO", zone_col, "CombinedZn", "Acres"] if c in gdf.columns]
    gdf = gdf[keep + ["geometry"]]

    out_path = full_path.replace(".geojson", "_simplified.geojson")
    gdf.to_file(out_path, driver="GeoJSON")

    size_mb = os.path.getsize(out_path) / 1_048_576
    logger.info("Simplified zoning overlay → %s (%.1f MB)", out_path, size_mb)
    return out_path


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Download ACC GIS shapefiles")
    parser.add_argument(
        "--layers", nargs="+", default=list(LAYERS.keys()),
        choices=list(LAYERS.keys()),
        help="Which layers to download (default: all)",
    )
    parser.add_argument(
        "--skip-simplify", action="store_true",
        help="Skip building the simplified zoning overlay",
    )
    args = parser.parse_args()

    for name in args.layers:
        cfg = LAYERS[name]
        out_path = download_layer(name, cfg)

        if name == "zoning" and not args.skip_simplify:
            build_simplified_zoning(out_path)

    logger.info("All downloads complete.")


if __name__ == "__main__":
    main()
