"""FEMA flood zone lookup for a lat/lng point."""
import os
from backend.config import SHAPEFILES

FLOOD_INSURANCE_COST = {"AE": 2000, "A": 1800, "AO": 1500, "VE": 3000}  # annual est.


def get_flood_zone(lat: float, lng: float) -> dict:
    gdf_path = SHAPEFILES.get("fema_flood")
    result = {"flood_zone": "X", "requires_insurance": False, "annual_insurance_est": 0, "flag": None}

    if not gdf_path or not os.path.exists(gdf_path):
        return result  # shapefiles not yet downloaded

    try:
        import geopandas as gpd
        from shapely.geometry import Point
    except ImportError:
        return result  # geopandas not available in this environment

    for f in os.listdir(gdf_path):
        if not f.endswith(".shp"):
            continue
        gdf = gpd.read_file(os.path.join(gdf_path, f))
        if gdf.crs and gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(epsg=4326)
        point = Point(lng, lat)
        match = gdf[gdf.geometry.contains(point)]
        if not match.empty:
            zone = match.iloc[0].get("FLD_ZONE", "X")
            result["flood_zone"] = zone
            if zone in FLOOD_INSURANCE_COST:
                result["requires_insurance"] = True
                result["annual_insurance_est"] = FLOOD_INSURANCE_COST[zone]
                result["flag"] = f"Zone {zone} — flood insurance required (~${FLOOD_INSURANCE_COST[zone]:,}/yr)"
        break

    return result
