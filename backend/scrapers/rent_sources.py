"""
External rent scrapers — Athens, GA.

Three city-level sources:
  • Craigslist Athens  — median of recent /apa listings by bedroom count
  • Zumper             — market median from rent-research page
  • RentCafe           — average rent from market-trends page

All scrapers fail gracefully (return None) on network / parse errors.
Results are cached in-memory for CACHE_TTL seconds so repeated score
calls for the same bedroom count don't hammer external sites.
"""
import re, time, logging
import urllib.request, urllib.parse, urllib.error

logger = logging.getLogger(__name__)

_TIMEOUT   = 8      # seconds per HTTP request
_CACHE_TTL = 3600   # re-scrape at most once per hour per (source, beds)

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


def _get(url: str) -> str | None:
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        logger.debug("HTTP GET %s failed: %s", url, e)
        return None


# ── Craigslist Athens ─────────────────────────────────────────────────────────

def scrape_craigslist(beds: int) -> dict | None:
    """
    Search Athens Craigslist /apa for the given bedroom count.
    Returns median asking rent from recent listings.
    """
    beds = max(0, int(beds))
    return _cached(f"craigslist:{beds}", lambda: _do_craigslist(beds))


def _do_craigslist(beds: int) -> dict | None:
    url = (
        f"https://athens.craigslist.org/search/apa"
        f"?min_bedrooms={beds}&max_bedrooms={beds}&sort=date"
    )
    html = _get(url)
    if not html:
        return None

    prices = []
    # Pattern 1: <span class="priceinfo">$1,450</span>
    for m in re.finditer(r'class="priceinfo[^"]*"[^>]*>[\s]*\$\s*([\d,]+)', html):
        v = int(m.group(1).replace(",", ""))
        if 300 <= v <= 8000:
            prices.append(v)
    # Pattern 2: data-price="XXXX"
    if not prices:
        for m in re.finditer(r'data-price="(\d+)"', html):
            v = int(m.group(1))
            if 300 <= v <= 8000:
                prices.append(v)
    # Pattern 3: >$X,XXX< anywhere (broader fallback)
    if not prices:
        for m in re.finditer(r'>\s*\$([\d,]{3,6})\s*<', html):
            v = int(m.group(1).replace(",", ""))
            if 300 <= v <= 8000:
                prices.append(v)

    if len(prices) < 3:
        return None

    prices.sort()
    n   = len(prices)
    mid  = prices[n // 2]
    low  = prices[n // 4]
    high = prices[3 * n // 4]

    return {
        "source":      "Craigslist",
        "mid":         mid,
        "low":         low,
        "high":        high,
        "sample_size": n,
    }


# ── Zumper ────────────────────────────────────────────────────────────────────

_ZUMPER_SLUG = {
    0: "studios",
    1: "one-bedrooms",
    2: "two-bedrooms",
    3: "three-bedrooms",
    4: "four-bedrooms",
}


def scrape_zumper(beds: int) -> dict | None:
    beds = max(0, min(int(beds), 4))
    return _cached(f"zumper:{beds}", lambda: _do_zumper(beds))


# Reasonable rent ranges by bedroom count for sanity-checking Zumper output
_ZUMPER_RENT_BOUNDS = {
    0: (600,  2200),
    1: (700,  2800),
    2: (900,  3500),
    3: (1100, 5000),
    4: (1300, 7000),
}


def _zumper_plausible(mid: int, beds: int) -> bool:
    lo, hi = _ZUMPER_RENT_BOUNDS.get(beds, (400, 8000))
    return lo <= mid <= hi


_ZUMPER_BED_KEY = {
    0: "STUDIO",
    1: "1_BED",
    2: "2_BED",
    3: "3_BED",
    4: "4_BED",
}


def _do_zumper(beds: int) -> dict | None:
    import json as _json

    slug    = _ZUMPER_SLUG.get(beds, "two-bedrooms")
    bed_key = _ZUMPER_BED_KEY.get(beds, "2_BED")
    url     = f"https://www.zumper.com/rent-research/athens-ga/{slug}"
    html    = _get(url)
    if not html:
        return None

    # Zumper embeds all data in window.__PRELOADED_STATE__
    # Structure: rentResearchHomepage.rentalData.cities[0]
    #            .bed_property_type.{N_BED}.AFR.median_rent
    m_state = re.search(
        r'window\.__PRELOADED_STATE__\s*=\s*(\{.*?\});\s*(?:window|</script>)',
        html, re.DOTALL,
    )
    if not m_state:
        # Broader fallback: grab everything after the assignment
        m_state = re.search(
            r'window\.__PRELOADED_STATE__\s*=\s*(\{.+)',
            html, re.DOTALL,
        )

    if m_state:
        raw = m_state.group(1).rstrip("; \n\r")
        # The blob may be truncated; try progressively shorter slices
        for end in (len(raw), 500_000, 200_000, 100_000):
            try:
                state = _json.loads(raw[:end])
                cities = (
                    state
                    .get("rentResearchHomepage", {})
                    .get("rentalData", {})
                    .get("cities", [])
                )
                # Find Athens (or just use the first city on an Athens-scoped page)
                city = next(
                    (c for c in cities if "athens" in str(c.get("city", "")).lower()),
                    cities[0] if cities else None,
                )
                if city:
                    val = (
                        city
                        .get("bed_property_type", {})
                        .get(bed_key, {})
                        .get("AFR", {})
                        .get("median_rent")
                    )
                    if isinstance(val, (int, float)):
                        mid = round(val)
                        if _zumper_plausible(mid, beds):
                            return {
                                "source":      "Zumper",
                                "mid":         mid,
                                "low":         round(mid * 0.88),
                                "high":        round(mid * 1.12),
                                "sample_size": None,
                            }
                break  # parsed OK but path not found — no point retrying
            except (_json.JSONDecodeError, Exception) as e:
                logger.debug("Zumper __PRELOADED_STATE__ parse (len=%d): %s", end, e)
                continue

    return None


# ── RentCafe ──────────────────────────────────────────────────────────────────

_RENTCAFE_LABELS = {
    0: ["studio", "Studio"],
    1: ["1 Bedroom", "1-bedroom", "1BR", "One Bedroom"],
    2: ["2 Bedroom", "2-bedroom", "2BR", "Two Bedroom"],
    3: ["3 Bedroom", "3-bedroom", "3BR", "Three Bedroom"],
    4: ["4 Bedroom", "4-bedroom", "4BR", "Four Bedroom"],
}


def scrape_rentcafe(beds: int) -> dict | None:
    beds = max(0, min(int(beds), 4))
    return _cached(f"rentcafe:{beds}", lambda: _do_rentcafe(beds))


def _do_rentcafe(beds: int) -> dict | None:
    url  = "https://www.rentcafe.com/average-rent-market-trends/us/ga/athens/"
    html = _get(url)
    if not html:
        return None

    for label in _RENTCAFE_LABELS.get(beds, ["2 Bedroom", "2BR"]):
        pat = re.escape(label) + r"[^$\d]{0,60}\$\s*([\d,]+)"
        m   = re.search(pat, html, re.IGNORECASE)
        if m:
            mid = int(m.group(1).replace(",", ""))
            if 300 <= mid <= 8000:
                return {
                    "source":      "RentCafe",
                    "mid":         mid,
                    "low":         round(mid * 0.88),
                    "high":        round(mid * 1.12),
                    "sample_size": None,
                }

    # Fallback: generic averageRent JSON field
    m = re.search(r'"averageRent"\s*:\s*(\d+)', html)
    if m:
        mid = int(m.group(1))
        if 300 <= mid <= 8000:
            return {
                "source":      "RentCafe",
                "mid":         mid,
                "low":         round(mid * 0.88),
                "high":        round(mid * 1.12),
                "sample_size": None,
            }

    return None
