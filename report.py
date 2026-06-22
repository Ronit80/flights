"""בניית דוח HTML יפה + טקסט לשיתוף בוואטסאפ.
מציג את N הדילים הזולים ביותר, ממוינים מהזול ליקר, כולל מזג אוויר צפוי."""
import html as _html
import urllib.parse

TOP_N = 7

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


def flatten_top(results, limit=TOP_N):
    """כל הדילים מכל היעדים, ממוין מהזול ליקר, top N (עם שם וקוד יעד)."""
    flat = []
    for d in results:
        for o in d.get("offers", []):
            flat.append({**o, "dest": d["name"], "code": d["code"]})
    flat.sort(key=lambda x: x["total"])
    return flat[:limit]


def empty_dests(results):
    return [d["name"] for d in results if not d.get("offers")]


# --- דירוג משולב: זול + יבש ---
RAIN_WEIGHT = 0.5  # כמה מזג האוויר משפיע (0=מחיר בלבד, 1=השפעה חזקה)


def _rain_ratio(o):
    w = o.get("weather")
    if w and w.get("days"):
        return w["rainy_days"] / max(w["days"], 1)
    return 0.20  # ברירת מחדל ניטרלית כשאין נתון מזג אוויר


def combined_score(o):
    """ציון נמוך = טוב יותר. כל יחס גשם מייקר את הדיל באופן יחסי."""
    return o["total"] * (1 + RAIN_WEIGHT * _rain_ratio(o))


def rank_combined(deals, top_n=TOP_N):
    return sorted(deals, key=combined_score)[:top_n]


def _weather_bits(w):
    """מחזיר (אימוג'י, תיאור, שורת מזג אוויר) מתוך נתוני האקלים."""
    if not w:
        return "", ""
    days = max(w.get("days", 0), 1)
    ratio = w["rainy_days"] / days
    if ratio <= 0.15:
        tag = "☀️ מעט גשם"
    elif ratio <= 0.35:
        tag = "⛅ גשם מתון"
    else:
        tag = "🌧️ גשום יחסית"
    line = (f"🌡️ ~{w['tmax']}°/{w['tmin']}° · {tag} "
            f"(~{w['rainy_days']} ימי גשם צפויים מתוך {days})")
    return tag, line


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


def _deal_card(o, rank):
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣"]
    medal = medals[rank] if rank < len(medals) else f"{rank+1}."
    booking = _html.escape(o["link"])
    cur = o["currency"]
    _, weather_line = _weather_bits(o.get("weather"))
    weather_html = f'<div class="weather">{weather_line}</div>' if weather_line else ""
    return f"""
      <div class="deal">
        <div class="deal-top">
          <span class="rank">{medal}</span>
          <span class="dest">{_html.escape(o['dest'])}</span>
        </div>
        <div class="prices">
          <div class="p1">🎫 מחיר לכרטיס אחד: <b>~{o['per_person']:,} {cur}</b></div>
          <div class="p9">👨‍👩‍👧‍👦 סה"כ ל-9 נוסעים: <b>~{o['total']:,} {cur}</b></div>
        </div>
        <div class="route">
          <span>🛫 {o['dep_date']} · {o['dep_time']}</span>
          <span class="arrow">→</span>
          <span>🛬 {o['ret_date']} · {o['ret_time']}</span>
          <span class="nights">{o['nights']} לילות</span>
        </div>
        {weather_html}
        <div class="airline">🏢 {_html.escape(o['airline'])} · טיסה ישירה</div>
        <div class="bag">🧳 {_bag(o['airline'])}</div>
        <a class="btn book" href="{booking}" target="_blank">להזמנה ולמחיר מדויק ➜</a>
      </div>"""


def build_html(deals, empties, today):
    summary = build_summary_text(deals, today)
    wa = _html.escape(wa_share_link(summary))

    if deals:
        cards = "".join(_deal_card(o, i) for i, o in enumerate(deals))
        body = f'<section class="list"><h2>{len(deals)} הדילים הכי משתלמים (שילוב מחיר נמוך + מעט גשם)</h2>{cards}</section>'
    else:
        body = """<section class="list"><p class="none">
          עדיין אין מחירים שמורים לתאריכים שלך (רחוק מהיום).
          הדף בודק כל בוקר ויציג דילים ברגע שיופיעו ✓</p></section>"""

    pending = ""
    if empties:
        pending = ('<p class="pending">⏳ עדיין ממתינים למחירים: '
                   + _html.escape("، ".join(empties)) + " (יתמלאו ככל שמתקרבים לתאריך)</p>")

    return f"""<!doctype html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>סוכן הטיסות המשפחתי — {today}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f0f4f8; color: #1a2b3c; padding: 16px; }}
  .wrap {{ max-width: 680px; margin: 0 auto; }}
  header {{ background: linear-gradient(135deg, #1e6091, #168aad); color: #fff;
           border-radius: 18px; padding: 24px; text-align: center; box-shadow: 0 6px 20px rgba(0,0,0,.12); }}
  header h1 {{ font-size: 1.5rem; }}
  header p {{ opacity: .92; margin-top: 6px; font-size: .9rem; }}
  .share {{ display: flex; gap: 10px; margin: 16px 0; }}
  .share a {{ flex: 1; text-align: center; padding: 13px; border-radius: 12px; text-decoration: none;
             font-weight: 700; color: #fff; }}
  .wa {{ background: #25d366; }}
  .list {{ background: #fff; border-radius: 16px; padding: 18px; box-shadow: 0 3px 12px rgba(0,0,0,.06); }}
  .list > h2 {{ font-size: 1.15rem; margin-bottom: 12px; color: #1e6091; }}
  .list .none {{ color: #7a8a99; font-size: .92rem; }}
  .deal {{ border: 1px solid #e3ebf2; border-radius: 12px; padding: 14px; margin-top: 12px; }}
  .deal-top {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }}
  .rank {{ font-size: 1.3rem; }}
  .deal-top .dest {{ font-size: 1.2rem; font-weight: 800; }}
  .prices {{ background: #f4f9fc; border-radius: 10px; padding: 10px 12px; margin: 8px 0; }}
  .prices .p1 {{ font-size: .95rem; color: #50606f; }}
  .prices .p9 {{ font-size: 1.2rem; color: #1e6091; margin-top: 2px; }}
  .prices b {{ font-weight: 800; }}
  .route {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 8px 0; font-size: .92rem; }}
  .route .arrow {{ color: #168aad; font-weight: 700; }}
  .route .nights {{ background: #e8f3f8; color: #1e6091; padding: 2px 8px; border-radius: 8px; font-size: .82rem; }}
  .weather {{ background: #fff7e6; border-radius: 8px; padding: 7px 10px; font-size: .9rem; color: #6b5a2e; margin: 6px 0; }}
  .airline {{ color: #50606f; font-size: .9rem; margin-bottom: 4px; }}
  .bag {{ font-size: .88rem; color: #50606f; margin-bottom: 10px; }}
  .btn {{ display: block; text-align: center; padding: 11px; border-radius: 10px;
         text-decoration: none; font-weight: 700; }}
  .book {{ background: #168aad; color: #fff; }}
  .pending {{ color: #8a99a8; font-size: .85rem; margin-top: 14px; text-align: center; }}
  footer {{ text-align: center; color: #8a99a8; font-size: .8rem; margin: 18px 0; line-height: 1.6; }}
</style>
</head>
<body>
  <div class="wrap">
    <header>
      <h1>✈️ סוכן הטיסות המשפחתי</h1>
      <p>מזרח אירופה · טיסה ישירה · הלוך 10-15, חזור ערב · 4 מבוגרים + 5 ילדים</p>
      <p>עודכן: {today}</p>
    </header>

    <div class="share">
      <a class="wa" href="{wa}" target="_blank">📲 שתפו בוואטסאפ</a>
    </div>

    {body}
    {pending}

    <footer>
      המחירים אומדן (מחיר נוסע ×9) ממאגר Aviasales — לחצו "להזמנה" למחיר סופי ולבדיקת מזוודה.<br>
      מזג האוויר הוא ממוצע אקלימי מ-5 השנים האחרונות (הערכה, לא תחזית). · הופק אוטומטית 🤖
    </footer>
  </div>
</body>
</html>"""
