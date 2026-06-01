"""
External rent scrapers — Athens, GA.

Two sources:
  • Redfin Rentals  — median of active rental listings in Athens-Clarke County
  • HUD FMR         — HUD Fair Market Rents for Athens metro (free API token required)

Both fail gracefully (return None) on network / parse errors.
Results are cached in-memory so repeated score calls don't hammer external sites:
  Redfin Rentals — 1 hour TTL
  HUD FMR raw    — 24 hour TTL (FMRs update once per fiscal year)
"""
import json as _json
import re
import time
import logging
import urllib.request

logger = logging.getLogger(__name__)

_TIMEOUT      = 8      # seconds per HTTP request
_CACHE_TTL    = 3600   # re-scrape at most once per hour per (source, beds)
_HUD_CACHE_TTL = 86400  # HUD FMRs change once per fiscal year; cache for 24 h

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

_cache: dict = {}  # key → (timestamp, value)


def clear_cache(prefix: str = "") -> None:
    """Remove cached entries (optionally filtered by key prefix)."""
    for k in list(_cache):
        if not prefix or k.startswith(prefix):
            del _cache[k]


def _cached(key: str, fn):
    entry = _cache.get(key)
    if entry and (time.time() - entry[0]) < _CACHE_TTL:
        return entry[1]
    result = fn()
    _cache[key] = (time.time(), result)
    return result


def _hud_cached(key: str, fn):
    """Like _cached but uses the longer HUD TTL."""
    entry = _cache.get(key)
    if entry and (time.time() - entry[0]) < _HUD_CACHE_TTL:
        return entry[1]
    result = fn()
    _cache[key] = (time.time(), result)
    return result


# ── Redfin Rentals ─────────────────────────────────────────────────────────────
#
# Scrapes Redfin's county rental search page (Athens-Clarke) filtered by bedroom
# count. Extracts "$X,XXX/mo" price patterns from the served HTML.
#
# This is a real-listing source — unlike the three city-aggregate sources above,
# it reflects actual active rentals competing in the Athens market right now.
# Falls back to None if Redfin blocks the request or changes their markup.

_REDFIN_RENTALS_BASE = (
    "https://www.redfin.com/county/36057/GA/Athens-Clarke/apartments-for-rent"
)

# Wider browser-like headers to reduce bot-detection risk
_REDFIN_HEADERS = {
    **_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
}


def scrape_redfin_rentals(beds: int) -> dict | None:
    beds = max(0, min(int(beds), 5))
    return _cached(f"redfin_rentals:{beds}", lambda: _do_redfin_rentals(beds))


def _do_redfin_rentals(beds: int) -> dict | None:
    url = f"{_REDFIN_RENTALS_BASE}/filter/min-beds={beds},max-beds={beds}"
    try:
        req = urllib.request.Request(url, headers=_REDFIN_HEADERS)
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            raw = resp.read()
        # Redfin may send gzip even without explicit Accept-Encoding negotiation
        try:
            import gzip as _gzip
            html = _gzip.decompress(raw).decode("utf-8", errors="ignore")
        except Exception:
            html = raw.decode("utf-8", errors="ignore")
    except Exception as e:
        logger.debug("Redfin rentals request failed (beds=%d): %s", beds, e)
        return None

    prices = []

    # Primary: "$X,XXX/mo" text in HTML (strong rental signal)
    for m in re.finditer(r'\$\s*([\d,]+)\s*/\s*mo\b', html, re.IGNORECASE):
        try:
            v = int(m.group(1).replace(",", ""))
            if 300 <= v <= 8000:
                prices.append(v)
        except (ValueError, TypeError):
            pass

    # Secondary: JSON "price" fields in the range of monthly rents (not sale prices)
    if len(prices) < 3:
        for m in re.finditer(r'"price"\s*:\s*(\d{3,4})', html):
            v = int(m.group(1))
            if 300 <= v <= 8000:
                prices.append(v)

    if len(prices) < 3:
        logger.debug(
            "Redfin rentals: too few prices found for %dBR (got %d) — skipping",
            beds, len(prices),
        )
        return None

    prices.sort()
    n = len(prices)
    result = {
        "source":      "Redfin Rentals",
        "mid":         prices[n // 2],
        "low":         prices[n // 4],
        "high":        prices[3 * n // 4],
        "sample_size": n,
    }
    logger.debug("Redfin rentals %dBR: %d listings, mid=$%d", beds, n, result["mid"])
    return result


# ── HUD Fair Market Rents ─────────────────────────────────────────────────────
#
# HUD publishes Fair Market Rents (FMRs) annually for each metro area.
# For Athens-Clarke County MSA these are the government-defined affordability
# benchmarks by bedroom count — a useful sanity-check floor for any estimate.
#
# Requires a free API token from https://www.huduser.gov/hudapi/public/register
# Set HUD_API_TOKEN in your .env file.
#
# FMRs update once per fiscal year (October). The raw Athens record is cached
# for 24 hours so repeated per-property calls don't re-hit the API.

_HUD_FMR_URL = "https://www.huduser.gov/hudapi/public/fmr/statedata/GA"

# HUD API field names for each bedroom count
_BED_TO_HUD_KEYS: dict[int, list[str]] = {
    0: ["Efficiency", "0br", "0BR", "eff"],
    1: ["One-Bedroom",  "1br", "1BR"],
    2: ["Two-Bedroom",  "2br", "2BR"],
    3: ["Three-Bedroom","3br", "3BR"],
    4: ["Four-Bedroom", "4br", "4BR"],
}


def scrape_hud_fmr(beds: int) -> dict | None:
    beds = max(0, min(int(beds), 4))
    return _cached(f"hud_fmr:{beds}", lambda: _do_hud_fmr(beds))


def _do_hud_fmr(beds: int) -> dict | None:
    from backend.config import HUD_API_TOKEN
    if not HUD_API_TOKEN:
        logger.debug("HUD_API_TOKEN not set — skipping HUD FMR source")
        return None

    # The raw Athens record is the expensive part; cache it for 24 h
    athens = _hud_cached(
        "hud_fmr_athens_GA",
        lambda: _fetch_hud_athens_record(HUD_API_TOKEN),
    )
    if not athens:
        return None

    mid = _extract_hud_fmr_value(athens, beds)
    if mid is None:
        return None

    result = {
        "source": "HUD FMR",
        "mid":    mid,
        "low":    round(mid * 0.88),
        "high":   round(mid * 1.12),
        "method": "hud_fmr",
    }
    logger.debug("HUD FMR %dBR: $%d", beds, mid)
    return result


def _fetch_hud_athens_record(token: str) -> dict | None:
    """
    Call HUD's statedata endpoint for Georgia, locate the Athens-Clarke
    metro entry, and return the raw FMR dict (keyed by bedroom label).
    """
    req = urllib.request.Request(
        _HUD_FMR_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": _HEADERS["User-Agent"],
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = _json.loads(resp.read().decode())
    except Exception as e:
        logger.warning("HUD FMR API request failed: %s", e)
        return None

    # Search metro areas first — Athens is an MSA
    for area in data.get("data", {}).get("metroareas", []):
        name = (area.get("areaname") or "") + (area.get("metroname") or "")
        if "athens" in name.lower():
            logger.debug("HUD FMR: found Athens metro record (%s)", area.get("areaname"))
            return area

    # Fallback: check county-level entries for Clarke County
    for county in data.get("data", {}).get("counties", []):
        name = (county.get("countyname") or "") + (county.get("areaname") or "")
        if "clarke" in name.lower():
            logger.debug("HUD FMR: found Clarke County record (%s)", county.get("countyname"))
            return county

    logger.warning("HUD FMR: Athens-Clarke record not found in GA state response")
    return None


def _extract_hud_fmr_value(data: dict, beds: int) -> int | None:
    """Try multiple key name variants to extract the FMR for a given bedroom count."""
    for key in _BED_TO_HUD_KEYS.get(beds, ["Two-Bedroom"]):
        v = data.get(key)
        if isinstance(v, (int, float)) and v > 0:
            return int(v)
    return None
