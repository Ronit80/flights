"""
הערכת מזג אוויר לתאריכי השהייה — ממוצע אקלימי מ-5 השנים האחרונות
(Open-Meteo Archive, חינמי, ללא מפתח). מחזיר טמפ' צפויה ומספר ימי גשם צפויים.
"""
import time
import requests

ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"

# קואורדינטות לפי קוד שדה תעופה (ערים נפוצות למשפחות)
COORDS = {
    "PRG": (50.08, 14.44), "BUD": (47.50, 19.04), "KRK": (50.06, 19.94),
    "WAW": (52.23, 21.01), "SOF": (42.70, 23.32), "VIE": (48.21, 16.37),
    "ATH": (37.98, 23.73), "LCA": (34.92, 33.62), "BCN": (41.39, 2.16),
    "FCO": (41.80, 12.24), "MXP": (45.63, 8.72), "CDG": (49.01, 2.55),
    "TBS": (41.71, 44.78), "BUS": (41.61, 41.60), "BEG": (44.82, 20.29),
}

_YEARS = (2021, 2022, 2023, 2024, 2025)
RAIN_MM = 1.0  # סף "יום גשום"


def _swap_year(date_str, year):
    # "2026-09-24" -> "2021-09-24"
    return f"{year}{date_str[4:]}"


def stay_weather(code, dep_date, ret_date):
    """מחזיר {tmax, tmin, rainy_days, days} כממוצע על פני 5 שנים, או None."""
    if code not in COORDS:
        return None
    lat, lon = COORDS[code]
    tmaxs, tmins, rainy_counts, day_counts = [], [], [], []

    for y in _YEARS:
        try:
            r = requests.get(ARCHIVE, params={
                "latitude": lat, "longitude": lon,
                "start_date": _swap_year(dep_date, y),
                "end_date": _swap_year(ret_date, y),
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                "timezone": "auto",
            }, timeout=30)
            r.raise_for_status()
            daily = r.json().get("daily", {})
        except Exception:
            continue
        tmax = [v for v in daily.get("temperature_2m_max", []) if v is not None]
        tmin = [v for v in daily.get("temperature_2m_min", []) if v is not None]
        prcp = [v for v in daily.get("precipitation_sum", []) if v is not None]
        if not tmax:
            continue
        tmaxs.append(sum(tmax) / len(tmax))
        tmins.append(sum(tmin) / len(tmin) if tmin else 0)
        rainy_counts.append(sum(1 for p in prcp if p >= RAIN_MM))
        day_counts.append(len(prcp))
        time.sleep(0.1)

    if not tmaxs:
        return None
    return {
        "tmax": round(sum(tmaxs) / len(tmaxs)),
        "tmin": round(sum(tmins) / len(tmins)),
        "rainy_days": round(sum(rainy_counts) / len(rainy_counts)),
        "days": round(sum(day_counts) / len(day_counts)) if day_counts else 0,
    }


def monthly_climate(code, months=(7, 8, 9, 10)):
    """ממוצע אקלים חודשי לכל יעד: {חודש: {tmax,tmin,rain_frac}}.
    מאפשר לדפדפן להעריך מזג אוויר לכל תאריך בלי קריאות API."""
    if code not in COORDS:
        return {}
    lat, lon = COORDS[code]
    # צובר ימים לפי חודש על פני 5 שנים
    buckets = {m: {"tmax": [], "tmin": [], "rain": 0, "days": 0} for m in months}
    for y in _YEARS:
        try:
            r = requests.get(ARCHIVE, params={
                "latitude": lat, "longitude": lon,
                "start_date": f"{y}-07-01", "end_date": f"{y}-10-31",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                "timezone": "auto",
            }, timeout=40)
            r.raise_for_status()
            daily = r.json().get("daily", {})
        except Exception:
            continue
        dates = daily.get("time", [])
        tmax = daily.get("temperature_2m_max", [])
        tmin = daily.get("temperature_2m_min", [])
        prcp = daily.get("precipitation_sum", [])
        for i, ds in enumerate(dates):
            m = int(ds[5:7])
            if m not in buckets:
                continue
            b = buckets[m]
            if i < len(tmax) and tmax[i] is not None:
                b["tmax"].append(tmax[i])
            if i < len(tmin) and tmin[i] is not None:
                b["tmin"].append(tmin[i])
            b["days"] += 1
            if i < len(prcp) and prcp[i] is not None and prcp[i] >= RAIN_MM:
                b["rain"] += 1
        time.sleep(0.1)

    out = {}
    for m, b in buckets.items():
        if not b["tmax"]:
            continue
        out[str(m)] = {
            "tmax": round(sum(b["tmax"]) / len(b["tmax"])),
            "tmin": round(sum(b["tmin"]) / len(b["tmin"])) if b["tmin"] else 0,
            "rain_frac": round(b["rain"] / b["days"], 3) if b["days"] else 0.2,
        }
    return out
