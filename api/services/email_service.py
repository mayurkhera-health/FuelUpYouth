"""
Best-effort transactional email via Gmail SMTP (stdlib smtplib — no extra deps).

Reads GMAIL_USER / GMAIL_APP_PASSWORD from the environment (Fly secrets). When
either is missing the send is skipped and False is returned, so callers MUST
treat email as best-effort: the primary work (e.g. persisting a report) must
never depend on, or block on, the result of send_email().
"""

import os
import ssl
import smtplib
import logging
from email.message import EmailMessage

logger = logging.getLogger(__name__)

_SMTP_HOST = "smtp.gmail.com"
_SMTP_PORT = 465  # implicit TLS (SMTP_SSL)


def send_email(subject: str, body: str, to: list[str], attachment_path: str | None = None) -> bool:
    """
    Send a plaintext email to `to`, optionally with an image attached.

    `attachment_path` — when provided and readable, the file is attached as an
    image (the body stays plain text). A missing/unreadable attachment is logged
    and the email is still sent without it. Returns True on success, False
    otherwise. Never raises — delivery is best-effort and must not break the caller.
    """
    user = os.getenv("GMAIL_USER")
    password = os.getenv("GMAIL_APP_PASSWORD")
    if not user or not password:
        logger.warning("send_email skipped: GMAIL_USER/GMAIL_APP_PASSWORD not configured")
        return False
    if not to:
        return False

    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = user
        msg["To"] = ", ".join(to)
        msg.set_content(body)

        if attachment_path:
            try:
                with open(attachment_path, "rb") as f:
                    data = f.read()
                ext = os.path.splitext(attachment_path)[1].lstrip(".").lower() or "jpg"
                subtype = "jpeg" if ext in ("jpg", "jpeg") else ext
                # add_attachment builds a multipart/mixed message with the image
                # part — the EmailMessage equivalent of MIMEMultipart + MIMEImage.
                msg.add_attachment(
                    data, maintype="image", subtype=subtype,
                    filename=os.path.basename(attachment_path),
                )
            except Exception:
                logger.exception("attachment read failed; sending email without it")

        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(_SMTP_HOST, _SMTP_PORT, context=ctx, timeout=15) as server:
            server.login(user, password)
            server.send_message(msg)
        return True
    except Exception:
        logger.exception("send_email failed")
        return False
