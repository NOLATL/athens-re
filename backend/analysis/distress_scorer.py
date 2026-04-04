"""
Distress scorer for Athens-area parcels.

Takes a dict of parcel data with boolean signal flags and returns a
distress score (0-100+), tier, and list of active signals.

Signals are defined in config.DISTRESS_WEIGHTS.
"""
from backend.config import DISTRESS_WEIGHTS, DISTRESS_TIERS


def score_distress(parcel_data: dict) -> dict:
    """
    Calculate distress score for a single parcel.

    Args:
        parcel_data: dict with any combination of signal keys from
                     DISTRESS_WEIGHTS as boolean values, plus optional
                     metadata fields.

    Expected signal keys (all optional, default False):
        tax_sale_list           - property on current ACC tax sale list
        tax_delinquent_1yr      - tax delinquent for 1+ years
        fi_fa_lien              - active state or county fi fa lien filed
        code_violation_active   - active code enforcement case
        water_disconnected_6mo  - water utility disconnected 6+ months (FOIA)
        code_violations_3yr     - multiple code violations in past 3 years
        absentee_owner          - owner mailing address != property address
        probate_filing          - probate filing associated with owner
        assessed_value_declining - assessed value declining year-over-year
        pre1970_no_permits      - structure pre-1970, no permit activity in 10yr

    Returns:
        dict with:
            distress_score  int     raw score (can exceed 100, capped at 100)
            distress_tier   str     "high" | "medium" | "low"
            signals         list    active signal keys sorted by weight desc
    """
    active_signals = []
    raw_score = 0

    for signal, weight in DISTRESS_WEIGHTS.items():
        if parcel_data.get(signal, False):
            active_signals.append((signal, weight))
            raw_score += weight

    # Sort signals by weight descending so highest-impact shows first
    active_signals.sort(key=lambda x: x[1], reverse=True)
    signal_keys = [s[0] for s in active_signals]

    score = min(raw_score, 100)

    # Determine tier
    if score >= DISTRESS_TIERS["high"]:
        tier = "high"
    elif score >= DISTRESS_TIERS["medium"]:
        tier = "medium"
    else:
        tier = "low"

    return {
        "distress_score": score,
        "distress_tier": tier,
        "signals": signal_keys,
    }


def enrich_parcel(parcel_data: dict) -> dict:
    """
    Score a parcel and merge the result back into the parcel dict.
    Also derives absentee_owner flag if owner/situs addresses are present.

    Returns the same dict with distress_score, distress_tier, signals added.
    """
    # Auto-derive absentee flag if not already set
    if "absentee_owner" not in parcel_data:
        owner_addr = (parcel_data.get("owner_mailing_address") or "").strip().lower()
        situs_addr = (parcel_data.get("address") or "").strip().lower()
        if owner_addr and situs_addr:
            parcel_data["absentee_owner"] = owner_addr != situs_addr

    result = score_distress(parcel_data)
    parcel_data.update(result)
    return parcel_data
