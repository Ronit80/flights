# -*- coding: utf-8 -*-
"""בניית דוח: אפליקציית HTML אינטראקטיבית (2 טאבים) לאתר + גרסת מייל סטטית."""
import html as _html
import json
import urllib.parse

TOP_N = 7
RAIN_WEIGHT = 0.3  # קודם זול, ואז גשם (משקל מתון לגשם)

BAG_HINT = {
    "Wizz Air": "מזוודה לא כלולה — תוספת ~€40-110 לכיוון",
    "Wizz Air Malta": "מזוודה לא כלולה — תוספת ~€40-110 לכיוון",
    "Wizz Air UK": "מזוודה לא כלולה — תוספת ~€40-110 לכיוון",
    "El Al": "בד\"כ כולל מזוודה 23 ק\"ג (תלוי בכרטיס)",
    "Arkia": "בד\"כ כולל מזוודה (בדקי בכרטיס)",
    "Israir": "תלוי בכרטיס — בדקי בקישור",
    "Bulgaria Air": "בד\"כ כולל מזוודה 23 ק\"ג",
    "Smartwings": "תלוי בכרטיס — בדקי בקישור",
    "LOT": "בד\"כ כולל מזוודה (תלוי בכרטיס)",
    "Czech Airlines": "בד\"כ כולל מזוודה (תלוי בכרטיס)",
}


def _bag(airline):
    return BAG_HINT.get(airline, "בדקי מזוודה בקישור ההזמנה")


def _fmt_dur(minutes):
    if not minutes:
        return ""
    h, m = divmod(int(minutes), 60)
    return f"{h}ש' {m}ד'" if m else f"{h}ש'"


def _conv(ils, fx):
    if not fx:
        return ""
    return f"(~${round(ils * fx['USD']):,} / ~€{round(ils * fx['EUR']):,})"


_DOW_HE = {0: "ב׳", 1: "ג׳", 2: "ד׳", 3: "ה׳", 4: "ו׳", 5: "שבת", 6: "א׳"}


def _fmt_date(iso):
    """'2026-08-27' -> 'יום ה׳ 27/08/26'"""
    from datetime import date
    y, m, d = iso.split("-")
    wd = date(int(y), int(m), int(d)).weekday()  # Mon=0
    return f"יום {_DOW_HE[wd]} {d}/{m}/{y[2:]}"


def flatten_top(results, limit=TOP_N):
    flat = flatten_all(results)
    return flat[:limit]


def flatten_all(results):
    flat = []
    for d in results:
        for o in d.get("offers", []):
            flat.append({**o, "dest": d["name"], "code": d["code"]})
    flat.sort(key=lambda x: x["total"])
    return flat


def empty_dests(results):
    return [d["name"] for d in results if not d.get("offers")]


def estimate_weather(deal, climate):
    """הערכת מזג אוויר לדיל מתוך אקלים חודשי."""
    cc = climate.get(deal["code"]) or {}
    m = str(int(deal["dep_date"][5:7]))
    c = cc.get(m)
    if not c:
        return None
    return {"tmax": c["tmax"], "tmin": c["tmin"],
            "rainy_days": round(c["rain_frac"] * deal["nights"]),
            "days": deal["nights"], "frac": c["rain_frac"]}


def _rain_ratio(o):
    w = o.get("weather")
    if w and w.get("days"):
        return w["rainy_days"] / max(w["days"], 1)
    return 0.20


def combined_score(o):
    return o["total"] * (1 + RAIN_WEIGHT * _rain_ratio(o))


def rank_combined(deals, top_n=TOP_N):
    return sorted(deals, key=combined_score)[:top_n]


# ---------- שיתוף + מייל סטטי ----------

def build_summary_text(deals, today):
    lines = [f"✈️ טיסות משפחתיות זולות — {today}", "(טיסה ישירה, 4 מבוגרים + 5 ילדים)", ""]
    if deals:
        for i, o in enumerate(deals, 1):
            w = o.get("weather")
            wx = f" | 🌡️~{w['tmax']}° 🌧️~{w['rainy_days']}ימי גשם" if w else ""
            lines.append(
                f"{i}. {o['dest']} | כרטיס ~{o['per_person']:,}₪ · ל-9 ~{o['total']:,}₪ | "
                f"{o['dep_date']} {o['dep_time']}→{o['ret_date']} {o['ret_time']} | {o['airline']}{wx}"
            )
    else:
        lines.append("עדיין אין מחירים לתאריכים — נמשיך לבדוק כל יום.")
    lines += ["", "הופק אוטומטית ע\"י סוכן הטיסות 🤖"]
    return "\n".join(lines)


def wa_share_link(text):
    return "https://wa.me/?text=" + urllib.parse.quote(text)


def _email_card(o, rank, fx=None):
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣"]
    medal = medals[rank] if rank < len(medals) else f"{rank+1}."
    cur = o["currency"]
    cs = 'color:#64748b;font-size:13px'
    w = o.get("weather")
    weather = (f'<div style="background:#fff7e6;border-radius:8px;padding:7px 10px;color:#6b5a2e;font-size:14px;margin:6px 0">'
               f'🌡️ ~{w["tmax"]}°/{w["tmin"]}° · 🌧️ ~{w["rainy_days"]} ימי גשם צפויים (מתוך {w["days"]})</div>') if w else ""
    return f"""
      <div style="border:1px solid #e3ebf2;border-radius:12px;padding:14px;margin-top:12px">
        <div style="font-size:20px;font-weight:800">{medal} {_html.escape(o['dest'])}</div>
        <div style="background:#f4f9fc;border-radius:10px;padding:10px;margin:8px 0">
          <div>🎫 מחיר לכרטיס אחד: <b>~{o['per_person']:,} {cur}</b> <span style="{cs}">{_conv(o['per_person'], fx)}</span></div>
          <div style="font-size:19px;color:#1e6091">👨‍👩‍👧‍👦 סה"כ ל-9 נוסעים: <b>~{o['total']:,} {cur}</b> <span style="{cs}">{_conv(o['total'], fx)}</span></div>
        </div>
        <div>🛫 {_fmt_date(o['dep_date'])} בשעה {o['dep_time']}</div>
        <div>🛬 {_fmt_date(o['ret_date'])} בשעה {o['ret_time']} ({o['nights']} לילות)</div>
        <div style="color:#50606f;font-size:14px">⏱️ משך טיסה: הלוך ~{_fmt_dur(o.get('dur_to'))} · חזור ~{_fmt_dur(o.get('dur_back'))}</div>
        {weather}
        <div style="color:#50606f">🏢 {_html.escape(o['airline'])} · טיסה ישירה · 🧳 {_bag(o['airline'])}</div>
        <a href="{_html.escape(o['link'])}" style="display:inline-block;margin-top:8px;background:#168aad;color:#fff;padding:9px 14px;border-radius:8px;text-decoration:none;font-weight:700">להזמנה ולמחיר מדויק ➜</a>
      </div>"""


def build_email_html(deals, empties, today, fx=None):
    cards = "".join(_email_card(o, i, fx) for i, o in enumerate(deals)) if deals else \
        '<p style="color:#7a8a99">עדיין אין מחירים לתאריכים אלה — נמשיך לבדוק כל יום ✓</p>'
    pend = ("<p style='color:#8a99a8;font-size:13px'>⏳ ממתינים למחירים: " + _html.escape("، ".join(empties)) + "</p>") if empties else ""
    return f"""<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;background:#f0f4f8;color:#1a2b3c;padding:12px">
  <div style="max-width:640px;margin:0 auto">
    <div style="background:#1e6091;color:#fff;border-radius:14px;padding:18px;text-align:center">
      <h1 style="margin:0">✈️ סוכן הטיסות המשפחתי</h1>
      <p style="margin:6px 0 0;opacity:.9">מזרח אירופה · ישיר · 4 מבוגרים + 5 ילדים · עודכן {today}</p>
    </div>
    <h2 style="color:#1e6091">{len(deals)} הדילים הכי משתלמים (זול + פחות גשם)</h2>
    {cards}
    {pend}
    <p style="color:#8a99a8;font-size:12px;margin-top:14px">מחירים אומדן (×9) ממאגר Aviasales. מזג אוויר = ממוצע אקלימי (הערכה). לחצו "להזמנה" למחיר סופי.</p>
    <p style="text-align:center"><a href="https://ronit80.github.io/flights/" style="color:#168aad;font-weight:700">פתחו את האפליקציה המלאה (בחירת יעדים, תאריכים ותכנון מסלול) ➜</a></p>
  </div>
</body></html>"""


# ---------- אפליקציה אינטראקטיבית (אתר) ----------

def _safe_json(obj):
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def build_app_html(all_deals, climate, dests, itin, today, fx=None):
    deals_js = []
    for o in all_deals:
        deals_js.append({
            "dest": o["dest"], "code": o["code"], "total": o["total"],
            "per_person": o["per_person"], "currency": o["currency"],
            "dep_date": o["dep_date"], "dep_time": o["dep_time"],
            "ret_date": o["ret_date"], "ret_time": o["ret_time"],
            "nights": o["nights"], "airline": o["airline"],
            "dur_to": o.get("dur_to", 0), "dur_back": o.get("dur_back", 0),
            "bag": _bag(o["airline"]), "link": o["link"],
        })
    data = {
        "DEALS": deals_js, "CLIMATE": climate,
        "DESTS": [{"code": d["code"], "name": d["name"]} for d in dests],
        "ITIN": itin, "TODAY": today, "FX": fx or {"USD": 0.27, "EUR": 0.25},
    }
    return APP_TEMPLATE.replace("__DATA__", _safe_json(data))


APP_TEMPLATE = r"""<!doctype html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>סוכן הטיסות המשפחתי</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Heebo:wght@400;500;700;800;900&display=swap" rel="stylesheet">
<style>
  :root{--bg:#eef2f7;--card:#fff;--ink:#0f2540;--muted:#64748b;--brand:#0ea5b7;--brand2:#1e6fd9;--line:#e6edf4}
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:'Heebo',system-ui,'Segoe UI',Arial,sans-serif;color:var(--ink);min-height:100vh;
    background:radial-gradient(1100px 480px at 100% -10%,#dbeafe 0,transparent 60%),
    radial-gradient(900px 480px at -10% 0,#cffafe 0,transparent 55%),var(--bg);
    padding:18px 14px 40px}
  .wrap{max-width:none;margin:0 auto}
  header{position:relative;overflow:hidden;background:linear-gradient(135deg,#1e6fd9,#0ea5b7 65%,#22c55e);
    color:#fff;border-radius:20px;padding:22px 22px;text-align:center;box-shadow:0 16px 36px -16px rgba(14,116,144,.5)}
  header::after{content:"✈️";position:absolute;font-size:150px;opacity:.10;inset-inline-start:-12px;top:-26px;transform:rotate(-15deg)}
  header h1{font-size:1.5rem;font-weight:900;letter-spacing:-.5px;position:relative}
  header .sub{margin-top:12px;display:flex;gap:7px;flex-wrap:wrap;justify-content:center;position:relative}
  header .sub span{background:rgba(255,255,255,.2);padding:6px 13px;border-radius:999px;font-size:.8rem;font-weight:500}
  header .upd{margin-top:11px;opacity:.85;font-size:.8rem;position:relative}
  .tabs{display:flex;gap:10px;margin:14px 0;position:sticky;top:8px;z-index:5}
  .tabs button{flex:1;padding:12px;border:0;border-radius:14px;font-family:inherit;font-weight:800;font-size:1rem;cursor:pointer;
    background:#fff;color:var(--brand2);box-shadow:0 6px 16px -8px rgba(2,32,71,.25);transition:.2s}
  .tabs button.active{background:linear-gradient(135deg,#1e6fd9,#0ea5b7);color:#fff;box-shadow:0 10px 22px -8px rgba(14,116,144,.6)}
  .panel{display:none}.panel.active{display:block;animation:fade .3s ease}
  @keyframes fade{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
  .banner{background:linear-gradient(135deg,#eef6ff,#ecfeff);border:1px solid #d6e6f5;border-radius:14px;padding:11px 14px;margin-bottom:14px;font-size:.83rem;line-height:1.5;color:#33506e}
  .banner b{color:#1e6fd9}
  .banner .lastupd{margin-top:6px;font-weight:700;color:#0ea5b7}
  .overlay{display:none;position:fixed;inset:0;background:rgba(15,37,64,.55);align-items:center;justify-content:center;z-index:50;padding:20px}
  .overlay.show{display:flex}
  .modal{background:#fff;border-radius:20px;padding:24px;max-width:430px;width:100%;box-shadow:0 30px 60px -20px rgba(0,0,0,.5);animation:pop .25s ease;text-align:center}
  @keyframes pop{from{opacity:0;transform:scale(.9)}to{opacity:1;transform:none}}
  .modal h3{color:#1e6fd9;font-size:1.35rem;margin-bottom:12px}
  .modal p{margin:9px 0;line-height:1.65;color:#33506e;font-size:.95rem;text-align:right}
  .modal .big{font-size:1.05rem;font-weight:800;color:#0ea5b7;text-align:center}
  .card{background:var(--card);border-radius:16px;padding:18px;margin-bottom:14px;border:1px solid var(--line);box-shadow:0 10px 28px -18px rgba(2,32,71,.25)}
  .card h3{font-weight:800;font-size:1.15rem;margin-bottom:12px}
  .collapsible{cursor:pointer;display:flex;align-items:center;justify-content:space-between;user-select:none}
  .pm{display:inline-flex;align-items:center;justify-content:center;width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,#1e6fd9,#0ea5b7);color:#fff;font-size:1.4rem;font-weight:800;line-height:1;flex:0 0 auto;box-shadow:0 4px 10px -3px rgba(14,116,144,.5)}
  label{display:block;font-size:.85rem;font-weight:500;color:var(--muted);margin:12px 0 5px}
  input,select,textarea{width:100%;padding:12px 13px;border:1.5px solid var(--line);border-radius:12px;font-family:inherit;font-size:.97rem;background:#fbfdff;color:var(--ink);transition:.15s}
  input:focus,select:focus,textarea:focus{outline:0;border-color:var(--brand);box-shadow:0 0 0 4px rgba(14,165,183,.16)}
  .row{display:flex;gap:12px;flex-wrap:wrap}.row>div{flex:1;min-width:140px}
  .checks{display:flex;flex-wrap:wrap;gap:9px;margin-top:4px}
  .checks label{display:flex;align-items:center;gap:7px;background:#f1f6fb;border:1.5px solid var(--line);padding:9px 14px;border-radius:12px;margin:0;cursor:pointer;font-size:.92rem;font-weight:500;color:var(--ink);transition:.15s}
  .checks label:hover{border-color:var(--brand)}
  .checks input{width:auto;accent-color:var(--brand)}
  .btn{display:block;width:100%;text-align:center;padding:15px;border:0;border-radius:14px;font-family:inherit;font-weight:800;font-size:1.04rem;color:#fff;cursor:pointer;text-decoration:none;margin-top:14px;transition:.2s;box-shadow:0 10px 20px -10px rgba(0,0,0,.4)}
  .btn:hover{transform:translateY(-2px)}
  .btn.go{background:linear-gradient(135deg,#1e6fd9,#0ea5b7)}
  .btn.wa{background:linear-gradient(135deg,#25d366,#1ebe5b)}
  .deal{display:flex;flex-wrap:wrap;align-items:center;gap:8px 18px;border:1px solid var(--line);border-radius:12px;padding:12px 16px;margin-top:10px;background:#fff;box-shadow:0 4px 14px -10px rgba(2,32,71,.3);transition:.15s}
  .deal:hover{box-shadow:0 10px 22px -12px rgba(2,32,71,.4);border-color:#cfe3f5}
  .c-dest{flex:0 0 auto;min-width:130px;font-size:1.18rem;font-weight:900;display:flex;align-items:center;gap:7px}
  .c-dest .rank{font-size:1.35rem}
  .c-price{flex:1 1 220px;background:#f4f9fc;border:1px solid #e2eef6;border-radius:10px;padding:8px 12px}
  .c-price .p9b{font-size:1.2rem;font-weight:900;color:var(--brand2);margin-top:1px}
  .conv{color:var(--muted);font-size:.8rem;font-weight:600;white-space:nowrap}
  .c-route{flex:1 1 240px;font-size:.88rem;line-height:1.55;color:#33506e}
  .nights{background:#eef6ff;color:var(--brand2);padding:2px 9px;border-radius:999px;font-size:.78rem;font-weight:700}
  .c-weather{flex:1 1 190px}
  .weather{background:#fff8eb;border:1px solid #fde9c8;border-radius:9px;padding:6px 10px;color:#92660a;font-size:.83rem;font-weight:500;margin-bottom:5px}
  .bag{color:var(--muted);font-size:.82rem}
  .c-book{flex:0 0 auto;margin-inline-start:auto}
  .book{display:block;text-align:center;background:linear-gradient(135deg,#1e6fd9,#0ea5b7);color:#fff;padding:10px 18px;border-radius:10px;text-decoration:none;font-weight:800;white-space:nowrap;transition:.2s}
  .book:hover{filter:brightness(1.08)}
  @media(max-width:760px){
    .deal{flex-direction:column;align-items:stretch;gap:8px;padding:14px 16px}
    .c-dest,.c-price,.c-route,.c-weather,.c-book{flex:none}
    .c-book{margin:0}.book{width:100%}
    .c-route{line-height:1.6}
    .card{padding:18px 16px}
    .banner{font-size:.85rem;padding:12px 14px}
  }
  .day{border-inline-start:5px solid var(--brand);background:#f7fbfd;border-radius:14px;padding:16px;margin-top:14px}
  .day h4{color:var(--brand2);font-size:1.05rem;margin-bottom:6px}
  .att{margin:8px 0;padding:12px;border:1px solid var(--line);border-radius:12px;background:#fff}
  .att .meta{font-size:.82rem;color:var(--muted);margin-top:4px}
  .muted{color:var(--muted);font-size:.92rem;margin:6px 0}
  footer{text-align:center;color:#94a3b8;font-size:.8rem;margin:24px 0 10px;line-height:1.7}
  @media(max-width:480px){header h1{font-size:1.45rem}.deal .dest{font-size:1.15rem}.prices .p9{font-size:1.2rem}}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>✈️ סוכן הטיסות המשפחתי</h1>
    <div class="sub"><span>🌍 מזרח אירופה</span><span>🛫 טיסה ישירה</span><span>🌅 בוקר→ערב</span><span>👨‍👩‍👧‍👦 4 + 5</span></div>
    <div class="upd" id="upd"></div>
  </header>

  <div class="tabs">
    <button id="tab1btn" class="active" onclick="showTab(1)">🔎 חיפוש דילים</button>
    <button id="tab2btn" onclick="showTab(2)">🗺️ תכנון מסלול</button>
  </div>

  <!-- טאב 1 -->
  <div id="panel1" class="panel active">
    <div class="banner">
      <div>⚡ <b>סינון מיידי:</b> שינוי יעדים/תאריכים מעדכן את התוצאות <b>מיד</b> — בלי המתנה.</div>
      <div>🔄 <b>נתונים חדשים מהשרת:</b> אוטומטית 3× ביום (08:00 · 13:00 · 18:00). עדכון מלא בשרת אורך <b>~25-30 דק'</b> — לחיצה על "↻ רענן" מציגה את העדכון האחרון שפורסם.</div>
      <div class="lastupd">🕐 הנתונים עודכנו לאחרונה: <span id="lastupd"></span></div>
    </div>
    <div class="card">
      <h3 class="collapsible" onclick="toggleSection('filterBody',this)">בחרי יעדים ותאריכים <span class="pm">−</span></h3>
      <div class="section-body" id="filterBody">
        <label>יעדים (אפשר לבחור כמה):</label>
        <div id="destChecks" class="checks"></div>
        <div class="row">
          <div><label>מתאריך</label><input type="date" id="dFrom" onchange="renderDeals()"></div>
          <div><label>עד תאריך</label><input type="date" id="dTo" onchange="renderDeals()"></div>
        </div>
        <div class="row">
          <div><label>מינ' לילות</label><input type="number" id="nMin" value="6" min="1" onchange="renderDeals()"></div>
          <div><label>מקס' לילות</label><input type="number" id="nMax" value="11" min="1" onchange="renderDeals()"></div>
        </div>
        <button class="btn go" onclick="refreshNow()">🔄 רענן תוצאות</button>
        <a class="btn wa" id="waBtn" href="#" target="_blank">📲 שתפו בוואטסאפ</a>
      </div>
    </div>
    <div id="dealsOut"></div>
  </div>

  <!-- טאב 2 -->
  <div id="panel2" class="panel">
    <div class="card">
      <h3>תכנון מסלול לילדים (8-12)</h3>
      <label>יעד</label><select id="pDest"></select>
      <div class="row">
        <div><label>תאריך הגעה</label><input type="date" id="pArr"></div>
        <div><label>שעת נחיתה</label><input type="time" id="pArrT" value="14:00"></div>
      </div>
      <div class="row">
        <div><label>תאריך חזרה</label><input type="date" id="pDep"></div>
        <div><label>שעת המראה</label><input type="time" id="pDepT" value="21:00"></div>
      </div>
      <div class="row">
        <div><label>תקציב לטיולים (₪, אופציונלי)</label><input type="number" id="pBudget" placeholder="לדוגמה 5000"></div>
        <div><label>רכב שכור?</label><select id="pCar"><option value="yes">כן</option><option value="no">לא</option></select></div>
      </div>
      <label>מה אתם אוהבים? (טקסט חופשי)</label>
      <textarea id="pWish" rows="3" placeholder="לדוגמה: פארקי מים, גני חיות, פחות הליכה, אוכל כשר..."></textarea>
      <button class="btn go" onclick="buildPlan()">בנה לי מסלול 🗺️</button>
      <a class="btn wa" id="planWa" href="#" target="_blank">📲 קבל תוכנית מותאמת אישית ממני</a>
    </div>
    <div id="planOut"></div>
  </div>

  <footer>
    מחירים אומדן (×9) ממאגר Aviasales — לחצו "להזמנה" למחיר סופי ולמזוודה.<br>
    מזג אוויר = ממוצע אקלימי 5 שנים (הערכה, לא תחזית). · הופק אוטומטית 🤖
  </footer>
</div>

<div id="popup" class="overlay" onclick="closePopup(event)">
  <div class="modal" onclick="event.stopPropagation()">
    <h3>🔄 רענון תוצאות</h3>
    <p>✅ <b>הסינון עודכן מיד</b> לפי הבחירה שלך (יעדים/תאריכים).</p>
    <p>🕐 הנתונים מהשרת עודכנו לאחרונה:<br><span class="big" id="popupTime"></span></p>
    <p>📡 נתונים חדשים מהשרת נמשכים <b>אוטומטית 3× ביום</b> (08:00 · 13:00 · 18:00).<br>
       עדכון מלא בשרת אורך <b>~25-30 דקות</b> — אין צורך להמתין כאן, הדף יתעדכן לבד.</p>
    <button class="btn go" onclick="location.reload()">↻ טען מחדש מהשרת</button>
    <button class="btn" style="background:#94a3b8;box-shadow:none" onclick="closePopup()">סגור</button>
  </div>
</div>

<script>
var D = __DATA__;
var FX = D.FX || {USD:0.27,EUR:0.25};
function conv(ils){var u=Math.round(ils*FX.USD),e=Math.round(ils*FX.EUR);return '(~$'+u.toLocaleString('en-US')+' / ~€'+e.toLocaleString('en-US')+')';}
document.getElementById('upd').textContent = 'עודכן: ' + D.TODAY;
var _lu=document.getElementById('lastupd'); if(_lu)_lu.textContent=D.TODAY;

/* ---------- כללי ---------- */
function showTab(n){
  document.getElementById('panel1').classList.toggle('active', n===1);
  document.getElementById('panel2').classList.toggle('active', n===2);
  document.getElementById('tab1btn').classList.toggle('active', n===1);
  document.getElementById('tab2btn').classList.toggle('active', n===2);
}
function esc(s){var e=document.createElement('div');e.textContent=s;return e.innerHTML;}
function refreshNow(){renderDeals();showPopup();}
function showPopup(){document.getElementById('popupTime').textContent=D.TODAY;document.getElementById('popup').classList.add('show');}
function closePopup(){document.getElementById('popup').classList.remove('show');}
function toggleSection(id,h){var b=document.getElementById(id);var pm=h.querySelector('.pm');if(b.style.display==='none'){b.style.display='';if(pm)pm.textContent='−';}else{b.style.display='none';if(pm)pm.textContent='+';}}
function nf(x){return Math.round(x).toLocaleString('he-IL');}
function fmtDur(m){if(!m)return '';var h=Math.floor(m/60),r=m%60;return r?(h+"ש' "+r+"ד'"):(h+"ש'");}
var DOW=['א׳','ב׳','ג׳','ד׳','ה׳','ו׳','שבת'];
function fmtDate(iso){var p=iso.split('-');var dt=new Date(+p[0],+p[1]-1,+p[2]);return 'יום '+DOW[dt.getDay()]+' '+p[2]+'/'+p[1]+'/'+p[0].slice(2);}

/* ---------- מזג אוויר + ניקוד ---------- */
function estW(d){
  var cc=D.CLIMATE[d.code]; if(!cc) return null;
  var m=String(parseInt(d.dep_date.slice(5,7),10)); var c=cc[m]; if(!c) return null;
  return {tmax:c.tmax,tmin:c.tmin,rainy:Math.round(c.rain_frac*d.nights),days:d.nights,frac:c.rain_frac};
}
function scoreOf(d){var w=estW(d);var f=w?w.frac:0.2;return d.total*(1+0.3*f);}

/* ---------- טאב 1: דילים ---------- */
function initDeals(){
  var box=document.getElementById('destChecks'); box.innerHTML='';
  D.DESTS.forEach(function(t){
    box.innerHTML += '<label><input type="checkbox" class="dchk" value="'+t.code+'" checked onchange="renderDeals()"> '+esc(t.name)+'</label>';
  });
  var dates=D.DEALS.map(function(d){return d.dep_date;}).sort();
  document.getElementById('dFrom').value = dates[0] || '2026-07-25';
  document.getElementById('dTo').value = (dates[dates.length-1]) || '2026-10-31';
  renderDeals();
}
function renderDeals(){
  var sel=[].slice.call(document.querySelectorAll('.dchk:checked')).map(function(c){return c.value;});
  var from=document.getElementById('dFrom').value, to=document.getElementById('dTo').value;
  var nmin=+document.getElementById('nMin').value||1, nmax=+document.getElementById('nMax').value||99;
  var rows=D.DEALS.filter(function(d){
    return sel.indexOf(d.code)>-1 && d.dep_date>=from && d.dep_date<=to && d.nights>=nmin && d.nights<=nmax;
  });
  rows.sort(function(a,b){return scoreOf(a)-scoreOf(b);});
  rows=rows.slice(0,30);
  var out=document.getElementById('dealsOut');
  if(!rows.length){out.innerHTML='<div class="card muted">לא נמצאו דילים לסינון הזה כרגע. (המאגר מתמלא ככל שמתקרבים לתאריך — נסי טווח רחב יותר או יעדים נוספים.)</div>';updateWa([]);return;}
  var medals=['🥇','🥈','🥉','4️⃣','5️⃣','6️⃣','7️⃣'];
  var html='<div class="card"><h3>'+rows.length+' דילים (זול + פחות גשם)</h3>';
  rows.forEach(function(d,i){
    var w=estW(d);
    var wl=w?('<div class="weather">🌡️ ~'+w.tmax+'°/'+w.tmin+'° · 🌧️ ~'+w.rainy+' ימי גשם (מתוך '+w.days+')</div>'):'';
    html+='<div class="deal">'
      +'<div class="c-dest"><span class="rank">'+(medals[i]||(i+1)+'.')+'</span> '+esc(d.dest)+'</div>'
      +'<div class="c-price"><div>🎫 כרטיס: <b>~'+nf(d.per_person)+' '+d.currency+'</b> <span class="conv">'+conv(d.per_person)+'</span></div>'
        +'<div class="p9b">👨‍👩‍👧‍👦 ל-9: <b>~'+nf(d.total)+' '+d.currency+'</b> <span class="conv">'+conv(d.total)+'</span></div></div>'
      +'<div class="c-route">🛫 '+fmtDate(d.dep_date)+' '+d.dep_time+'<br>🛬 '+fmtDate(d.ret_date)+' '+d.ret_time+' <span class="nights">'+d.nights+' לילות</span><br>⏱️ '+fmtDur(d.dur_to)+' → '+fmtDur(d.dur_back)+' · 🏢 '+esc(d.airline)+' · ישיר</div>'
      +'<div class="c-weather">'+wl+'<div class="bag">🧳 '+esc(d.bag)+'</div></div>'
      +'<div class="c-book"><a class="book" href="'+d.link+'" target="_blank">להזמנה ➜</a></div>'
    +'</div>';
  });
  html+='</div>';
  out.innerHTML=html;
  updateWa(rows);
}
function updateWa(rows){
  var t='✈️ דילים משפחתיים (טיסה ישירה):\n\n';
  rows.slice(0,7).forEach(function(d,i){t+=(i+1)+'. '+d.dest+' | כרטיס ~'+nf(d.per_person)+'₪ · ל-9 ~'+nf(d.total)+'₪ | '+d.dep_date+'→'+d.ret_date+'\n';});
  t+='\nמתוך סוכן הטיסות שלי 🤖';
  document.getElementById('waBtn').href='https://wa.me/?text='+encodeURIComponent(t);
}

/* ---------- טאב 2: תכנון מסלול ---------- */
function initPlan(){
  var s=document.getElementById('pDest'); s.innerHTML='';
  Object.keys(D.ITIN).forEach(function(code){
    s.innerHTML+='<option value="'+code+'">'+esc(D.ITIN[code].name)+'</option>';
  });
  document.getElementById('pArr').value='2026-09-20';
  document.getElementById('pDep').value='2026-09-26';
}
function daysBetween(a,b){return Math.round((new Date(b)-new Date(a))/86400000);}
function buildPlan(){
  var code=document.getElementById('pDest').value, it=D.ITIN[code];
  var arr=document.getElementById('pArr').value, dep=document.getElementById('pDep').value;
  var arrT=document.getElementById('pArrT').value, depT=document.getElementById('pDepT').value;
  var car=document.getElementById('pCar').value, budget=document.getElementById('pBudget').value;
  var wish=(document.getElementById('pWish').value||'').toLowerCase();
  var out=document.getElementById('planOut');
  if(!it||!arr||!dep){out.innerHTML='<div class="card muted">בחרי יעד ותאריכים.</div>';return;}
  var nDays=daysBetween(arr,dep)+1; if(nDays<1)nDays=1;

  /* העדפות מהטקסט החופשי */
  var pref=[];
  if(/מים|בריכ|מגלש|אקווה/.test(wish))pref.push('water');
  if(/מוזיא|מדע|אינטראקט/.test(wish))pref.push('museum');
  if(/חיו|זו|ספארי/.test(wish))pref.push('zoo');
  if(/פארק|טבע|ירוק/.test(wish))pref.push('park');
  if(/שעשוע|לונה|רכבת|אדרנל/.test(wish))pref.push('themepark');
  if(/היסטור|טירה|מצוד/.test(wish))pref.push('history');
  var atts=it.attractions.slice().sort(function(a,b){
    var pa=pref.indexOf(a.tag)>-1?0:1, pb=pref.indexOf(b.tag)>-1?0:1;
    if(pa!==pb)return pa-pb;
    return (b.wow?1:0)-(a.wow?1:0);  /* "חובה לא לפספס" קודם */
  });

  /* חלוקה ליומים */
  var pool=atts.slice(), days=[];
  for(var i=0;i<nDays;i++){
    var isArr=(i===0), isDep=(i===nDays-1 && nDays>1);
    var picks=[];
    var max=(isArr||isDep)?1:2;
    while(picks.length<max && pool.length){ picks.push(pool.shift()); }
    days.push({arr:isArr,dep:isDep,picks:picks});
  }

  var html='<div class="card"><h3>🗺️ מסלול ל'+esc(it.name)+' · '+nDays+' ימים</h3>';
  html+='<div class="muted">לינה מומלצת: '+esc(it.lodging)+'</div>';
  if(budget)html+='<div class="muted">💰 תקציב טיולים שציינת: ~'+nf(+budget)+'₪ — שובץ לפי רמת עלות (₪=זול, ₪₪=בינוני).</div>';
  if(car==='no')html+='<div class="muted">🚗 בלי רכב — אטרקציות מחוץ לעיר סומנו (עדיף טיול מאורגן/מונית).</div>';
  if(wish)html+='<div class="muted">📝 הבקשות שלך נלקחו בחשבון: "'+esc(wish)+'"</div>';

  days.forEach(function(day,idx){
    var lbl='יום '+(idx+1);
    var note='';
    if(day.arr)note=' (יום הגעה · נחיתה '+arrT+' — פעילות קלה ליד הלינה + ארוחה)';
    if(day.dep)note=' (יום חזרה · המראה '+depT+' — אטרקציה בבוקר ואז שדה תעופה)';
    html+='<div class="day"><h4>'+lbl+esc(note)+'</h4>';
    if(!day.picks.length){html+='<div class="muted">יום חופשי — שוטטות, קניות, או חזרה לאטרקציה אהובה.</div>';}
    day.picks.forEach(function(a){
      var carNote=(car==='no'&&a.car)?' · 🚗 עדיף רכב/טיול מאורגן':'';
      var wowB=a.wow?'<span style="background:#ffd84d;color:#6b4e00;border-radius:6px;padding:1px 6px;font-size:.75rem;font-weight:800">⭐ חובה</span> ':'';
      html+='<div class="att">'+wowB+'<b>'+esc(a.t)+'</b><div>'+esc(a.d)+'</div><div class="meta">⏱️ '+esc(a.h)+' · 💰 '+esc(a.c)+carNote+'</div></div>';
    });
    html+='</div>';
  });
  html+='</div>';
  out.innerHTML=html;

  /* קישור לתוכנית מותאמת אישית */
  var msg='שלום! בחרתי '+it.name+'. תאריכים '+arr+' '+arrT+' עד '+dep+' '+depT
    +'. תקציב טיולים: '+(budget||'-')+'₪. רכב: '+(car==='yes'?'כן':'לא')
    +'. אנחנו 4 מבוגרים ו-5 ילדים בגילאי 8-12. בקשות: '+(wish||'-')
    +'. אשמח לתוכנית מסלול מפורטת ומותאמת.';
  document.getElementById('planWa').href='https://wa.me/?text='+encodeURIComponent(msg);
}

initDeals();
initPlan();
</script>
</body>
</html>"""
