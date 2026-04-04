"""
Rent estimator for Athens-area investment properties.

Uses ACS census tract median rents as the neighborhood baseline,
adjusted by bedroom count, UGA proximity, and county.

No external API calls required — uses the census GeoJSON already downloaded by
backend/scripts/download_census_data.py.  Falls back to Athens market-wide
averages (RentCafe/Zillow/RentHop, Mar 2026) when census data is unavailable.

Usage:
    from backend.analysis.rent_estimator import estimate_rent
    result = estimate_rent(33.945, -83.38, beds=3, county="clarke")
    # {"low": 1700, "mid": 1930, "high": 2160, "method": "census_tract", "per_unit": False}
"""
import math
import logging

logger = logging.getLogger(__name__)

# ── Athens 2026 market baseline rents ────────────────────────────────────────
# Source: RentCafe, Zillow, Rent.com, RentHop — Mar 2026
# Whole-unit unfurnished; keyed by bedroom count (0 = studio)
ATHENS_BASE_RENTS = {
    0: 1067,
    1: 1185,
    2: 1400,
    3: 1837,
    4: 2400,
    5: 2800,
}

# Per-unit rents for multifamily (per individual unit, not whole building)
ATHENS_BASE_RENTS_PER_UNIT = {
    1: 950,
    2: 1100,
    3: 1300,
    4: 1450,
}

# Athens market 2BR median (baseline denominator for census tract ratio)
_ATHENS_2BR_MEDIAN = 1400

# UGA campus coordinates
_UGA = (33.9480, -83.3774)

# Oconee County school-district premium
_OCONEE_PREMIUM = 0.08


# ── Helpers ───────────────────────────────────────────────────────────────────

def _haversine_miles(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 3958.8
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lng / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))


def _uga_premium(lat: float, lng: float) -> float:
    """Return UGA proximity rent premium fraction (0.0–0.15)."""
    dist = _haversine_miles(lat, lng, _UGA[0], _UGA[1])
    if dist <= 0.5:
        return 0.15
    if dist <= 1.0:
        return 0.08
    return 0.0


def _is_multifamily(property_type: str) -> bool:
    pt = (property_type or "").lower()
    return any(k in pt for k in ("multi", "duplex", "triplex", "quadplex", "5+", "apartment"))


def _estimate_unit_count(property_type: str, beds: int) -> int:
    """
    Estimate number of units in a multifamily property from its type string and
    total bedroom count.  Used to derive beds-per-unit for rent estimation.
    """
    pt = (property_type or "").lower()
    if "duplex" in pt:
        return 2
    if "triplex" in pt:
        return 3
    if "quadplex" in pt:
        return 4
    if "5+" in pt:
        return max(5, beds // 2)
    # "Multi-Family (2-4 Unit)" — infer from beds
    if beds <= 3:
        return 2
    if beds <= 5:
        return 2
    if beds <= 8:
        return min(4, max(2, beds // 2))
    return max(4, beds // 3)


def _get_tract_median_rent(lat: float, lng: float):
    """
    Return ACS median_gross_rent for the census tract containing (lat, lng),
    or None if census data is unavailable or the point is outside Clarke County.
    """
    try:
        from backend.gis.census_demographics import load_census_geojson
        from shapely.geometry import Point, shape

        data = load_census_geojson()
        if not data:
            return None

        pt = Point(lng, lat)   # GeoJSON coordinates are (lng, lat)
        for feat in data.get("features", []):
            geom = feat.get("geometry")
            if not geom:
                continue
            try:
                if shape(geom).contains(pt):
                    return feat.get("properties", {}).get("median_gross_rent")
            except Exception:
                continue
    except Exception as e:
        logger.debug("Tract rent lookup failed: %s", e)

    return None


# ── Public API ────────────────────────────────────────────────────────────────

def estimate_rent(
    lat: float,
    lng: float,
    beds: int,
    sqft: int = 0,
    property_type: str = "",
    county: str = "clarke",
) -> dict:
    """
    Estimate monthly rent for a property.

    Algorithm:
    1. Start from Athens market-average base rent for the bedroom count.
    2. If census tract data is available for the location, scale the base rent
       by the tract's median_gross_rent relative to the Athens 2BR median.
       (Ratio clamped to ±35% to avoid outlier tracts dominating the estimate.)
    3. Apply UGA proximity premium for Clarke County properties.
    4. Apply Oconee County school-district premium.
    5. Output a ±12% range around the point estimate.

    Args:
        lat, lng:       Property coordinates (WGS84)
        beds:           Bedroom count (0 = studio)
        sqft:           Square footage (unused currently, reserved for future sqft model)
        property_type:  String from Redfin CSV (e.g. "Multi-Family (2-4 Unit)")
        county:         "clarke" | "oconee"

    Returns:
        {
            "low":      int,   conservative estimate
            "mid":      int,   base point estimate
            "high":     int,   optimistic estimate
            "method":   str,   "census_tract" | "market_avg"
            "per_unit": bool,  True = estimate is per unit (multifamily)
        }
    """
    beds = max(0, int(beds or 0))
    per_unit = _is_multifamily(property_type)

    # Step 1 — Athens market average for this bedroom count
    if per_unit:
        unit_count = _estimate_unit_count(property_type, beds)
        beds_per_unit = max(1, round(beds / unit_count))
        market_base = ATHENS_BASE_RENTS_PER_UNIT.get(min(beds_per_unit, 4), 1000)
    else:
        market_base = ATHENS_BASE_RENTS.get(min(beds, 5), 1400)

    # Step 2 — Neighborhood adjustment via census tract median rent
    tract_rent = _get_tract_median_rent(lat, lng)
    method = "market_avg"

    if tract_rent and tract_rent > 500:
        ratio = tract_rent / _ATHENS_2BR_MEDIAN
        ratio = max(0.65, min(1.35, ratio))          # clamp to ±35%
        base_rent = round(market_base * ratio)
        method = "census_tract"
    else:
        base_rent = market_base

    # Step 3 — UGA proximity premium (Clarke County only)
    if county == "clarke":
        uga_pct = _uga_premium(lat, lng)
        if uga_pct:
            base_rent = round(base_rent * (1 + uga_pct))

    # Step 4 — Oconee school district premium
    if county == "oconee":
        base_rent = round(base_rent * (1 + _OCONEE_PREMIUM))

    # Step 5 — Output range ±12%
    return {
        "low":      round(base_rent * 0.88),
        "mid":      base_rent,
        "high":     round(base_rent * 1.12),
        "method":   method,
        "per_unit": per_unit,
    }


def aggregate_rent_estimates(
    lat: float,
    lng: float,
    beds: int,
    sqft: int = 0,
    property_type: str = "",
    county: str = "clarke",
    address: str = "",
) -> dict:
    """
    Aggregate rent estimates from the internal model and external scrapers.

    Runs all sources in parallel (scrapers share a 10 s timeout budget).
    Averages the mid values of all sources that return a result.

    Returns:
        {
            "mid":      int,        averaged across all valid sources
            "low":      int,        ±12% around averaged mid
            "high":     int,
            "method":   str,        "aggregated" | "internal_only"
            "per_unit": bool,
            "sources":  list[dict]  each: {source, mid, low, high, sample_size?, method?}
        }
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from backend.scrapers.rent_sources import (
        scrape_craigslist, scrape_zumper, scrape_rentcafe,
    )

    # Internal calc is always available
    internal = estimate_rent(lat, lng, beds, sqft, property_type, county)
    internal_source = {
        "source": "Internal model",
        "mid":    internal["mid"],
        "low":    internal["low"],
        "high":   internal["high"],
        "method": internal["method"],
    }

    beds_int = max(0, int(beds or 0))
    scraper_tasks = [
        lambda b=beds_int: scrape_craigslist(b),
        lambda b=beds_int: scrape_zumper(b),
        lambda b=beds_int: scrape_rentcafe(b),
    ]

    external: list[dict] = []
    try:
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(fn) for fn in scraper_tasks]
            for f in as_completed(futures, timeout=10):
                try:
                    result = f.result()
                    if result:
                        external.append(result)
                except Exception as e:
                    logger.debug("Rent scraper error: %s", e)
    except Exception as e:
        logger.debug("Rent scraper pool error: %s", e)

    all_sources = [internal_source] + external
    mids = [s["mid"] for s in all_sources if s.get("mid")]

    if len(mids) <= 1:
        return {**internal, "sources": all_sources, "method": "internal_only"}

    avg_mid = round(sum(mids) / len(mids))
    return {
        "mid":      avg_mid,
        "low":      min(mids),   # actual spread across sources
        "high":     max(mids),
        "method":   "aggregated",
        "per_unit": internal["per_unit"],
        "sources":  all_sources,
    }


if __name__ == "__main__":
    import pprint
    # Example: 3BR near UGA
    pprint.pprint(estimate_rent(33.945, -83.38, beds=3, county="clarke"))
    # Example: 2BR duplex, West Athens
    pprint.pprint(estimate_rent(33.965, -83.44, beds=2, property_type="Multi-Family (2-4 Unit)", county="clarke"))
    # Example: Oconee
    pprint.pprint(estimate_rent(33.90, -83.47, beds=3, county="oconee"))
