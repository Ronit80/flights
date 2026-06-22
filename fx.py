# -*- coding: utf-8 -*-
"""שערי חליפין — ערך של 1 ש"ח בדולר וביורו (חינמי, ללא מפתח)."""
import requests

FALLBACK = {"USD": 0.27, "EUR": 0.25}  # גיבוי משוער אם ה-API לא זמין


def get_rates():
    for url in ("https://open.er-api.com/v6/latest/ILS",
                "https://api.frankfurter.app/latest?from=ILS&to=USD,EUR"):
        try:
            d = requests.get(url, timeout=20).json()
            r = d.get("rates", {})
            if r.get("USD") and r.get("EUR"):
                return {"USD": round(float(r["USD"]), 4), "EUR": round(float(r["EUR"]), 4)}
        except Exception:
            continue
    return dict(FALLBACK)
