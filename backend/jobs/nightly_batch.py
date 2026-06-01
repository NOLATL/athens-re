"""
Nightly batch pipeline for the Athens RE Investment Platform.

Sequence:
  1. Load last_run_state.json
  2. Scrape fresh Redfin MLS listings (Clarke + Oconee)
  3. Run distressed property pipeline (Clarke County)
  4. Classify listing events against previous state
  5. Pre-compute rent estimates + cash flow + composite score for all listings
  6. Write updated properties.json and distressed_parcels.json
  7. Write updated last_run_state.json
  8. Send email digest if any new listings or price drops
  9. Log run summary

Usage:
  python -m backend.jobs.nightly_batch            # full run
  python -m backend.jobs.nightly_batch --dry-run  # no file writes, no email
"""
import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone

# Ensure project root is on sys.path
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "reference")
STATE_FILE = os.path.join(DATA_DIR, "last_run_state.json")
PROPERTIES_FILE = os.path.join(DATA_DIR, "properties.json")
DISTRESSED_FILE = os.path.join(DATA_DIR, "distressed_parcels.json")

# Module-level references populated lazily to avoid circular import at top level
aggregate_rent_estimates = None
analyze = None


# ── State helpers ─────────────────────────────────────────────────────────────

def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _default_state() -> dict:
    return {
        "last_run": None,
        "listing_ids": [],
        "parcel_ids": [],
        "listings": {},
    }


def _load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                raw = json.load(f)
                return _normalize_state(raw)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Could not read state file: %s — starting fresh", e)
    return _default_state()


def _normalize_state(state: dict | None) -> dict:
    normalized = _default_state()
    if not isinstance(state, dict):
        return normalized

    normalized["last_run"] = state.get("last_run")
    normalized["parcel_ids"] = list(state.get("parcel_ids", []))
    listings = state.get("listings")

    if isinstance(listings, dict) and listings:
        normalized["listings"] = listings
        normalized["listing_ids"] = list(state.get("listing_ids") or listings.keys())
        return normalized

    # Migrate legacy flat listing_ids format.
    # Mark all previously-tracked IDs as active — they were in the scrape window
    # last run, so active is correct and avoids a false "back_on_market" flood on
    # the first run after migration. last_price is unknown so price-drop detection
    # begins cleanly on the next run.
    legacy_ids = list(state.get("listing_ids", []))
    normalized["listing_ids"] = legacy_ids
    normalized["listings"] = {
        lid: {
            "listing_key": lid,
            "first_seen": state.get("last_run"),
            "last_seen": state.get("last_run"),
            "last_price": None,
            "status": "active",
            "address": "",
            "url": "",
            "mls_number": "",
            "source": "redfin",
        }
        for lid in legacy_ids
    }
    return normalized


def _save_state(state: dict) -> None:
    state = _normalize_state(state)
    state["last_run"] = _utcnow_iso()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
    logger.info(
        "State saved: %d active listings tracked, %d parcels",
        len(state.get("listing_ids", [])),
        len(state.get("parcel_ids", [])),
    )


def _normalize_address(address: str) -> str:
    address = (address or "").strip().lower()
    address = re.sub(r"[^a-z0-9]+", "-", address)
    return address.strip("-")


def _price_to_float(raw) -> float | None:
    text = str(raw or "").replace("$", "").replace(",", "").replace("~", "").strip()
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _format_price(value: float | int | None) -> str:
    if value in (None, ""):
        return "—"
    try:
        return f"${float(value):,.0f}"
    except (TypeError, ValueError):
        return str(value)


def listing_key(prop: dict) -> str:
    mls = str(prop.get("mls_number") or prop.get("mls") or prop.get("source_id") or "").strip()
    if mls:
        return f"mls:{mls}"

    url = str(prop.get("url") or "").strip()
    if url:
        return f"url:{url}"

    return f"addr:{_normalize_address(prop.get('address', ''))}"


def classify_listing_events(
    listings: list[dict],
    previous_state: dict,
    now_iso: str | None = None,
) -> tuple[dict, dict]:
    now_iso = now_iso or _utcnow_iso()
    previous_state = _normalize_state(previous_state)
    previous_listings = previous_state.get("listings", {})

    events: dict[str, list] = {
        "true_new": [],
        "unchanged": [],
        "price_drop": [],
        "disappeared": [],
        "back_on_market": [],
    }

    next_listings_state: dict[str, dict] = {}
    current_keys: set[str] = set()

    for prop in listings:
        key = listing_key(prop)
        current_keys.add(key)
        prev = previous_listings.get(key, {})
        prev_status = prev.get("status") or (
            "inactive" if key in previous_state.get("listing_ids", []) else None
        )
        prev_price = _price_to_float(prev.get("last_price"))
        current_price = _price_to_float(prop.get("price"))

        enriched = dict(prop)
        enriched["listing_key"] = key

        if not prev:
            events["true_new"].append(enriched)
        else:
            if prev_status != "active":
                events["back_on_market"].append({**enriched, "previous_status": prev_status})
            if prev_price is not None and current_price is not None and current_price < prev_price:
                events["price_drop"].append({
                    **enriched,
                    "previous_price": _format_price(prev_price),
                    "previous_price_value": prev_price,
                })
            if prev_status == "active" and not (
                prev_price is not None and current_price is not None and current_price < prev_price
            ):
                events["unchanged"].append(enriched)

        next_listings_state[key] = {
            "listing_key": key,
            "first_seen": prev.get("first_seen") or now_iso,
            "last_seen": now_iso,
            "last_price": current_price,
            "status": "active",
            "address": prop.get("address", ""),
            "url": prop.get("url", ""),
            "mls_number": prop.get("mls_number", ""),
            "source": prop.get("source", "redfin"),
            "county": prop.get("county", ""),
        }

    for key, prev in previous_listings.items():
        if key in current_keys:
            continue
        if prev.get("status") == "active":
            events["disappeared"].append({
                "listing_key": key,
                "address": prev.get("address", ""),
                "url": prev.get("url", ""),
                "price": _format_price(prev.get("last_price")),
                "type": prev.get("property_type") or prev.get("type") or "—",
            })
        next_listings_state[key] = {**prev, "status": "inactive"}

    next_state = {
        "last_run": now_iso,
        "listing_ids": sorted(current_keys),
        "parcel_ids": list(previous_state.get("parcel_ids", [])),
        "listings": next_listings_state,
    }
    return events, next_state


# ── Rent baseline refresh ─────────────────────────────────────────────────────

def _refresh_rent_baselines() -> bool:
    """
    Fetch current HUD Fair Market Rents for the Athens metro and write
    rent_baselines.json so rent_estimator.py uses up-to-date market rates.

    No-ops silently if HUD_API_TOKEN is not configured.
    Returns True if the file was updated.
    """
    try:
        from backend.scrapers.rent_sources import _fetch_hud_athens_record, _extract_hud_fmr_value
        from backend.config import HUD_API_TOKEN
        if not HUD_API_TOKEN:
            logger.debug("HUD_API_TOKEN not set — skipping rent baseline refresh")
            return False
        athens = _fetch_hud_athens_record(HUD_API_TOKEN)
        if not athens:
            return False
        baselines = {}
        for beds in range(6):
            val = _extract_hud_fmr_value(athens, beds)
            if val:
                baselines[str(beds)] = val
        if not baselines:
            return False
        path = os.path.join(DATA_DIR, "rent_baselines.json")
        with open(path, "w") as f:
            json.dump(baselines, f, indent=2)
        logger.info("Rent baselines updated from HUD FMR: %s", baselines)
        return True
    except Exception as e:
        logger.warning("HUD FMR baseline refresh failed: %s", e)
        return False


# ── Listing enrichment ────────────────────────────────────────────────────────

def _ensure_analysis_functions() -> tuple:
    global aggregate_rent_estimates, analyze
    if not callable(aggregate_rent_estimates):
        from backend.analysis.rent_estimator import aggregate_rent_estimates as _agg
        aggregate_rent_estimates = _agg
    if not callable(analyze):
        from backend.analysis.cash_flow_engine import analyze as _analyze
        analyze = _analyze
    return aggregate_rent_estimates, analyze


def _rent_status_for_result(rent_result: dict | None) -> dict:
    if not rent_result:
        return {"status": "failed", "source_count": 0, "message": "Rent estimate failed"}

    sources = rent_result.get("sources") or []
    source_count = len(sources)
    method = rent_result.get("method")

    if method == "internal_only":
        return {"status": "internal_fallback_only", "source_count": source_count or 1, "message": "Internal fallback only"}

    if source_count > 1 or method == "aggregated":
        return {"status": "external_sources", "source_count": source_count, "message": f"{source_count} source(s) used"}

    return {"status": "estimated", "source_count": source_count, "message": method or "Estimated"}


def _enrich_listing(prop: dict) -> dict:
    """Add rent estimate, cash flow, and composite investment score to a listing dict."""
    try:
        aggregate_fn, analyze_fn = _ensure_analysis_functions()

        lat = prop.get("lat", 0)
        lng = prop.get("lng", 0)
        beds = prop.get("beds", 2)
        sqft = prop.get("sqft", 0)
        property_type = prop.get("property_type", "")
        county = prop.get("county", "clarke")
        address = prop.get("address", "")

        rent_result = aggregate_fn(lat, lng, beds, sqft, property_type, county, address)
        mid_rent = (rent_result or {}).get("mid", 0)
        price = _price_to_float(prop.get("price")) or 0.0

        cf = {}
        if price > 0 and mid_rent > 0:
            cf = analyze_fn(price, mid_rent, county)

        prop["rent_estimate"] = rent_result
        prop["cash_flow"] = cf
        prop["rent_status"] = _rent_status_for_result(rent_result)

        if price > 0 and mid_rent > 0:
            try:
                from backend.analysis.property_scorer import composite_score as _composite_score
                score_result = _composite_score(
                    purchase_price=price,
                    estimated_rent=mid_rent,
                    lat=lat or 33.945,
                    lng=lng or -83.4,
                    county=county,
                    year_built=prop.get("year_built"),
                )
                prop["composite_score"] = score_result.get("composite_score")
                prop["sub_scores"] = score_result.get("sub_scores", {})
            except Exception as e:
                logger.debug("Score failed for %s: %s", address, e)

    except Exception as e:
        prop["rent_status"] = _rent_status_for_result(None)
        logger.warning("Rent enrichment failed for %s: %s", prop.get("address"), e)

    return prop


# ── Distressed parcels → GeoJSON ──────────────────────────────────────────────

def _parcels_to_geojson(parcels: list[dict]) -> dict:
    features = []
    for p in parcels:
        lat = p.get("lat")
        lng = p.get("lng")
        if not lat or not lng:
            continue
        feature = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lng, lat]},
            "properties": {k: v for k, v in p.items() if k not in ("lat", "lng")},
        }
        features.append(feature)
    return {"type": "FeatureCollection", "features": features}


# ── Main pipeline ─────────────────────────────────────────────────────────────

def run(dry_run: bool = False) -> dict:
    """
    Execute the full nightly batch pipeline.

    Args:
        dry_run: If True, skip file writes and email. Useful for local testing.

    Returns:
        Summary dict with listing/parcel counts, event counts, and errors.
    """
    start = datetime.now(timezone.utc)
    summary = {
        "started_at": start.isoformat(),
        "listings_total": 0,
        "listings_new": 0,
        "parcels_total": 0,
        "parcels_new": 0,
        "email_sent": False,
        "listing_event_counts": {},
        "errors": [],
    }

    # ── Step 1: Load previous state ───────────────────────────────────────────
    state = _load_state()
    prev_listing_ids = set(state.get("listing_ids", []))
    prev_parcel_ids = set(state.get("parcel_ids", []))
    logger.info(
        "Previous state: %d active listings, %d parcels (last run: %s)",
        len(prev_listing_ids), len(prev_parcel_ids), state.get("last_run", "never"),
    )

    # ── Step 1.5: Refresh rent baselines from HUD FMR ────────────────────────
    _refresh_rent_baselines()

    # ── Step 2: Fetch fresh Redfin listings ───────────────────────────────────
    listings: list[dict] = []
    try:
        from backend.scrapers.redfin import fetch_and_normalize, REGION_CLARKE, REGION_OCONEE
        logger.info("Fetching Redfin listings...")
        listings = fetch_and_normalize(
            counties=[(REGION_CLARKE, "clarke"), (REGION_OCONEE, "oconee")]
        )
        logger.info("Redfin: %d listings fetched", len(listings))
    except Exception as e:
        msg = f"Redfin scraper failed: {e}"
        logger.error(msg)
        summary["errors"].append(msg)

    # ── Step 3: Fetch fresh distressed parcels ────────────────────────────────
    parcels: list[dict] = []
    try:
        from backend.scrapers.distressed import run_distress_pipeline
        logger.info("Running distress pipeline...")
        parcels = run_distress_pipeline("clarke")
        logger.info("Distress pipeline: %d parcels", len(parcels))
    except Exception as e:
        msg = f"Distress pipeline failed: {e}"
        logger.error(msg)
        summary["errors"].append(msg)

    # ── Step 4: Classify listing events against previous state ────────────────
    listing_events, next_state = classify_listing_events(listings, state)
    current_parcel_ids = [p.get("parcel_id", p.get("address", f"p-{i}")) for i, p in enumerate(parcels)]
    new_parcels = [p for p, pid in zip(parcels, current_parcel_ids) if pid not in prev_parcel_ids]
    next_state["parcel_ids"] = current_parcel_ids

    summary["listings_total"] = len(listings)
    summary["listings_new"] = len(listing_events["true_new"])
    summary["parcels_total"] = len(parcels)
    summary["parcels_new"] = len(new_parcels)
    summary["listing_event_counts"] = {k: len(v) for k, v in listing_events.items()}

    logger.info(
        "Listing events: new=%d, price_drop=%d, back_on_market=%d, disappeared=%d, unchanged=%d",
        len(listing_events["true_new"]),
        len(listing_events["price_drop"]),
        len(listing_events["back_on_market"]),
        len(listing_events["disappeared"]),
        len(listing_events["unchanged"]),
    )

    # ── Step 5: Enrich all listings with rent, cash flow, and composite score ─
    logger.info("Enriching listings with rent estimates, cash flow, and scores...")
    enriched_listings = [_enrich_listing(dict(p)) for p in listings]

    # Assign global ranks by composite_score (rank 1 = best investment)
    scored = sorted(
        [p for p in enriched_listings if p.get("composite_score") is not None],
        key=lambda p: p["composite_score"],
        reverse=True,
    )
    for rank, p in enumerate(scored, 1):
        p["rank"] = rank

    enriched_by_key = {listing_key(p): p for p in enriched_listings}

    # Merge enrichment data back into event lists, preserving event-specific fields
    enriched_events: dict[str, list[dict]] = {}
    for event_name, props in listing_events.items():
        enriched_events[event_name] = []
        for item in props:
            base = dict(enriched_by_key.get(item.get("listing_key"), item))
            for extra_key in ("previous_price", "previous_price_value", "previous_status", "listing_key"):
                if extra_key in item:
                    base[extra_key] = item[extra_key]
            enriched_events[event_name].append(base)

    # ── Step 5b: Merge tracking metadata into enriched listings ──────────────
    # Attach first_seen / previous_price so the frontend can surface price history.
    price_drop_by_key = {e["listing_key"]: e for e in listing_events.get("price_drop", [])}
    for p in enriched_listings:
        key = listing_key(p)
        state_entry = next_state["listings"].get(key, {})
        p["first_seen"] = state_entry.get("first_seen")
        p["last_seen"] = state_entry.get("last_seen")
        if key in price_drop_by_key:
            p["previous_price"] = price_drop_by_key[key].get("previous_price_value")

    # ── Step 6 & 7: Write JSON files and state ────────────────────────────────
    if dry_run:
        logger.info("[DRY RUN] Would write %d listings to properties.json", len(enriched_listings))
        logger.info("[DRY RUN] Would write %d parcels to distressed_parcels.json", len(parcels))
    else:
        os.makedirs(DATA_DIR, exist_ok=True)

        with open(PROPERTIES_FILE, "w") as f:
            json.dump(enriched_listings, f, indent=2, default=str)
        logger.info("Wrote %d listings to properties.json", len(enriched_listings))

        freshness_file = os.path.join(DATA_DIR, "data_freshness.json")
        _now = datetime.now(timezone.utc)
        _date_str = f"{_now.strftime('%B')} {_now.day}, {_now.year}"
        with open(freshness_file, "w") as f:
            json.dump({"data_as_of": _date_str}, f)
        logger.info("Wrote data_freshness.json")

        geojson = _parcels_to_geojson(parcels)
        with open(DISTRESSED_FILE, "w") as f:
            json.dump(geojson, f, indent=2, default=str)
        logger.info("Wrote %d mappable parcels to distressed_parcels.json", len(geojson["features"]))

        _save_state(next_state)

    # ── Step 8: Email digest — only new listings and price drops ─────────────
    actionable_events = {
        "true_new": enriched_events["true_new"],
        "price_drop": enriched_events["price_drop"],
    }
    actionable_count = len(actionable_events["true_new"]) + len(actionable_events["price_drop"])

    if actionable_count or new_parcels:
        if dry_run:
            logger.info(
                "[DRY RUN] Would send email: %d new listings, %d price drops, %d new parcels",
                len(actionable_events["true_new"]),
                len(actionable_events["price_drop"]),
                len(new_parcels),
            )
        else:
            try:
                from backend.notifications.email_digest import send_digest
                app_url = os.getenv("APP_URL", "")
                sent = send_digest(actionable_events, new_parcels, app_url=app_url)
                summary["email_sent"] = sent
            except Exception as e:
                msg = f"Email digest failed: {e}"
                logger.error(msg)
                summary["errors"].append(msg)
    else:
        logger.info("No new listings or price drops — skipping email digest")

    # ── Step 9: Log summary ───────────────────────────────────────────────────
    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    summary["elapsed_seconds"] = round(elapsed, 1)
    logger.info(
        "Batch complete in %.1fs — new=%d, price_drop=%d, back_on_market=%d, disappeared=%d, parcels=%d, email=%s, errors=%d",
        elapsed,
        len(enriched_events["true_new"]),
        len(enriched_events["price_drop"]),
        len(enriched_events["back_on_market"]),
        len(enriched_events["disappeared"]),
        len(new_parcels),
        summary["email_sent"],
        len(summary["errors"]),
    )
    return summary


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Athens RE nightly batch pipeline")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run scrapers but skip file writes and email (safe for testing)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    summary = run(dry_run=args.dry_run)

    if summary["errors"]:
        print("\nErrors encountered:")
        for err in summary["errors"]:
            print(f"  - {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
