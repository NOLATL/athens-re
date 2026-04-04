"""Weighted proximity scoring for a property coordinate."""
import math
from backend.config import LOCATIONS

# (location_key, weight, max_score_miles)
TARGETS = [
    ("uga_campus",          3.0, 2.0),
    ("sanford_stadium",     1.0, 1.5),
    ("akins_ford_arena",    1.5, 2.0),
    ("downtown_athens",     2.0, 2.0),
    ("epps_bridge",         0.5, 3.0),
    ("uga_health_sciences", 1.5, 2.0),
]


def haversine_miles(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 3958.8  # Earth radius in miles
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def score_proximity(lat: float, lng: float) -> dict:
    """
    Returns a 0-100 proximity score and per-target distances.
    Higher = closer to more value drivers.
    """
    total_weight = sum(w for _, w, _ in TARGETS)
    weighted_score = 0.0
    distances = {}

    for key, weight, max_miles in TARGETS:
        target_lat, target_lng = LOCATIONS[key]
        dist = haversine_miles(lat, lng, target_lat, target_lng)
        distances[key] = round(dist, 2)
        # Linear decay: 1.0 at 0 miles, 0.0 at max_miles
        proximity = max(0.0, 1.0 - dist / max_miles)
        weighted_score += proximity * weight

    normalized = (weighted_score / total_weight) * 100
    return {"proximity_score": round(normalized, 1), "distances_miles": distances}


if __name__ == "__main__":
    import pprint
    # Test: Park Ridge Ct duplex
    pprint.pprint(score_proximity(33.934262, -83.340972))
