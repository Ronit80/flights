"""
חיפוש טיסות הלוך-ושוב למספר יעדים דרך Travelpayouts (Aviasales) Flight Data API.
חינמי. מסנן לכל יעד: טיסה ישירה בלבד, הלוך בשעות 10:00-15:00,
חזור ערב/לילה, חלון תאריכים גמיש. מחזיר את הזולות לכל יעד + קישור הזמנה.

הערה: המחיר מ-Aviasales הוא לכל נוסע (הלוך-חזור). הסוכן מכפיל
במספר הנוסעים לאומדן משפחתי. המחיר הסופי המדויק ייקבע באתר ההזמנה
(במיוחד לילדים) — הקישור מצורף לכל דיל.
"""
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import time
import requests

API = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"
AVIASALES = "https://www.aviasales.com"

AIRLINES = {
    "JU": "Air Serbia", "LY": "El Al", "W6": "Wizz Air", "W4": "Wizz Air Malta",
    "W9": "Wizz Air UK", "IZ": "Arkia", "6H": "Israir", "OS": "Austrian",
    "LH": "Lufthansa", "A3": "Aegean", "TK": "Turkish", "FB": "Bulgaria Air",
    "QS": "Smartwings", "OK": "Czech Airlines", "RO": "Tarom",
    "LO": "LOT", "BT": "airBaltic", "RYR": "Ryanair", "FR": "Ryanair",
    "BZ": "Bluebird Airways", "5W": "Wizz Air Abu Dhabi", "EW": "Eurowings",
    "VY": "Vueling", "U2": "easyJet", "DY": "Norwegian",
}


def _date_pairs(start, end, min_nights, max_nights, blackout_start=None, blackout_end=None):
    """כל זוגות (הלוך, חזור) בחלון שעומדים ב-min..max לילות.
    מדלג על נסיעות שחופפות לטווח החסום (blackout) — אם הוגדר."""
    d0 = datetime.strptime(start, "%Y-%m-%d")
    d1 = datetime.strptime(end, "%Y-%m-%d")
    bs = datetime.strptime(blackout_start, "%Y-%m-%d") if blackout_start else None
    be = datetime.strptime(blackout_end, "%Y-%m-%d") if blackout_end else None
    out = []
    dep = d0
    while dep <= d1:
        for n in range(min_nights, max_nights + 1):
            ret = dep + timedelta(days=n)
            if ret > d1:
                continue
            # דילוג אם הנסיעה חופפת לטווח החסום
            if bs and be and dep <= be and ret >= bs:
                continue
            out.append((dep.strftime("%Y-%m-%d"), ret.strftime("%Y-%m-%d"), n))
        dep += timedelta(days=1)
    return out


def _hour(iso_dt):
    # "2026-09-27T11:35:00+03:00" -> 11
    return int(iso_dt[11:13])


def _hhmm(s):
    return int(s[:2]) * 60 + int(s[3:5])


def _israel_landing(ret_at, dur_back):
    """דקות-ביום של הנחיתה בישראל (IDT, UTC+3) לטיסת החזור, או None."""
    try:
        hh, mm = int(ret_at[11:13]), int(ret_at[14:16])
        sign = 1 if ret_at[19] == "+" else -1
        off = sign * (int(ret_at[20:22]) * 60 + int(ret_at[23:25]))
        land = (hh * 60 + mm) - off + int(dur_back or 0) + 180  # +3h שעון ישראל
        return land % 1440
    except Exception:
        return None


def _query(token, origin, destination, dep_date, ret_date, direct, currency):
    params = {
        "origin": origin,
        "destination": destination,
        "departure_at": dep_date,
        "return_at": ret_date,
        "currency": currency,
        "direct": "true" if direct else "false",
        "one_way": "false",
        "sorting": "price",
        "limit": 30,
        "token": token,
    }
    for attempt in range(4):
        r = requests.get(API, params=params, timeout=40)
        if r.status_code == 429:  # חריגה ממגבלת קצב — המתנה וניסיון חוזר
            time.sleep(2 + attempt * 2)
            continue
        r.raise_for_status()
        return r.json()
    r.raise_for_status()
    return r.json()


def _search_destination(token, s, dest):
    """מחזיר את הדילים הזולים ליעד בודד שעומדים בכל התנאים."""
    pax = s["adults"] + len(s["children_ages"])
    pairs = _date_pairs(s["window_start"], s["window_end"], s["min_nights"], s["max_nights"],
                        s.get("blackout_start"), s.get("blackout_end"))
    offers, errors = [], 0

    def _fetch(pair):
        dep, ret, nights = pair
        try:
            return nights, _query(token, s["origin"], dest["code"], dep, ret,
                                  s["nonstop_only"], s["currency"])
        except requests.HTTPError:
            return nights, None

    # חיפוש מקבילי — הרבה יותר מהיר (במקום סדרתי)
    with ThreadPoolExecutor(max_workers=10) as ex:
        results = list(ex.map(_fetch, pairs))

    for nights, data in results:
        if data is None:
            errors += 1
            continue
        for o in data.get("data", []):
            if s["nonstop_only"] and (o.get("transfers", 0) or o.get("return_transfers", 0)):
                continue
            dep_at, ret_at = o.get("departure_at", ""), o.get("return_at", "")
            if not dep_at or not ret_at:
                continue
            out_h = _hour(dep_at)
            if not (s["outbound_earliest_hour"] <= out_h <= s["outbound_latest_hour"]):
                continue
            # סינון לפי שעת הנחיתה בישראל בחזרה (ברירת מחדל 16:00-18:30)
            land = _israel_landing(ret_at, o.get("duration_back") or 0)
            le = _hhmm(s.get("return_landing_earliest", "16:00"))
            ll = _hhmm(s.get("return_landing_latest", "18:30"))
            if land is None or not (le <= land <= ll):
                continue
            land_str = f"{land // 60:02d}:{land % 60:02d}"

            unit = float(o["price"])
            offers.append({
                "total": round(unit * pax),
                "per_person": round(unit),
                "currency": data.get("currency", s["currency"]).upper(),
                "airline": AIRLINES.get(o.get("airline", ""), o.get("airline", "?")),
                "dep_date": dep_at[:10], "dep_time": dep_at[11:16],
                "ret_date": ret_at[:10], "ret_time": ret_at[11:16],
                "nights": nights,
                "dur_to": o.get("duration_to") or 0,
                "dur_back": o.get("duration_back") or 0,
                "land_time": land_str,
                "link": AVIASALES + o["link"] if o.get("link") else AVIASALES,
            })

    offers.sort(key=lambda x: x["total"])
    seen, unique = set(), []
    for o in offers:
        key = (o["dep_date"], o["dep_time"], o["ret_date"], o["airline"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(o)
    return unique[: s.get("top_per_destination", 2)], errors


def find_best(cfg):
    """מחזיר רשימת יעדים, כל אחד עם הדילים הזולים שלו."""
    s = cfg["search"]
    token = cfg["travelpayouts"]["token"]
    results = []
    total_pairs = len(_date_pairs(s["window_start"], s["window_end"],
                                  s["min_nights"], s["max_nights"],
                                  s.get("blackout_start"), s.get("blackout_end")))
    for dest in s["destinations"]:
        top, errors = _search_destination(token, s, dest)
        results.append({"name": dest["name"], "code": dest["code"],
                        "offers": top, "errors": errors})
    # מיון יעדים לפי הדיל הזול ביותר שנמצא בכל אחד
    results.sort(key=lambda d: d["offers"][0]["total"] if d["offers"] else 10**12)
    return results, total_pairs
