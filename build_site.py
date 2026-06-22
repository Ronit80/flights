# -*- coding: utf-8 -*-
"""
רץ בענן (GitHub Actions) כל בוקר:
- מחפש טיסות לכל היעדים בכל החלון
- מחשב אקלים חודשי לכל יעד
- בונה public/index.html = אפליקציה אינטראקטיבית (2 טאבים)
- שולח מייל יומי עם 7 הדילים הכי משתלמים (זול + פחות גשם)
המפתחות מגיעים ממשתני סביבה (GitHub Secrets).
"""
import json
import os
import sys
from datetime import datetime, timedelta

from flights import find_best
from weather import monthly_climate
from fx import get_rates
from itinerary import ITIN
from report import (build_app_html, build_email_html, build_summary_text,
                    flatten_all, flatten_top, empty_dests,
                    estimate_weather, rank_combined, TOP_N)

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    with open(os.path.join(HERE, "config.json"), encoding="utf-8") as f:
        cfg = json.load(f)

    token = os.environ.get("TRAVELPAYOUTS_TOKEN") or cfg.get("travelpayouts", {}).get("token")
    if not token:
        sys.exit("חסר TRAVELPAYOUTS_TOKEN (הגדירי אותו ב-GitHub Secrets).")
    cfg["travelpayouts"] = {"token": token}

    # חותמת זמן בשעון ישראל (UTC+3, קיץ) — יום + dd/mm/yy + שעה
    now_il = datetime.utcnow() + timedelta(hours=3)
    _dow = {0: "ב׳", 1: "ג׳", 2: "ד׳", 3: "ה׳", 4: "ו׳", 5: "שבת", 6: "א׳"}
    today = f"יום {_dow[now_il.weekday()]} {now_il.strftime('%d/%m/%y %H:%M')}"
    print(f"[{today}] מחפש טיסות...")
    results, _ = find_best(cfg)

    dests = cfg["search"]["destinations"]
    all_deals = flatten_all(results)
    print(f"נמצאו {len(all_deals)} דילים ישירים בסך הכל.")

    # אקלים חודשי לכל יעד (מאפשר סינון ודירוג מזג אוויר בדפדפן)
    print("מחשב אקלים חודשי...")
    climate = {d["code"]: monthly_climate(d["code"]) for d in dests}

    fx = get_rates()
    print(f"שערי חליפין: 1 ILS = ${fx['USD']} / €{fx['EUR']}")

    # 1) אפליקציה אינטראקטיבית -> public/index.html
    app_html = build_app_html(all_deals, climate, dests, ITIN, today, fx)
    out_dir = os.path.join(HERE, "public")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(app_html)
    print("✅ נוצר public/index.html (אפליקציה)")

    # 2) למייל: 7 הכי משתלמים (זול + פחות גשם)
    candidates = flatten_top(results, max(15, cfg["search"].get("top_results", TOP_N) * 2))
    for c in candidates:
        c["weather"] = estimate_weather(c, climate)
    top = rank_combined(candidates, cfg["search"].get("top_results", TOP_N))
    for o in top:
        print(f"  {o['dest']}: ~{o['total']:,} | {o['dep_date']}→{o['ret_date']}")

    pw = os.environ.get("GMAIL_APP_PASSWORD")
    send_email_now = os.environ.get("SEND_EMAIL", "true").lower() == "true"
    if pw and not send_email_now:
        print("ℹ️ ריצת רענון (לא 8:00) — מדלג על מייל, הדף עודכן.")
    elif pw:
        from email_send import send_email
        sender = os.environ.get("EMAIL_SENDER", "")
        recips = [r.strip() for r in os.environ.get("EMAIL_RECIPIENTS", "").split(",") if r.strip()] or [sender]
        try:
            send_email(
                {"smtp_host": "smtp.gmail.com", "smtp_port": 465, "sender": sender,
                 "app_password": pw, "recipients": recips},
                f"✈️ סוכן הטיסות — דילים ל-{today}",
                build_email_html(top, empty_dests(results), today, fx),
                build_summary_text(top, today),
            )
            print(f"✅ מייל נשלח ל-{len(recips)} נמענים")
        except Exception as e:
            print(f"❌ מייל נכשל: {e}")
    else:
        print("ℹ️ מייל לא הוגדר — מדלג.")


if __name__ == "__main__":
    main()
