"""Cash flow analysis for a given property."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from backend.config import SEARCH_CRITERIA


def monthly_mortgage(purchase_price: float, down_pct: float, rate_pct: float, years: int = 30) -> float:
    loan = purchase_price * (1 - down_pct / 100)
    r = rate_pct / 100 / 12
    n = years * 12
    if r == 0:
        return loan / n
    return loan * r * (1 + r) ** n / ((1 + r) ** n - 1)


def monthly_property_tax(purchase_price: float, county: str = "clarke") -> float:
    millage = SEARCH_CRITERIA["tax_millage"].get(county, 33.95)
    assessed = purchase_price * 0.4
    return assessed * millage / 1000 / 12


def analyze(
    purchase_price: float,
    estimated_rent: float,
    county: str = "clarke",
    down_pct: float | None = None,
    rate_pct: float | None = None,
    annual_tax: float | None = None,
    insurance_monthly: float | None = None,
) -> dict:
    c = SEARCH_CRITERIA
    down_pct = down_pct if down_pct is not None else c["down_payment_pct"]
    rate_pct = rate_pct if rate_pct is not None else c["interest_rate"]
    insurance = insurance_monthly if insurance_monthly is not None else c["insurance_monthly_est"]

    mortgage = monthly_mortgage(purchase_price, down_pct, rate_pct)
    tax = (annual_tax / 12) if annual_tax else monthly_property_tax(purchase_price, county)
    maintenance = estimated_rent * c["maintenance_pct"] / 100
    vacancy = estimated_rent * c["vacancy_pct"] / 100
    management = estimated_rent * c["management_pct"] / 100

    total_expenses = mortgage + tax + insurance + maintenance + vacancy + management
    cash_flow = estimated_rent - total_expenses
    down_payment = purchase_price * down_pct / 100
    cash_on_cash = (cash_flow * 12 / down_payment) * 100 if down_payment else 0
    noi = (estimated_rent - tax - insurance - maintenance) * 12
    cap_rate = (noi / purchase_price) * 100

    return {
        "monthly_mortgage": round(mortgage, 2),
        "monthly_tax": round(tax, 2),
        "monthly_insurance": round(insurance, 2),
        "monthly_maintenance": round(maintenance, 2),
        "monthly_vacancy": round(vacancy, 2),
        "monthly_management": round(management, 2),
        "total_expenses": round(total_expenses, 2),
        "monthly_cash_flow": round(cash_flow, 2),
        "annual_cash_flow": round(cash_flow * 12, 2),
        "cash_on_cash_pct": round(cash_on_cash, 2),
        "cap_rate_pct": round(cap_rate, 2),
        "down_payment": round(down_payment, 2),
    }


if __name__ == "__main__":
    import pprint
    pprint.pprint(analyze(305_000, 2_000))
