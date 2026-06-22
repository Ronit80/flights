"""בניית דוח HTML יפה + טקסט לשיתוף בוואטסאפ."""
import html as _html
import urllib.parse


def build_summary_text(results, today):
    """טקסט קצר לשיתוף מהיר בוואטסאפ."""
    lines = [f"✈️ טיסות משפחתיות זולות — {today}", "(טיסה ישירה, 4 מבוגרים + 5 ילדים)", ""]
    found = False
    for d in results:
        if d["offers"]:
            found = True
            o = d["offers"][0]
            lines.append(
                f"📍 {d['name']}: ~{o['total']:,}₪ למשפחה | "
                f"{o['dep_date']} {o['dep_time']} → {o['ret_date']} {o['ret_time']} | {o['airline']}"
            )
    if not found:
        lines.append("עדיין אין מחירים לתאריכים — נמשיך לבדוק כל יום.")
    lines.append("")
    lines.append("הופק אוטומטית ע\"י סוכן הטיסות 🤖")
    return "\n".join(lines)


def wa_share_link(text):
    return "https://wa.me/?text=" + urllib.parse.quote(text)


def _deal_card(o):
    booking = _html.escape(o["link"])
    return f"""
      <div class="deal">
        <div class="price">~{o['total']:,} <span>{o['currency']}</span>
          <small>למשפחה · ~{o['per_person']:,}/נוסע</small></div>
        <div class="route">
          <span>🛫 {o['dep_date']} · {o['dep_time']}</span>
          <span class="arrow">→</span>
          <span>🛬 {o['ret_date']} · {o['ret_time']}</span>
          <span class="nights">{o['nights']} לילות</span>
        </div>
        <div class="airline">🏢 {_html.escape(o['airline'])} · טיסה ישירה</div>
        <a class="btn book" href="{booking}" target="_blank">להזמנה ולמחיר מדויק ➜</a>
      </div>"""


def _dest_block(d, rank):
    medals = ["🥇", "🥈", "🥉", "🏅", "🏅"]
    medal = medals[rank] if rank < len(medals) else "📍"
    if not d["offers"]:
        return f"""
      <section class="dest empty">
        <h2>{medal} {_html.escape(d['name'])}</h2>
        <p class="none">עדיין אין מחירים שמורים לתאריכים שלך (רחוק מהיום). נתפוס ברגע שיופיעו ✓</p>
      </section>"""
    cards = "".join(_deal_card(o) for o in d["offers"])
    return f"""
      <section class="dest">
        <h2>{medal} {_html.escape(d['name'])}</h2>
        {cards}
      </section>"""


def build_html(results, today):
    summary = build_summary_text(results, today)
    wa = _html.escape(wa_share_link(summary))
    blocks = "".join(_dest_block(d, i) for i, d in enumerate(results))

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
  .dest {{ background: #fff; border-radius: 16px; padding: 18px; margin-bottom: 14px;
          box-shadow: 0 3px 12px rgba(0,0,0,.06); }}
  .dest h2 {{ font-size: 1.2rem; margin-bottom: 12px; }}
  .dest.empty .none {{ color: #7a8a99; font-size: .92rem; }}
  .deal {{ border: 1px solid #e3ebf2; border-radius: 12px; padding: 14px; margin-top: 10px; }}
  .price {{ font-size: 1.7rem; font-weight: 800; color: #1e6091; }}
  .price span {{ font-size: 1rem; }}
  .price small {{ display: block; font-size: .8rem; color: #7a8a99; font-weight: 400; }}
  .route {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 10px 0; font-size: .92rem; }}
  .route .arrow {{ color: #168aad; font-weight: 700; }}
  .route .nights {{ background: #e8f3f8; color: #1e6091; padding: 2px 8px; border-radius: 8px; font-size: .82rem; }}
  .airline {{ color: #50606f; font-size: .9rem; margin-bottom: 10px; }}
  .btn {{ display: block; text-align: center; padding: 11px; border-radius: 10px;
         text-decoration: none; font-weight: 700; }}
  .book {{ background: #168aad; color: #fff; }}
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

    {blocks}

    <footer>
      המחירים אומדן (מחיר נוסע ×9) ממאגר Aviasales — לחצו "להזמנה" למחיר סופי ולבדיקת מזוודה.<br>
      מזוודה לא תמיד כלולה (במיוחד Wizz/מחיר Light). · הופק אוטומטית 🤖
    </footer>
  </div>
</body>
</html>"""
