"""Outbound mail via plain SMTP (stdlib smtplib).

Chosen over SendGrid/Mailgun because it needs no third-party account or SDK:
any provider (Google Workspace app password, campus relay, Mailgun's own SMTP
endpoint) plugs into the same four env vars. When SMTP is not configured the
mailer logs the message to the app logger instead of failing, so dev and
seeded demos run keyless.
"""
import smtplib
from email.message import EmailMessage

from flask import current_app


def send_email(to_address, subject, body):
    """Returns True if handed to an SMTP server, False if logged-only."""
    host = current_app.config.get("SMTP_HOST")
    if not host:
        current_app.logger.warning(
            "SMTP not configured — email NOT sent.\nTo: %s\nSubject: %s\n%s",
            to_address, subject, body,
        )
        return False

    msg = EmailMessage()
    msg["From"] = current_app.config["MAIL_FROM"]
    msg["To"] = to_address
    msg["Subject"] = subject
    msg.set_content(body)

    port = int(current_app.config.get("SMTP_PORT") or 587)
    with smtplib.SMTP(host, port, timeout=15) as smtp:
        smtp.starttls()
        username = current_app.config.get("SMTP_USERNAME")
        if username:
            smtp.login(username, current_app.config.get("SMTP_PASSWORD") or "")
        smtp.send_message(msg)
    return True


def send_verification_email(to_address, verify_url):
    body = (
        "Welcome to Campus Crosswalk!\n\n"
        "Confirm your campus email to activate your account:\n\n"
        f"    {verify_url}\n\n"
        "The link expires in 24 hours. If you didn't sign up, ignore this email."
    )
    return send_email(to_address, "Verify your Campus Crosswalk account", body)
