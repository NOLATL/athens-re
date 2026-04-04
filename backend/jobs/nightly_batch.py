"""
Nightly batch pipeline for the Athens RE Investment Platform.

Sequence:
  1. Load last_run_state.json  (previous listing addresses + parcel IDs)
  2. Scrape fresh Redfin MLS listings (Clarke + Oconee)
  3. Run distressed property pipeline (Clarke County)
  4. Diff both lists against previous state → new_listings, new_parcels
  5. Pre-compute rent estimates + cash flow for all listings
  6. Write updated properties.json and distressed_parcels.json
  7. Write updated last_run_state.json
  8. Send email digest if any new items found
  9. Log run summary

Usage:
  python -m backend.jobs.nightly_batch            # full run
  python -m backend.jobs.nightly_batch --dry-run  # no file writes, no email
"""
import argparse
import json
import logging
import os
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


# ── State helpers ─────────────────────────────────────────────────────────────

def _load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Could not read state file: %s — starting fresh", e)
    return {"last_run": None, "listing_ids": [], "parcel_ids": []}


def _save_state(listing_ids: list[str], parcel_ids: list[str]) -> None:
    state = {
        "last_run": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "listing_ids": listing_ids,
        "parcel_ids": parcel_ids,
    }
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
    logger.info("State saved: %d listings, %d parcels", len(listing_ids), len(parcel_ids))


# ── Listing enrichment ────────────────────────────────────────────────────────

def _enrich_listing(prop: dict) -> dict:
    """Add rent estimate and cash flow pre-computation to a listing dict."""
    try:
        from backend.analysis.rent_estimator import estimate_rent
        from backend.analysis.cash_flow_engine import analyze

        lat = prop.get("lat", 0)
        lng = prop.get("lng", 0)
        beds = prop.get("beds", 2)
        sqft = prop.get("sqft", 0)
        property_type = prop.get("property_type", "")
        county = prop.get("county", "clarke")

        rent_result = estimate_rent(lat, lng, beds, sqft, property_type, county)
        mid_rent = rent_result.get("mid", 0)

        # Parse price string → float
        price_raw = str(prop.get("price", "0")).replace("$", "").replace(",", "").strip()
        try:
            price = float(price_raw)
        except ValueError:
            price = 0.0

        cf = {}
        if price > 0 and mid_rent > 0:
            cf = analyze(price, mid_rent, county)

        prop["rent_estimate"] = rent_result
        prop["cash_flow"] = cf
    except Exception as e:
        logger.debug("Enrichment failed for %s: %s", prop.get("address"), e)

    return prop


# ── Distressed parcels → GeoJSON ──────────────────────────────────────────────

def _parcels_to_geojson(parcels: list[dict]) -> dict:
    """Convert flat parcel dicts from run_distress_pipeline to GeoJSON FeatureCollection."""
    features = []
    for p in parcels:
        lat = p.get("lat")
        lng = p.get("lng")
        # Skip parcels without coordinates — they can't be mapped
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
        Summary dict: {listings_total, listings_new, parcels_total, parcels_new,
                       email_sent, errors}
    """
    start = datetime.now(timezone.utc)
    summary = {
        "started_at": start.isoformat(),
        "listings_total": 0,
        "listings_new": 0,
        "parcels_total": 0,
        "parcels_new": 0,
        "email_sent": False,
        "errors": [],
    }

    # ── Step 1: Load previous state ───────────────────────────────────────────
    state = _load_state()
    prev_listing_ids = set(state.get("listing_ids", []))
    prev_parcel_ids = set(state.get("parcel_ids", []))
    logger.info(
        "Previous state: %d listings, %d parcels (last run: %s)",
        len(prev_listing_ids), len(prev_parcel_ids), state.get("last_run", "never"),
    )

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

    # ── Step 4: Diff against previous state ───────────────────────────────────
    # Use address as listing key (Redfin CSV has no stable MLS ID across runs)
    current_listing_ids = [p.get("address", f"id-{p.get('id', i)}") for i, p in enumerate(listings)]
    current_parcel_ids = [p.get("parcel_id", p.get("address", f"p-{i}")) for i, p in enumerate(parcels)]

    new_listings = [
        p for p, lid in zip(listings, current_listing_ids)
        if lid not in prev_listing_ids
    ]
    new_parcels = [
        p for p, pid in zip(parcels, current_parcel_ids)
        if pid not in prev_parcel_ids
    ]

    summary["listings_total"] = len(listings)
    summary["listings_new"] = len(new_listings)
    summary["parcels_total"] = len(parcels)
    summary["parcels_new"] = len(new_parcels)

    logger.info(
        "Diff: %d new listings, %d new distressed parcels",
        len(new_listings), len(new_parcels),
    )

    # ── Step 5: Pre-compute rent + cash flow for all listings ─────────────────
    logger.info("Enriching listings with rent estimates and cash flow...")
    enriched_listings = [_enrich_listing(p) for p in listings]
    enriched_new_listings = [
        p for p in enriched_listings
        if p.get("address") in {n.get("address") for n in new_listings}
    ]

    # ── Step 6 & 7: Write JSON files and state ────────────────────────────────
    if dry_run:
        logger.info("[DRY RUN] Would write %d listings to properties.json", len(enriched_listings))
        logger.info("[DRY RUN] Would write %d parcels to distressed_parcels.json", len(parcels))
    else:
        os.makedirs(DATA_DIR, exist_ok=True)

        with open(PROPERTIES_FILE, "w") as f:
            json.dump(enriched_listings, f, indent=2, default=str)
        logger.info("Wrote %d listings to properties.json", len(enriched_listings))

        geojson = _parcels_to_geojson(parcels)
        with open(DISTRESSED_FILE, "w") as f:
            json.dump(geojson, f, indent=2, default=str)
        logger.info("Wrote %d mappable parcels to distressed_parcels.json", len(geojson["features"]))

        _save_state(current_listing_ids, current_parcel_ids)

    # ── Step 8: Send email digest ─────────────────────────────────────────────
    if new_listings or new_parcels:
        if dry_run:
            logger.info(
                "[DRY RUN] Would send email: %d new listings, %d new parcels",
                len(new_listings), len(new_parcels),
            )
        else:
            try:
                from backend.notifications.email_digest import send_digest
                from backend.config import NOTIFY_EMAIL
                app_url = os.getenv("APP_URL", "")
                sent = send_digest(enriched_new_listings, new_parcels, app_url=app_url)
                summary["email_sent"] = sent
            except Exception as e:
                msg = f"Email digest failed: {e}"
                logger.error(msg)
                summary["errors"].append(msg)
    else:
        logger.info("No new items — skipping email digest")

    # ── Step 9: Log summary ───────────────────────────────────────────────────
    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    summary["elapsed_seconds"] = round(elapsed, 1)
    logger.info(
        "Batch complete in %.1fs — %d new listings, %d new parcels, email=%s, errors=%d",
        elapsed,
        summary["listings_new"],
        summary["parcels_new"],
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
