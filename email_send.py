"""שליחת המייל היומי (גוף HTML) דרך SMTP — למשל Gmail."""
import smtplib
import ssl
from email.message import EmailMessage


def send_email(email_cfg, subject, html_body, plain_fallback):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = email_cfg["sender"]
    recipients = email_cfg["recipients"]
    msg["To"] = ", ".join(recipients)
    msg.set_content(plain_fallback)
    msg.add_alternative(html_body, subtype="html")

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(email_cfg["smtp_host"], int(email_cfg["smtp_port"]), context=ctx) as srv:
        srv.login(email_cfg["sender"], email_cfg["app_password"])
        srv.send_message(msg)
    return len(recipients)
