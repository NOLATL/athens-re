"""
Fetch active Redfin listings for Athens-area counties and save to
backend/data/reference/properties.json.

The /api/properties Flask endpoint serves this file directly.

Usage:
  python -m backend.scripts.fetch_listings

Options:
  --oconee    Also fetch Oconee County listings (verify REGION_OCONEE id first)
  --dry-run   Fetch and print results without writing to disk
"""
import argparse
import json
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

OUT_FILE = os.path.join(
    os.path.dirname(__file__), "..", "data", "reference", "properties.json"
)


def main():
    parser = argparse.ArgumentParser(description="Fetch Redfin listings for Athens area")
    parser.add_argument(
        "--oconee",
        action="store_true",
        help="Also fetch Oconee County listings (verify REGION_OCONEE id first)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print results without saving to disk",
    )
    args = parser.parse_args()

    from backend.scrapers.redfin import REGION_CLARKE, REGION_OCONEE, fetch_and_normalize

    counties = [(REGION_CLARKE, "clarke")]
    if args.oconee:
        counties.append((REGION_OCONEE, "oconee"))
        logger.info(
            "Including Oconee County (region_id=%d) — verify this ID at "
            "https://www.redfin.com/county/*/GA/Oconee-County before using",
            REGION_OCONEE,
        )

    listings = fetch_and_normalize(counties)
    if not listings:
        logger.error(
            "No listings fetched. Possible causes:\n"
            "  1. Redfin blocked the request (try again in a few minutes)\n"
            "  2. region_id is wrong (check REGION_CLARKE in scrapers/redfin.py)\n"
            "  3. No active listings match the property type filter"
        )
        sys.exit(1)

    if args.dry_run:
        print(json.dumps(listings[:3], indent=2))
        print(f"\n[dry-run] {len(listings)} listings would be saved to {OUT_FILE}")
        return

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(listings, f, indent=2)

    logger.info("Saved %d listings → %s", len(listings), OUT_FILE)
    size_kb = os.path.getsize(OUT_FILE) / 1024
    logger.info("File size: %.1f KB", size_kb)


if __name__ == "__main__":
    main()
