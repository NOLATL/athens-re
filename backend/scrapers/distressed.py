"""
Distressed property data collection pipeline for Clarke and Oconee counties.

Sources:
  1. qPublic (Schneider Corp) — ACC parcel records, tax delinquency, owner address
  2. ACC Tax Commissioner tax sale list (accgov.com/1703)
  3. GSCCCA.org — state fi fa liens and lis pendens by county
  4. ACC Open Data Portal — code enforcement cases (if available without FOIA)

Note on scraping:
  qPublic and GSCCCA are public-facing portals without a formal API.
  Requests use standard HTTP + BeautifulSoup HTML parsing. If a site adds
  bot protection, switch to Selenium or Playwright.

Usage:
  from backend.scrapers.distressed import fetch_tax_delinquents, fetch_fi_fa_liens
  parcels = fetch_tax_delinquents("clarke")
"""
import json as _json
import logging
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from typing import Optional

import requests
from bs4 import BeautifulSoup

from backend.config import (
    QPUBLIC_CLARKE_URL,
    GSCCCA_BASE_URL,
    ACC_TAX_SALE_URL,
)
from backend.analysis.distress_scorer import enrich_parcel

logger = logging.getLogger(__name__)


class ScraperError(Exception):
    """A source failed to FETCH (network/403/500), as distinct from fetching
    successfully and finding no distressed parcels. The pipeline collects these
    so the nightly batch can report a real error count instead of `errors=0`
    while both distress sources are silently dead."""

_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
})

# Clarke County qPublic AppID / LayerID (verified 2026-04)
_QPUBLIC_SEARCH_URL = (
    "https://qpublic.schneidercorp.com/Application.aspx"
    "?AppID=830&LayerID=14971&PageTypeID=2&PageID=7069"
)
_QPUBLIC_PARCEL_URL = (
    "https://qpublic.schneidercorp.com/Application.aspx"
    "?AppID=830&LayerID=14971&PageTypeID=4&PageID=7071&KeyValue={parcel_id}"
)

# GSCCCA lien search endpoint
_GSCCCA_LIEN_URL = "https://search.gsccca.org/RealEstate/index.aspx"


# ── helpers ───────────────────────────────────────────────────────────────────

def _get(url: str, params: dict = None, retries: int = 3) -> Optional[requests.Response]:
    """GET with retry and polite 1-second delay."""
    for attempt in range(retries):
        try:
            time.sleep(1)
            r = _SESSION.get(url, params=params, timeout=20)
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            logger.warning("GET %s attempt %d failed: %s", url, attempt + 1, e)
    return None


def _post(url: str, data: dict, retries: int = 3) -> Optional[requests.Response]:
    """POST with retry and polite 1-second delay."""
    for attempt in range(retries):
        try:
            time.sleep(1)
            r = _SESSION.post(url, data=data, timeout=20)
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            logger.warning("POST %s attempt %d failed: %s", url, attempt + 1, e)
    return None


# ── qPublic parcel detail ─────────────────────────────────────────────────────

def fetch_parcel_detail(parcel_id: str) -> dict:
    """
    Fetch a single parcel's detail page from qPublic and parse key fields.

    Returns a dict with:
        parcel_id, address, owner_name, owner_mailing_address,
        assessed_value, tax_owed, year_built, lot_size_acres, county
    Returns an empty dict on failure.
    """
    url = _QPUBLIC_PARCEL_URL.format(parcel_id=parcel_id)
    r = _get(url)
    if not r:
        return {}

    soup = BeautifulSoup(r.text, "html.parser")

    def _cell(label: str) -> str:
        """Find a table cell whose preceding label cell contains `label`."""
        for td in soup.find_all("td"):
            if label.lower() in td.get_text(strip=True).lower():
                nxt = td.find_next_sibling("td")
                if nxt:
                    return nxt.get_text(strip=True)
        return ""

    assessed_raw = _cell("Assessed Value").replace("$", "").replace(",", "")
    tax_raw = _cell("Tax Due").replace("$", "").replace(",", "")
    lot_raw = _cell("Lot Size").replace(",", "")
    year_raw = _cell("Year Built")

    parcel = {
        "parcel_id": parcel_id,
        "address": _cell("Location Address") or _cell("Situs Address"),
        "owner_name": _cell("Owner Name"),
        "owner_mailing_address": _cell("Mailing Address"),
        "assessed_value": float(assessed_raw) if assessed_raw else None,
        "tax_owed": float(tax_raw) if tax_raw else None,
        "year_built": int(year_raw) if year_raw.isdigit() else None,
        "lot_size_acres": float(lot_raw) if lot_raw else None,
        "county": "clarke",
    }
    return parcel


# ── tax delinquents ───────────────────────────────────────────────────────────

def fetch_tax_delinquents(county: str = "clarke") -> list[dict]:
    """
    Search qPublic for parcels with a non-zero tax balance (delinquent).

    qPublic doesn't expose a bulk delinquency endpoint, so this function
    queries the advanced search for parcels where "Tax Due" > 0.
    In practice, the most reliable approach is to cross-reference the
    parcel list against qPublic's tax balance field.

    Returns: list of parcel dicts (same structure as fetch_parcel_detail)
    """
    if county != "clarke":
        logger.warning("fetch_tax_delinquents: only Clarke County is currently supported")
        return []

    logger.info("Fetching tax delinquents from qPublic (Clarke County)...")

    # qPublic advanced search — filter to tax delinquent status
    # The form fields below are derived from the qPublic Clarke County search page.
    # Adjust field names if the portal is updated.
    data = {
        "PageTypeID": "2",
        "AppID": "830",
        "LayerID": "14971",
        "SearchType": "ADVANCED",
        "TaxDue": "Y",   # filter to parcels with outstanding tax balance
    }
    r = _post(_QPUBLIC_SEARCH_URL, data)
    if not r:
        raise ScraperError("failed to fetch delinquent parcel list from qPublic")

    soup = BeautifulSoup(r.text, "html.parser")
    parcel_ids = []

    # Parse result table — each row links to a parcel detail page
    for a in soup.select("table.searchresults a[href*='KeyValue=']"):
        href = a.get("href", "")
        if "KeyValue=" in href:
            pid = href.split("KeyValue=")[-1].split("&")[0]
            parcel_ids.append(pid)

    logger.info("Found %d delinquent parcel IDs", len(parcel_ids))

    results = []
    for pid in parcel_ids:
        detail = fetch_parcel_detail(pid)
        if detail:
            detail["tax_delinquent_1yr"] = True
            results.append(enrich_parcel(detail))

    return results


# ── ACC tax sale list ─────────────────────────────────────────────────────────

def fetch_tax_sale_list() -> list[dict]:
    """
    Scrape the ACC Tax Commissioner's published tax sale list.

    URL: https://www.accgov.com/1703
    The page typically hosts a PDF or HTML table of properties slated for
    the next tax sale. This function attempts HTML table parsing first,
    then falls back to a PDF download notice.

    Returns: list of dicts with parcel_id, address, tax_owed, tax_sale_list=True
    """
    logger.info("Fetching ACC tax sale list...")
    r = _get(ACC_TAX_SALE_URL)
    if not r:
        logger.error("Failed to fetch ACC tax sale page")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    results = []

    # Try to find a table with parcel data
    for table in soup.find_all("table"):
        headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
        if any(h in headers for h in ("parcel", "account", "address", "owner")):
            for row in table.find_all("tr")[1:]:  # skip header
                cells = [td.get_text(strip=True) for td in row.find_all("td")]
                if len(cells) >= 2:
                    parcel = {
                        "parcel_id": cells[0] if cells else "",
                        "address": cells[1] if len(cells) > 1 else "",
                        "tax_owed": None,
                        "county": "clarke",
                        "tax_sale_list": True,
                    }
                    results.append(enrich_parcel(parcel))
            break

    # If no table found, look for PDF links and log a notice
    if not results:
        pdf_links = [a["href"] for a in soup.find_all("a", href=True) if ".pdf" in a["href"].lower()]
        if pdf_links:
            logger.info(
                "Tax sale list appears to be a PDF — manual download required: %s",
                pdf_links[0],
            )
        else:
            logger.warning("Could not parse tax sale list — page structure may have changed")

    return results


# ── GSCCCA fi fa liens ────────────────────────────────────────────────────────

def fetch_fi_fa_liens(county: str = "clarke") -> list[dict]:
    """
    Search GSCCCA.org for fi fa (fieri facias) state and county tax liens
    recorded against Clarke County properties.

    GSCCCA is the Georgia Superior Court Clerks' Cooperative Authority.
    The lien search at search.gsccca.org is public record.

    Returns: list of dicts with parcel_id (if parseable), owner_name,
             address, fi_fa_lien=True, county
    """
    county_map = {"clarke": "Clarke", "oconee": "Oconee"}
    county_name = county_map.get(county, "Clarke")

    logger.info("Fetching fi fa liens from GSCCCA (%s County)...", county_name)

    # GSCCCA uses a GET-based search form
    params = {
        "County": county_name,
        "RecordType": "LIEN",
        "SearchType": "FiFa",
    }
    r = _get(_GSCCCA_LIEN_URL, params=params)
    if not r:
        raise ScraperError("failed to fetch GSCCCA lien search results")

    soup = BeautifulSoup(r.text, "html.parser")
    results = []

    for row in soup.select("table.searchResults tr")[1:]:
        cells = [td.get_text(strip=True) for td in row.find_all("td")]
        if len(cells) >= 3:
            parcel = {
                "parcel_id": cells[0] if cells else "",
                "owner_name": cells[1] if len(cells) > 1 else "",
                "address": cells[2] if len(cells) > 2 else "",
                "county": county,
                "fi_fa_lien": True,
            }
            results.append(enrich_parcel(parcel))

    logger.info("Found %d fi fa liens in %s County", len(results), county_name)
    return results


# ── Code enforcement ──────────────────────────────────────────────────────────

def fetch_code_violations(county: str = "clarke") -> list[dict]:
    """
    Fetch active code enforcement cases from the ACC Open Data Portal.

    Attempts to use the ACC ArcGIS REST API (open data portal).
    Falls back gracefully if the layer is not available — a FOIA request
    to ACC Code Enforcement would be required in that case.

    Returns: list of dicts with address, code_violation_active=True, county
    """
    if county != "clarke":
        logger.warning("fetch_code_violations: only Clarke County is currently supported")
        return []

    # ACC Open Data — Code Enforcement feature service (if published)
    # Layer URL from data-athensclarke.opendata.arcgis.com
    CODE_ENFORCEMENT_LAYER = (
        "https://services1.arcgis.com/Ug5xGQbHsD8zuZzM/arcgis/rest/services/"
        "Code_Enforcement_Cases/FeatureServer/0/query"
    )
    params = {
        "where": "STATUS='OPEN'",
        "outFields": "PARCEL_ID,ADDRESS,CASE_TYPE,OPEN_DATE",
        "f": "json",
        "resultRecordCount": 2000,
    }

    r = _get(CODE_ENFORCEMENT_LAYER, params=params)
    if not r:
        logger.warning(
            "Code enforcement layer unavailable — submit an open records request "
            "to ACC Code Enforcement for active case list"
        )
        return []

    try:
        data = r.json()
    except ValueError:
        logger.error("Code enforcement response was not valid JSON")
        return []

    features = data.get("features", [])
    results = []
    for feat in features:
        attrs = feat.get("attributes", {})
        parcel = {
            "parcel_id": attrs.get("PARCEL_ID", ""),
            "address": attrs.get("ADDRESS", ""),
            "county": "clarke",
            "code_violation_active": True,
        }
        results.append(enrich_parcel(parcel))

    logger.info("Found %d active code enforcement cases", len(results))
    return results


# ── geocoding ─────────────────────────────────────────────────────────────────

_GEO_CACHE: dict = {}   # address → (lat, lng) | None

# ACC ArcGIS parcels feature service — Clarke County parcel centroids
_ACC_PARCELS_LAYER = (
    "https://services1.arcgis.com/Ug5xGQbHsD8zuZzM/arcgis/rest/services/"
    "Parcels/FeatureServer/0/query"
)


def _geocode_address(address: str, county: str = "clarke") -> tuple | None:
    """
    Geocode an address to (lat, lng).

    Strategy:
      1. ACC ArcGIS parcels feature service (accurate, Clarke County only)
      2. Nominatim / OpenStreetMap (free, no key, city-level fallback)

    Results are cached per address for the lifetime of the process.
    """
    cache_key = address.strip().lower()
    if cache_key in _GEO_CACHE:
        return _GEO_CACHE[cache_key]

    result = None

    # 1 — ACC ArcGIS parcels (Clarke County only)
    if county == "clarke" and address:
        street = address.split(",")[0].strip()
        params = {
            "where": f"UPPER(SITUS_ADDR) LIKE UPPER('{street.replace(chr(39), chr(39)*2)}%')",
            "outFields": "OBJECTID",
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "json",
            "resultRecordCount": "1",
        }
        r = _get(_ACC_PARCELS_LAYER, params=params)
        if r:
            try:
                data = r.json()
                feats = data.get("features", [])
                if feats:
                    geom = feats[0].get("geometry", {})
                    x, y = geom.get("x"), geom.get("y")
                    if x is not None and y is not None and -90 <= y <= 90:
                        result = (round(y, 6), round(x, 6))
            except Exception as e:
                logger.debug("ArcGIS geocode failed for '%s': %s", address, e)

    # 2 — Nominatim fallback
    if result is None and address:
        query = f"{address}, Athens, GA, USA"
        url = (
            "https://nominatim.openstreetmap.org/search"
            f"?q={urllib.parse.quote(query)}&format=json&limit=1&countrycodes=us"
        )
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "AthensREPlatform/1.0 (private research tool)"}
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                hits = _json.loads(resp.read().decode())
            if hits:
                result = (round(float(hits[0]["lat"]), 6), round(float(hits[0]["lon"]), 6))
        except Exception as e:
            logger.debug("Nominatim geocode failed for '%s': %s", address, e)

    _GEO_CACHE[cache_key] = result
    return result


# ── absentee owner check ──────────────────────────────────────────────────────

def is_absentee_owner(parcel_id: str) -> bool:
    """
    Returns True if the owner's mailing address differs from the property
    situs address, indicating an absentee/investor owner.
    """
    detail = fetch_parcel_detail(parcel_id)
    if not detail:
        return False
    owner = (detail.get("owner_mailing_address") or "").strip().lower()
    situs = (detail.get("address") or "").strip().lower()
    return bool(owner and situs and owner != situs)


# ── full pipeline ─────────────────────────────────────────────────────────────

def run_distress_pipeline(county: str = "clarke", errors: list | None = None) -> list[dict]:
    """
    Run all scrapers, merge results by parcel_id, and return a deduplicated
    list of parcels enriched with distress scores.

    Signals from different sources are OR'd together — if any source flags
    a parcel, that signal is set to True.

    Per-source failure isolation: a source that raises ScraperError is logged
    and its message appended to `errors` (if provided), and the pipeline
    continues with the other sources — one dead source never kills the run. But
    the failure is now VISIBLE to the caller, so the nightly batch stops
    reporting `errors=0` while the distress half is entirely dead.
    """
    logger.info("Starting distress pipeline for %s county...", county)

    all_parcels: dict[str, dict] = {}  # keyed by parcel_id

    def _safe(source_name: str, fn):
        try:
            return fn()
        except ScraperError as exc:
            msg = f"distress source '{source_name}': {exc}"
            logger.error(msg)
            if errors is not None:
                errors.append(msg)
            return []

    def _merge(parcels: list[dict]):
        for p in parcels:
            pid = p.get("parcel_id") or p.get("address", "")
            if not pid:
                continue
            if pid in all_parcels:
                # Merge signals: existing takes precedence for non-signal fields
                existing = all_parcels[pid]
                for signal in ("tax_sale_list", "tax_delinquent_1yr", "fi_fa_lien",
                               "code_violation_active", "absentee_owner",
                               "code_violations_3yr", "assessed_value_declining",
                               "pre1970_no_permits"):
                    if p.get(signal):
                        existing[signal] = True
            else:
                all_parcels[pid] = p

    _merge(_safe("tax_sale_list", fetch_tax_sale_list))
    _merge(_safe("tax_delinquents", lambda: fetch_tax_delinquents(county)))
    _merge(_safe("fi_fa_liens", lambda: fetch_fi_fa_liens(county)))
    _merge(_safe("code_violations", lambda: fetch_code_violations(county)))

    # Geocode any parcels that lack lat/lng so they appear on the map
    logger.info("Geocoding parcels without coordinates...")
    for p in all_parcels.values():
        if p.get("lat") and p.get("lng"):
            continue
        addr = p.get("address", "")
        if not addr:
            continue
        coords = _geocode_address(addr, p.get("county", "clarke"))
        if coords:
            p["lat"], p["lng"] = coords
        time.sleep(1)   # respect Nominatim rate limit (1 req/sec)

    # Re-score merged parcels
    merged = [enrich_parcel(p) for p in all_parcels.values()]
    merged.sort(key=lambda x: x.get("distress_score", 0), reverse=True)

    logger.info(
        "Pipeline complete: %d unique parcels, %d high-distress",
        len(merged),
        sum(1 for p in merged if p.get("distress_tier") == "high"),
    )
    return merged
