"""
Flask API — serves property data to the React frontend.
Run: flask --app backend/api/app.py run --port 5000
"""
import sys, os

# Ensure project root is on sys.path so `backend.*` imports work when Flask
# is started via the CLI (which does not add CWD to sys.path automatically).
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import gzip, json, math, re
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)
CORS(app)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "reference")

# Cache entries: filename → (mtime, data)
# Re-reads the file if it has been modified since last load (e.g. by the nightly batch job).
_file_cache: dict = {}

def _load(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return {}
    mtime = os.path.getmtime(path)
    cached = _file_cache.get(filename)
    if cached and cached[0] == mtime:
        return cached[1]
    with open(path) as f:
        data = json.load(f)
    _file_cache[filename] = (mtime, data)
    return data


@app.get("/api/properties")
def get_properties():
    data = _load("properties.json")
    # Always return a list — _load returns {} when file is missing
    return jsonify(data if isinstance(data, list) else [])


@app.get("/api/market-stats")
def get_market_stats():
    return jsonify(_load("market_stats.json"))


@app.get("/api/development-projects")
def get_development_projects():
    return jsonify(_load("development_projects.json"))


@app.get("/api/zoning-geojson")
def get_zoning_geojson():
    """
    Serve the ACC zoning GeoJSON for the Leaflet map overlay.
    Returns the simplified version (if available) with gzip compression.

    Query params:
      zone   str   if provided, filter to a single zone code (e.g. ?zone=RS-15)
    """
    from backend.gis.zoning_lookup import get_zoning_overlay_path

    path = get_zoning_overlay_path()
    if not os.path.exists(path):
        return jsonify({"error": "Zoning data not yet downloaded. Run backend/scripts/download_shapefiles.py"}), 503

    zone_filter = request.args.get("zone", "").strip().upper()

    # If no filter, stream the file directly with gzip compression
    if not zone_filter:
        with open(path, "rb") as f:
            raw = f.read()
        compressed = gzip.compress(raw, compresslevel=6)
        return Response(
            compressed,
            status=200,
            headers={
                "Content-Type": "application/geo+json",
                "Content-Encoding": "gzip",
                "Cache-Control": "public, max-age=3600",
                "Access-Control-Allow-Origin": "*",
            },
        )

    # Filtered: parse JSON, filter features, return subset
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    features = [
        feat for feat in data.get("features", [])
        if (feat.get("properties") or {}).get("CurrentZn", "").upper() == zone_filter
    ]
    return jsonify({"type": "FeatureCollection", "features": features})


@app.get("/api/zoning-lookup")
def zoning_lookup():
    """
    Point-in-polygon zoning lookup.
    Query params: lat (float), lng (float)
    Returns: parcel_id, zoning_code, lot_size_acres, address, owner_name, absentee_owner
    """
    try:
        lat = float(request.args["lat"])
        lng = float(request.args["lng"])
    except (KeyError, ValueError):
        return jsonify({"error": "lat and lng query params required"}), 400

    from backend.gis.zoning_lookup import get_zoning
    result = get_zoning(lat, lng)
    if not result:
        return jsonify({"error": "No parcel found at this location"}), 404
    return jsonify(result)


@app.get("/api/distressed-parcels")
def get_distressed_parcels():
    """
    Returns distressed parcels as a GeoJSON FeatureCollection.

    Query params:
      min_score  int   minimum distress score (default 0)
      county     str   "clarke" | "oconee" | "all" (default "all")
      limit      int   max results (default 200)
    """
    min_score = int(request.args.get("min_score", 0))
    county = request.args.get("county", "all").lower()
    limit = int(request.args.get("limit", 200))

    parcels = _load("distressed_parcels.json")
    if isinstance(parcels, dict) and "features" in parcels:
        # Already GeoJSON
        features = parcels["features"]
    else:
        features = parcels if isinstance(parcels, list) else []

    filtered = []
    for feat in features:
        props = feat.get("properties", feat)  # support both GeoJSON and plain list
        score = props.get("distress_score", 0)
        pcounty = props.get("county", "")
        if score >= min_score and (county == "all" or pcounty == county):
            filtered.append(feat)
        if len(filtered) >= limit:
            break

    return jsonify({
        "type": "FeatureCollection",
        "features": filtered,
        "meta": {
            "total": len(filtered),
            "min_score": min_score,
            "county": county,
        },
    })


@app.get("/api/distressed-parcels/<parcel_id>")
def get_distressed_parcel(parcel_id: str):
    """Full opportunity card for a single parcel."""
    parcels = _load("distressed_parcels.json")
    features = parcels.get("features", parcels) if isinstance(parcels, dict) else parcels

    for feat in (features if isinstance(features, list) else []):
        props = feat.get("properties", feat)
        if props.get("parcel_id") == parcel_id:
            return jsonify(props)

    return jsonify({"error": "Parcel not found"}), 404


@app.get("/api/census-tracts")
def get_census_tracts():
    """
    Serve Clarke County census tract boundaries + ACS demographics as GeoJSON.

    The data is pre-built by backend/scripts/download_census_data.py and cached
    on disk. Returns 503 if the file has not been downloaded yet.

    Query params:
      fields  str   comma-separated list of demographic fields to include in
                    properties (default: all). E.g. ?fields=median_household_income,renter_pct
    """
    from backend.gis.census_demographics import load_census_geojson, get_census_overlay_path

    data = load_census_geojson()
    if data is None:
        return jsonify({
            "error": "Census tract data not yet downloaded. Run: python -m backend.scripts.download_census_data"
        }), 503

    fields_param = request.args.get("fields", "").strip()
    if fields_param:
        keep = set(fields_param.split(","))
        # Always keep geometry-identifying fields
        keep.update({"GEOID", "NAME", "tract_code", "geoid"})
        for feat in data.get("features", []):
            props = feat.get("properties") or {}
            feat["properties"] = {k: v for k, v in props.items() if k in keep}

    compressed = gzip.compress(
        json.dumps(data, separators=(",", ":")).encode("utf-8"),
        compresslevel=6,
    )
    return Response(
        compressed,
        status=200,
        headers={
            "Content-Type": "application/geo+json",
            "Content-Encoding": "gzip",
            "Cache-Control": "public, max-age=86400",
            "Access-Control-Allow-Origin": "*",
        },
    )


@app.get("/api/cash-flow")
def get_cash_flow():
    """
    Run rent estimation + cash flow analysis for a property.

    Query params (all optional except price):
      price           float   purchase price
      lat             float   latitude  (default Athens centroid)
      lng             float   longitude (default Athens centroid)
      beds            int     bedroom count (default 2)
      sqft            int     square footage (default 0)
      property_type   str     Redfin property type string
      county          str     "clarke" | "oconee" (default "clarke")
      hoa_monthly     float   HOA monthly fee (default 0)
      rent_override   float   use this rent value instead of estimating
    """
    try:
        price = float(request.args["price"])
    except (KeyError, ValueError):
        return jsonify({"error": "price query param required (numeric)"}), 400

    try:
        lat = float(request.args.get("lat", 33.945))
        lng = float(request.args.get("lng", -83.4))
        beds = int(float(request.args.get("beds", 2)))
        sqft = int(float(request.args.get("sqft", 0)))
        property_type = request.args.get("property_type", "")
        county = request.args.get("county", "clarke").lower()
        hoa_monthly = float(request.args.get("hoa_monthly", 0))
        rent_override = request.args.get("rent_override")
        down_pct = float(request.args.get("down_pct", 0)) or None
        rate_pct = float(request.args.get("rate_pct", 0)) or None
    except Exception as e:
        import traceback
        return jsonify({"error": "param parse error", "detail": traceback.format_exc()}), 400

    try:
        from backend.analysis.rent_estimator import aggregate_rent_estimates
        from backend.analysis.cash_flow_engine import analyze
    except Exception as e:
        import traceback
        return jsonify({"error": "import error", "detail": traceback.format_exc()}), 500

    try:
        if rent_override:
            mid = round(float(rent_override))
            rent_est = {
                "low": round(mid * 0.88),
                "mid": mid,
                "high": round(mid * 1.12),
                "method": "override",
                "per_unit": False,
                "sources": [{"source": "Manual override", "mid": mid}],
            }
        else:
            address = request.args.get("address", "")
            rent_est = aggregate_rent_estimates(lat, lng, beds, sqft, property_type, county, address)

        cf = analyze(
            purchase_price=price,
            estimated_rent=rent_est["mid"],
            county=county,
            down_pct=down_pct,
            rate_pct=rate_pct,
        )

        # Fold HOA into cash flow (it's an expense not captured by analyze())
        if hoa_monthly:
            cf["monthly_cash_flow"] = round(cf["monthly_cash_flow"] - hoa_monthly, 2)
            cf["annual_cash_flow"] = round(cf["annual_cash_flow"] - hoa_monthly * 12, 2)
            cf["total_expenses"] = round(cf["total_expenses"] + hoa_monthly, 2)
        cf["hoa_monthly"] = round(hoa_monthly, 2)

        return jsonify({
            "rent_estimate": rent_est,
            "cash_flow": cf,
        })
    except Exception:
        import traceback
        return jsonify({"error": "analysis error", "detail": traceback.format_exc()}), 500


@app.get("/api/score")
def get_score():
    """
    Composite investment score (0-100) for a property.
    Combines cash flow (35%), appreciation/proximity (25%), entry price vs.
    comps (20%), demand/proximity (10%), and risk/flood/age (10%).

    Query params:
      price           float  purchase price (required)
      lat, lng        float  coordinates
      beds            int    bedroom count (default 2)
      sqft            int    square footage (default 0)
      property_type   str    Redfin property type string
      county          str    "clarke" | "oconee" (default "clarke")
      year_built      int    for risk scoring (optional)
      rent_override   float  skip rent estimation
    """
    try:
        price = float(request.args["price"])
    except (KeyError, ValueError):
        return jsonify({"error": "price required"}), 400

    try:
        lat = float(request.args.get("lat", 33.945))
        lng = float(request.args.get("lng", -83.4))
        beds = int(float(request.args.get("beds", 2)))
        sqft = int(float(request.args.get("sqft", 0)))
        property_type = request.args.get("property_type", "")
        county = request.args.get("county", "clarke").lower()
        yr_raw = request.args.get("year_built", "")
        year_built = int(yr_raw) if yr_raw and yr_raw.isdigit() else None
        rent_override = request.args.get("rent_override")
    except Exception:
        import traceback
        return jsonify({"error": "param error", "detail": traceback.format_exc()}), 400

    try:
        from backend.analysis.rent_estimator import estimate_rent
        from backend.analysis.property_scorer import composite_score
    except Exception:
        import traceback
        return jsonify({"error": "import error", "detail": traceback.format_exc()}), 500

    try:
        # Rent estimate
        if rent_override:
            mid_rent = round(float(rent_override))
        else:
            mid_rent = estimate_rent(lat, lng, beds, sqft, property_type, county)["mid"]

        # Comp median price for entry-price scoring
        import math, re
        def _hav(la1, lo1, la2, lo2):
            R = 3958.8
            a = math.sin(math.radians(la2 - la1) / 2) ** 2 + math.cos(math.radians(la1)) * math.cos(math.radians(la2)) * math.sin(math.radians(lo2 - lo1) / 2) ** 2
            return R * 2 * math.asin(math.sqrt(a))

        comp_avg_price = None
        props = _load("properties.json")
        if isinstance(props, list) and props:
            comp_prices = []
            for prop in props:
                if prop.get("county", "clarke") != county:
                    continue
                if abs(int(prop.get("beds") or 0) - beds) > 1:
                    continue
                p_lat, p_lng = prop.get("lat"), prop.get("lng")
                if not p_lat or not p_lng:
                    continue
                if _hav(lat, lng, float(p_lat), float(p_lng)) > 4.0:
                    continue
                m = re.search(r"[\d]+", str(prop.get("price") or "").replace(",", ""))
                if m:
                    comp_prices.append(float(m.group()))
            if comp_prices:
                comp_prices.sort()
                comp_avg_price = comp_prices[len(comp_prices) // 2]

        result = composite_score(price, mid_rent, lat, lng, county, year_built, comp_avg_price)
        return jsonify(result)
    except Exception:
        import traceback
        return jsonify({"error": "score error", "detail": traceback.format_exc()}), 500


@app.post("/api/score-batch")
def score_batch():
    """
    Score multiple properties in parallel.
    Body: JSON array of objects, each with the same fields as /api/score.
    Returns: JSON object keyed by the 'id' field of each input item.
    """
    try:
        items = request.get_json(force=True)
        if not isinstance(items, list):
            return jsonify({"error": "body must be a JSON array"}), 400
    except Exception:
        return jsonify({"error": "invalid JSON body"}), 400

    try:
        from backend.analysis.rent_estimator import estimate_rent
        from backend.analysis.property_scorer import composite_score
    except Exception:
        import traceback
        return jsonify({"error": "import error", "detail": traceback.format_exc()}), 500

    # Pre-load properties once for comp lookup (shared across all workers)
    props_list = _load("properties.json")
    if not isinstance(props_list, list):
        props_list = []

    def _score_one(item):
        prop_id = item.get("id")
        try:
            price = float(item["price"])
            lat   = float(item.get("lat", 33.945))
            lng   = float(item.get("lng", -83.4))
            beds  = int(float(item.get("beds", 2)))
            sqft  = int(float(item.get("sqft", 0)))
            property_type = item.get("property_type", "")
            county = item.get("county", "clarke").lower()
            yr_raw = item.get("year_built", "")
            year_built = int(yr_raw) if yr_raw and str(yr_raw).isdigit() else None

            if item.get("rent_override"):
                mid_rent = round(float(item["rent_override"]))
            else:
                mid_rent = estimate_rent(lat, lng, beds, sqft, property_type, county)["mid"]

            # Comp median price
            def _hav(la1, lo1, la2, lo2):
                R = 3958.8
                a = math.sin(math.radians(la2-la1)/2)**2 + math.cos(math.radians(la1)) * math.cos(math.radians(la2)) * math.sin(math.radians(lo2-lo1)/2)**2
                return R * 2 * math.asin(math.sqrt(a))

            comp_avg_price = None
            if props_list:
                comp_prices = []
                for p in props_list:
                    if p.get("county", "clarke") != county:
                        continue
                    if abs(int(p.get("beds") or 0) - beds) > 1:
                        continue
                    p_lat, p_lng = p.get("lat"), p.get("lng")
                    if not p_lat or not p_lng:
                        continue
                    if _hav(lat, lng, float(p_lat), float(p_lng)) > 4.0:
                        continue
                    m = re.search(r"[\d]+", str(p.get("price") or "").replace(",", ""))
                    if m:
                        comp_prices.append(float(m.group()))
                if comp_prices:
                    comp_prices.sort()
                    comp_avg_price = comp_prices[len(comp_prices) // 2]

            result = composite_score(price, mid_rent, lat, lng, county, year_built, comp_avg_price)
            return prop_id, result
        except Exception:
            import traceback
            return prop_id, {"error": traceback.format_exc()}

    results = {}
    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = {executor.submit(_score_one, item): item.get("id") for item in items}
        for future in as_completed(futures):
            prop_id, result = future.result()
            results[prop_id] = result

    return jsonify(results)


@app.get("/api/comps")
def get_comps():
    """
    Find comparable active listings for a subject property.
    Uses properties.json (same data as /api/properties).

    Query params:
      price      float  subject price (required)
      lat        float  subject latitude  (default Athens centroid)
      lng        float  subject longitude
      beds       int    bedroom count (default 2)
      sqft       int    square footage (default 0 = unknown)
      county     str    "clarke" | "oconee" (default "clarke")
      radius_mi  float  search radius in miles (default 4.0)

    Returns:
      comp_count, median_price, median_price_per_sqft,
      subject_price_per_sqft, fair_value_estimate (if sqft known),
      price_vs_comps_pct (positive = above market)
    """
    import math, re

    try:
        price = float(request.args["price"])
    except (KeyError, ValueError):
        return jsonify({"error": "price required"}), 400

    lat = float(request.args.get("lat", 33.945))
    lng = float(request.args.get("lng", -83.4))
    beds = int(float(request.args.get("beds", 2)))
    sqft = int(float(request.args.get("sqft", 0)))
    county = request.args.get("county", "clarke").lower()
    radius_mi = float(request.args.get("radius_mi", 4.0))

    def _haversine(lat1, lng1, lat2, lng2):
        R = 3958.8
        d_lat = math.radians(lat2 - lat1)
        d_lng = math.radians(lng2 - lng1)
        a = math.sin(d_lat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lng / 2) ** 2
        return R * 2 * math.asin(math.sqrt(a))

    def _parse_price(raw):
        m = re.search(r"[\d]+", str(raw or "").replace(",", ""))
        return float(m.group()) if m else None

    properties = _load("properties.json")
    if not isinstance(properties, list) or not properties:
        return jsonify({"comp_count": 0})

    comps = []
    for prop in properties:
        if prop.get("county", "clarke") != county:
            continue
        prop_sqft = int(prop.get("sqft") or 0)
        if prop_sqft <= 0:
            continue
        prop_beds = int(prop.get("beds") or 0)
        if abs(prop_beds - beds) > 1:
            continue
        p_lat = prop.get("lat")
        p_lng = prop.get("lng")
        if not p_lat or not p_lng:
            continue
        if _haversine(lat, lng, float(p_lat), float(p_lng)) > radius_mi:
            continue
        prop_price = _parse_price(prop.get("price"))
        if not prop_price or prop_price <= 0:
            continue
        comps.append({"price": prop_price, "sqft": prop_sqft, "ppsf": prop_price / prop_sqft})

    if not comps:
        return jsonify({"comp_count": 0})

    sorted_prices = sorted(c["price"] for c in comps)
    sorted_ppsf = sorted(c["ppsf"] for c in comps)
    n = len(comps)
    median_price = sorted_prices[n // 2]
    median_ppsf = sorted_ppsf[n // 2]

    result = {
        "comp_count": n,
        "median_price": round(median_price),
        "median_price_per_sqft": round(median_ppsf),
    }

    if sqft > 0:
        fair_value = round(median_ppsf * sqft)
        result["fair_value_estimate"] = fair_value
        result["subject_price_per_sqft"] = round(price / sqft)
        result["price_vs_comps_pct"] = round((price - fair_value) / fair_value * 100, 1)
    else:
        result["price_vs_comps_pct"] = round((price - median_price) / median_price * 100, 1)

    return jsonify(result)


@app.get("/api/traffic")
def get_traffic():
    """
    Return nearest major traffic corridor context for a lat/lng point.

    Query params:
      lat        float  latitude  (default Athens centroid)
      lng        float  longitude
      radius_mi  float  search radius in miles (default 0.75)

    Returns traffic corridor details including AADT, road type, tier,
    and a 0-100 demand_signal for the composite scorer.
    Returns {"found": false} if no corridor within radius.
    """
    try:
        lat = float(request.args.get("lat", 33.945))
        lng = float(request.args.get("lng", -83.4))
        radius_mi = float(request.args.get("radius_mi", 2.0))
    except ValueError:
        return jsonify({"error": "lat, lng, radius_mi must be numeric"}), 400

    try:
        from backend.analysis.traffic_lookup import get_traffic_context
        result = get_traffic_context(lat, lng, radius_mi=radius_mi)
        if result is None:
            return jsonify({"found": False, "radius_mi": radius_mi})
        return jsonify({"found": True, **result})
    except Exception:
        import traceback
        return jsonify({"error": "traffic lookup failed", "detail": traceback.format_exc()}), 500


@app.get("/api/permit-activity")
def get_permit_activity():
    """
    Summarize building permit activity near a property location.

    Requires acc_permits.json to be present (run fetch_permit_data.py first).
    Returns gracefully with data_available=false if file is missing.

    Query params:
      lat        float  latitude  (default Athens centroid)
      lng        float  longitude
      radius_mi  float  search radius in miles (default 0.5)
      years_back int    years of permit history (default 3)
    """
    try:
        lat = float(request.args.get("lat", 33.945))
        lng = float(request.args.get("lng", -83.4))
        radius_mi = float(request.args.get("radius_mi", 0.5))
        years_back = int(request.args.get("years_back", 3))
    except ValueError:
        return jsonify({"error": "invalid query params"}), 400

    try:
        from backend.analysis.permit_activity import get_permit_activity as _get_permits
        result = _get_permits(lat, lng, radius_mi=radius_mi, years_back=years_back)
        return jsonify(result)
    except Exception:
        import traceback
        return jsonify({"error": "permit lookup failed", "detail": traceback.format_exc()}), 500


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
