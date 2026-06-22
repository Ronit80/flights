"""
נקודת הכניסה שרצה בענן (GitHub Actions) כל בוקר:
מחפש טיסות, בונה public/index.html (הדף שמתפרסם), ושולח מייל אם הוגדר.
המפתחות הרגישים מגיעים ממשתני סביבה (GitHub Secrets) — לא מהקוד.
"""
import json
import os
import sys
from datetime import datetime

from flights import find_best
from report import build_html, build_summary_text

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    with open(os.path.join(HERE, "config.json"), encoding="utf-8") as f:
        cfg = json.load(f)

    token = os.environ.get("TRAVELPAYOUTS_TOKEN") or cfg.get("travelpayouts", {}).get("token")
    if not token:
        sys.exit("חסר TRAVELPAYOUTS_TOKEN (הגדירי אותו ב-GitHub Secrets).")
    cfg["travelpayouts"] = {"token": token}

    today = datetime.now().strftime("%d/%m/%Y")
    print(f"[{today}] מחפש טיסות...")
    results, _ = find_best(cfg)

    html = build_html(results, today)
    out_dir = os.path.join(HERE, "public")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ נוצר public/index.html")

    for d in results:
        if d["offers"]:
            o = d["offers"][0]
            print(f"  {d['name']}: ~{o['total']:,} | {o['dep_date']} {o['dep_time']}→{o['ret_date']} {o['ret_time']}")
        else:
            print(f"  {d['name']}: אין עדיין מחיר")

    # מייל אופציונלי — נשלח רק אם הוגדרה סיסמת אפליקציה ב-Secrets
    pw = os.environ.get("GMAIL_APP_PASSWORD")
    if pw:
        from email_send import send_email
        sender = os.environ.get("EMAIL_SENDER", "")
        recips = [r.strip() for r in os.environ.get("EMAIL_RECIPIENTS", "").split(",") if r.strip()]
        recips = recips or [sender]
        try:
            send_email(
                {"smtp_host": "smtp.gmail.com", "smtp_port": 465, "sender": sender,
                 "app_password": pw, "recipients": recips},
                f"✈️ סוכן הטיסות — דילים ל-{today}",
                html, build_summary_text(results, today),
            )
            print(f"✅ מייל נשלח ל-{len(recips)} נמענים")
        except Exception as e:
            print(f"❌ מייל נכשל: {e}")
    else:
        print("ℹ️ מייל לא הוגדר (לא חובה) — מדלג.")


if __name__ == "__main__":
    main()
