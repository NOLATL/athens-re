"""
Zoning lookup for a lat/lng point using ACC GeoJSON data.

Data source: enigma.accgov.com ACC GIS server (downloaded by
backend/scripts/download_shapefiles.py into backend/data/shapefiles/).

Layers used:
  acc_zoning/acc_zoning.geojson   — zoning + lot size per parcel
  acc_parcels/acc_parcels.geojson — parcel address + owner info

Both GeoDataFrames are loaded once and cached at module level
(with a spatial index built on first load) so repeated lookups are fast.
"""
import logging
import os

import geopandas as gpd
from shapely.geometry import Point

from backend.config import SHAPEFILES

logger = logging.getLogger(__name__)

# ── module-level cache ────────────────────────────────────────────────────────
_zoning_gdf: gpd.GeoDataFrame | None = None
_parcels_gdf: gpd.GeoDataFrame | None = None
_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "shapefiles")


def _load_zoning() -> gpd.GeoDataFrame | None:
    global _zoning_gdf
    if _zoning_gdf is not None:
        return _zoning_gdf

    path = os.path.join(_DATA_DIR, "acc_zoning", "acc_zoning.geojson")
    if not os.path.exists(path):
        logger.warning("Zoning GeoJSON not found at %s — run download_shapefiles.py", path)
        return None

    logger.info("Loading zoning layer from %s...", path)
    gdf = gpd.read_file(path)
    if gdf.crs is None or gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)
    gdf = gdf[gdf.geometry.notna()]
    _zoning_gdf = gdf
    logger.info("Zoning layer loaded: %d parcels", len(gdf))
    return _zoning_gdf


def _load_parcels() -> gpd.GeoDataFrame | None:
    global _parcels_gdf
    if _parcels_gdf is not None:
        return _parcels_gdf

    path = os.path.join(_DATA_DIR, "acc_parcels", "acc_parcels.geojson")
    if not os.path.exists(path):
        logger.warning("Parcels GeoJSON not found at %s — run download_shapefiles.py", path)
        return None

    logger.info("Loading parcels layer from %s...", path)
    gdf = gpd.read_file(path)
    # Index by PARCEL_NO for fast joins
    if "PARCEL_NO" in gdf.columns:
        gdf = gdf.set_index("PARCEL_NO")
    _parcels_gdf = gdf
    logger.info("Parcels layer loaded: %d parcels", len(gdf))
    return _parcels_gdf


# ── public API ────────────────────────────────────────────────────────────────

def get_zoning(lat: float, lng: float) -> dict:
    """
    Return zoning and parcel info for a coordinate.

    Args:
        lat: latitude (WGS84)
        lng: longitude (WGS84)

    Returns dict with:
        parcel_id       str     ACC parcel number (PARCEL_NO)
        zoning_code     str     current zoning designation (e.g. "RS-15", "MU-B")
        combined_zoning str     combined zoning (handles split-zoned parcels)
        lot_size_acres  float   parcel acreage
        address         str     parcel situs address (from parcels layer)
        owner_name      str     owner name
        owner_address   str     owner mailing address
        county          str     "clarke" | "oconee"
        absentee_owner  bool    owner mailing addr != situs addr

    Returns empty dict if shapefiles are not yet downloaded.
    """
    zoning_gdf = _load_zoning()
    if zoning_gdf is None:
        return {}

    point = Point(lng, lat)   # Shapely uses (x=lon, y=lat)

    # Point-in-polygon using spatial index (sindex built automatically by geopandas)
    candidates = list(zoning_gdf.sindex.intersection(point.bounds))
    if not candidates:
        return {}

    match = zoning_gdf.iloc[candidates]
    match = match[match.geometry.contains(point)]
    if match.empty:
        return {}

    row = match.iloc[0]
    parcel_id = str(row.get("PARCEL_NO", "")).strip()

    result = {
        "parcel_id": parcel_id,
        "zoning_code": str(row.get("CurrentZn", "")).strip() or None,
        "combined_zoning": str(row.get("CombinedZn", "")).strip() or None,
        "lot_size_acres": float(row["Acres"]) if row.get("Acres") else None,
        "address": None,
        "owner_name": None,
        "owner_address": None,
        "county": "clarke",
        "absentee_owner": False,
    }

    # Enrich with parcel address + owner from parcels layer
    parcels_gdf = _load_parcels()
    if parcels_gdf is not None and parcel_id in parcels_gdf.index:
        prow = parcels_gdf.loc[parcel_id]
        situs = str(prow.get("PAR_ADD", "")).strip()
        owner_addr = str(prow.get("OWNER_ADD", "")).strip()
        result["address"] = situs or None
        result["owner_name"] = str(prow.get("OWNER_NAME", "")).strip() or None
        result["owner_address"] = owner_addr or None
        result["absentee_owner"] = bool(
            situs and owner_addr and situs.lower() != owner_addr.lower()
        )

    return result


def get_zoning_overlay_path() -> str:
    """Return path to the simplified zoning GeoJSON for map overlay serving."""
    simplified = os.path.join(_DATA_DIR, "acc_zoning", "acc_zoning_simplified.geojson")
    full = os.path.join(_DATA_DIR, "acc_zoning", "acc_zoning.geojson")
    return simplified if os.path.exists(simplified) else full


if __name__ == "__main__":
    # Quick smoke test — downtown Athens, should be MU or commercial
    test_points = [
        ("Downtown Athens", 33.9601, -83.3774),
        ("UGA campus", 33.9480, -83.3774),
        ("Broad St commercial", 33.9596, -83.3750),
    ]
    for label, lat, lng in test_points:
        r = get_zoning(lat, lng)
        print(f"{label}: {r.get('zoning_code')} | {r.get('lot_size_acres')} ac | {r.get('address')}")
