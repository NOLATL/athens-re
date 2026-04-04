"""
Permit activity analysis for Athens-area investment properties.

Analyzes building permit density and type within a radius of a subject
property. Permit activity is a leading indicator of:
  - Neighborhood reinvestment (rising values)
  - Owner-occupant vs. investor activity ratio
  - Infrastructure upgrades (electrical, plumbing, HVAC permits)

Requires acc_permits.json to be downloaded first:
    python -m backend.scripts.fetch_permit_data

Falls back gracefully when data is unavailable.
"""
import json
import math
import os
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_DATA_FILE = os.path.join(
    os.path.dirname(__file__), "..", "data", "reference", "acc_permits.json"
)

# Permit categories for display
_RENOVATION_KEYWORDS = ("remodel", "renovation", "addition", "alteration", "repair", "rehab")
_NEW_CONSTRUCTION_KEYWORDS = ("new", "construction", "build")
_ELECTRICAL_KEYWORDS = ("electrical", "electric", "wiring")
_PLUMBING_KEYWORDS = ("plumbing", "plumb", "hvac", "mechanical")
_DEMO_KEYWORDS = ("demolition", "demo")


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


def _categorize(permit_type: str) -> str:
    pt = (permit_type or "").lower()
    if any(k in pt for k in _DEMO_KEYWORDS):
        return "demolition"
    if any(k in pt for k in _NEW_CONSTRUCTION_KEYWORDS):
        return "new_construction"
    if any(k in pt for k in _RENOVATION_KEYWORDS):
        return "renovation"
    if any(k in pt for k in _ELECTRICAL_KEYWORDS):
        return "electrical"
    if any(k in pt for k in _PLUMBING_KEYWORDS):
        return "plumbing_hvac"
    return "other"


def _load_permits() -> list[dict]:
    if not os.path.exists(_DATA_FILE):
        return []
    try:
        with open(_DATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Could not load permit data: %s", e)
        return []


def get_permit_activity(
    lat: float,
    lng: float,
    radius_mi: float = 0.5,
    years_back: int = 3,
) -> dict:
    """
    Summarize building permit activity within radius_mi of (lat, lng).

    Args:
        lat, lng:    Property coordinates
        radius_mi:   Search radius in miles (default 0.5)
        years_back:  How many years of permit history to include (default 3)

    Returns dict with:
        total           int   total permits in area
        new_construction int  new construction permits
        renovation      int   remodel / addition / alteration permits
        electrical      int   electrical permits
        plumbing_hvac   int   plumbing / HVAC permits
        demolition      int   demolition permits
        other           int   other permit types
        total_value     int   sum of permit valuations ($)
        radius_mi       float search radius used
        years_back      int   years of history included
        trend           str   "active" | "moderate" | "quiet"
        data_available  bool  False if acc_permits.json not yet downloaded
    """
    permits = _load_permits()
    if not permits:
        return {
            "total": 0,
            "new_construction": 0,
            "renovation": 0,
            "electrical": 0,
            "plumbing_hvac": 0,
            "demolition": 0,
            "other": 0,
            "total_value": 0,
            "radius_mi": radius_mi,
            "years_back": years_back,
            "trend": "unknown",
            "data_available": False,
        }

    cutoff_year = datetime.now(timezone.utc).year - years_back
    counts = {k: 0 for k in ("new_construction", "renovation", "electrical", "plumbing_hvac", "demolition", "other")}
    total_value = 0

    for p in permits:
        plat = p.get("lat")
        plng = p.get("lng")
        if plat is None or plng is None:
            continue
        if _haversine_miles(lat, lng, float(plat), float(plng)) > radius_mi:
            continue

        # Date filter
        issued = p.get("issued_date", "")
        if issued:
            try:
                yr = int(str(issued)[:4])
                if yr < cutoff_year:
                    continue
            except (ValueError, TypeError):
                pass

        cat = _categorize(p.get("permit_type", ""))
        counts[cat] = counts.get(cat, 0) + 1

        try:
            total_value += float(p.get("value") or 0)
        except (TypeError, ValueError):
            pass

    total = sum(counts.values())

    # Trend classification: per-year annualized rate
    annual_rate = total / max(years_back, 1)
    if annual_rate >= 10:
        trend = "active"
    elif annual_rate >= 4:
        trend = "moderate"
    else:
        trend = "quiet"

    return {
        "total": total,
        **counts,
        "total_value": int(total_value),
        "radius_mi": radius_mi,
        "years_back": years_back,
        "trend": trend,
        "data_available": True,
    }


if __name__ == "__main__":
    import pprint
    # Near UGA campus area
    pprint.pprint(get_permit_activity(33.945, -83.38, radius_mi=0.5))
