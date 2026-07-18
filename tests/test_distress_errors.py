"""Regression test: a dead distress source must surface as a real error, not
be swallowed into `errors=0`.

The bug (observed 2026-07-18): qPublic 403'd and GSCCCA 500'd, each fetcher
logged ERROR and returned [], run_distress_pipeline returned 0 parcels, and the
nightly batch reported `errors=0, email=True` — emailing a "success" digest
while the distress half of the product was entirely non-functional.

First test in this repo. Network-free: the fetchers are monkeypatched.

Run:  cd athens-re && .venv/bin/python -m pytest tests/test_distress_errors.py -q
"""

import backend.scrapers.distressed as d


def test_scraper_error_is_collected_not_swallowed(monkeypatch):
    # Both critical sources fail to fetch; the other two return nothing.
    def boom(*a, **k):
        raise d.ScraperError("403 Forbidden")

    monkeypatch.setattr(d, "fetch_tax_delinquents", boom)
    monkeypatch.setattr(d, "fetch_fi_fa_liens", boom)
    monkeypatch.setattr(d, "fetch_tax_sale_list", lambda *a, **k: [])
    monkeypatch.setattr(d, "fetch_code_violations", lambda *a, **k: [])

    errors: list[str] = []
    parcels = d.run_distress_pipeline("clarke", errors=errors)

    # Pipeline still returns (failure-isolated), but the failures are now visible.
    assert parcels == []
    assert len(errors) == 2
    assert any("tax_delinquents" in e for e in errors)
    assert any("fi_fa_liens" in e for e in errors)


def test_healthy_run_reports_no_errors(monkeypatch):
    monkeypatch.setattr(d, "fetch_tax_delinquents", lambda *a, **k: [])
    monkeypatch.setattr(d, "fetch_fi_fa_liens", lambda *a, **k: [])
    monkeypatch.setattr(d, "fetch_tax_sale_list", lambda *a, **k: [])
    monkeypatch.setattr(d, "fetch_code_violations", lambda *a, **k: [])

    errors: list[str] = []
    d.run_distress_pipeline("clarke", errors=errors)
    assert errors == []


def test_one_dead_source_does_not_kill_the_others(monkeypatch):
    parcel = {"parcel_id": "X1", "address": "1 Main St", "tax_sale_list": True}

    def boom(*a, **k):
        raise d.ScraperError("500")

    monkeypatch.setattr(d, "fetch_tax_delinquents", boom)
    monkeypatch.setattr(d, "fetch_fi_fa_liens", lambda *a, **k: [])
    monkeypatch.setattr(d, "fetch_tax_sale_list", lambda *a, **k: [parcel])
    monkeypatch.setattr(d, "fetch_code_violations", lambda *a, **k: [])
    # Skip geocoding/network for the surviving parcel.
    monkeypatch.setattr(d, "_geocode_address", lambda *a, **k: None)

    errors: list[str] = []
    parcels = d.run_distress_pipeline("clarke", errors=errors)
    assert len(parcels) == 1                 # the healthy source still produced a parcel
    assert len(errors) == 1                  # and the dead one was reported


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
