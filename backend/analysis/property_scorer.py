"""
Composite property scorer (0-100).
Combines cash flow, appreciation potential, entry price, demand, and risk.
"""
from backend.config import SEARCH_CRITERIA
from backend.analysis.cash_flow_engine import analyze as cash_flow_analyze
from backend.gis.proximity_scoring import score_proximity
from backend.gis.flood_zone import get_flood_zone
from backend.analysis.traffic_lookup import get_traffic_context


def score_cash_flow(cf_result: dict) -> float:
    """0-100 based on monthly cash flow and CoC return."""
    cf = cf_result["monthly_cash_flow"]
    coc = cf_result["cash_on_cash_pct"]
    # Cash flow: -$500 = 0, $0 = 40, $500+ = 100
    cf_score = max(0, min(100, (cf + 500) / 1000 * 100))
    # CoC: 0% = 0, 5% = 50, 10%+ = 100
    coc_score = max(0, min(100, coc * 10))
    return round((cf_score + coc_score) / 2, 1)


def score_entry_price(list_price: int, comp_avg_price: int | None) -> float:
    """0-100: below comp average = higher score."""
    if not comp_avg_price:
        return 50.0  # neutral when no comp data
    ratio = list_price / comp_avg_price
    # 0.85x comps = 100, at comps = 50, 1.15x comps = 0
    return max(0, min(100, (1.15 - ratio) / 0.30 * 100))


def score_risk(flood_result: dict, year_built: int | None) -> float:
    """0-100: higher = lower risk."""
    risk = 100.0
    if flood_result.get("requires_insurance"):
        risk -= 30
    if year_built and year_built < 1980:
        risk -= 15
    elif year_built and year_built < 1960:
        risk -= 25
    return max(0, round(risk, 1))


def composite_score(
    purchase_price: float,
    estimated_rent: float,
    lat: float,
    lng: float,
    county: str = "clarke",
    year_built: int | None = None,
    comp_avg_price: int | None = None,
) -> dict:
    weights = SEARCH_CRITERIA["score_weights"]

    cf = cash_flow_analyze(purchase_price, estimated_rent, county)
    cf_score = score_cash_flow(cf)

    prox = score_proximity(lat, lng)
    appreciation_score = prox["proximity_score"]

    entry_score = score_entry_price(int(purchase_price), comp_avg_price)

    # Demand score: UGA/amenity proximity (60%) + traffic corridor signal (40%)
    traffic = get_traffic_context(lat, lng)
    traffic_signal = traffic["demand_signal"] if traffic else 0
    demand_score = round(
        min(100, prox["proximity_score"] * 0.60 + traffic_signal * 0.40), 1
    )

    flood = get_flood_zone(lat, lng)
    risk_score = score_risk(flood, year_built)

    total = (
        cf_score * weights["cash_flow"]
        + appreciation_score * weights["appreciation"]
        + entry_score * weights["entry_price"]
        + demand_score * weights["demand"]
        + risk_score * weights["risk"]
    )

    return {
        "composite_score": round(total, 1),
        "sub_scores": {
            "cash_flow": cf_score,
            "appreciation": round(appreciation_score, 1),
            "entry_price": round(entry_score, 1),
            "demand": round(demand_score, 1),
            "risk": risk_score,
        },
        "cash_flow_detail": cf,
        "proximity_detail": prox,
        "flood_detail": flood,
        "traffic_detail": traffic,
    }


if __name__ == "__main__":
    import pprint
    # Park Ridge Ct duplex
    pprint.pprint(composite_score(305_000, 2_000, 33.934262, -83.340972))
