"""
Traffic corridor lookup for Athens-area investment properties.

Uses GDOT Annual Average Daily Traffic (AADT) counts for major Athens
corridors, stored in backend/data/reference/athens_traffic_corridors.json.

Returns the nearest major road within a configurable radius along with
traffic context useful for:
  - Commercial conversion potential scoring
  - Demand signal for the composite investment score
  - Seller intelligence display (is this a high-visibility location?)

Usage:
    from backend.analysis.traffic_lookup import get_traffic_context
    result = get_traffic_context(33.9297, -83.4444)
    # {"road": "SR-316 / Epps Bridge Pkwy", "aadt": 47200, "road_type": "state_highway",
    #  "distance_miles": 0.02, "tier": "heavy_corridor", "demand_signal": 95}
"""
import json
import math
import os
import logging

logger = logging.getLogger(__name__)

_DATA_FILE = os.path.join(
    os.path.dirname(__file__), "..", "data", "reference", "athens_traffic_corridors.json"
)

# Tier thresholds (AADT)
TIER_HEAVY    = 30_000   # major highway / commercial spine
TIER_ARTERIAL = 15_000   # urban arterial
TIER_COLLECTOR = 8_000   # collector / neighborhood connector


def _haversine_miles(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 3958.8
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
        * math.sin(d_lng / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))


_corridors_cache: list[dict] | None = None

def _load_corridors() -> list[dict]:
    global _corridors_cache
    if _corridors_cache is not None:
        return _corridors_cache
    try:
        with open(_DATA_FILE, encoding="utf-8") as f:
            _corridors_cache = json.load(f)
        return _corridors_cache
    except Exception as e:
        logger.warning("Could not load traffic corridors: %s", e)
        return []


def _traffic_tier(aadt: int) -> str:
    if aadt >= TIER_HEAVY:
        return "heavy_corridor"
    if aadt >= TIER_ARTERIAL:
        return "urban_arterial"
    if aadt >= TIER_COLLECTOR:
        return "collector"
    return "residential"


def _demand_signal(aadt: int, distance_miles: float) -> int:
    """
    0-100 demand signal for the composite scorer.
    Decays with distance; scales with AADT tier.
    """
    if distance_miles > 0.75:
        return 0

    # Base score from AADT
    if aadt >= 40_000:
        base = 90
    elif aadt >= 25_000:
        base = 75
    elif aadt >= 15_000:
        base = 60
    elif aadt >= 8_000:
        base = 40
    else:
        base = 20

    # Linear distance decay: full score at 0mi, 0 bonus beyond 0.75mi
    decay = max(0.0, 1.0 - distance_miles / 0.75)
    return round(base * decay)


def get_traffic_context(
    lat: float,
    lng: float,
    radius_mi: float = 2.0,
) -> dict | None:
    """
    Return traffic context for the nearest major corridor within radius_mi.

    Args:
        lat, lng:    Property coordinates (WGS84)
        radius_mi:   Search radius in miles (default 0.75)

    Returns dict with keys:
        road          str   road name
        segment       str   cross-street / location description
        aadt          int   annual average daily traffic (vehicles/day)
        road_type     str   state_highway | us_highway | urban_arterial | county_arterial
        distance_miles float  haversine distance to corridor count station
        tier          str   heavy_corridor | urban_arterial | collector | residential
        demand_signal int   0-100 demand contribution for composite scorer
        note          str   qualitative context about the corridor

    Returns None if no corridor found within radius_mi.
    """
    corridors = _load_corridors()
    if not corridors:
        return None

    best = None
    best_dist = radius_mi + 1  # sentinel beyond radius

    for c in corridors:
        dist = _haversine_miles(lat, lng, c["lat"], c["lng"])
        if dist < best_dist:
            best_dist = dist
            best = c

    if best is None or best_dist > radius_mi:
        return None

    aadt = best["aadt"]
    return {
        "road":           best["road"],
        "segment":        best["segment"],
        "aadt":           aadt,
        "road_type":      best["road_type"],
        "distance_miles": round(best_dist, 2),
        "tier":           _traffic_tier(aadt),
        "demand_signal":  _demand_signal(aadt, best_dist),
        "note":           best.get("note", ""),
    }


if __name__ == "__main__":
    import pprint
    # SR-316 corridor (property #8)
    pprint.pprint(get_traffic_context(33.8998, -83.4085))
    # Five Points / near UGA
    pprint.pprint(get_traffic_context(33.9323, -83.3920))
    # Duplex in West Athens
    pprint.pprint(get_traffic_context(33.9671, -83.4457))
