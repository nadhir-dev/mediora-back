from src.config.env import env
from src.config.env import production
from src.schemas.users import Email

from fastapi_mail import (
    ConnectionConfig,
)


if production:

    conf = ConnectionConfig(
        MAIL_USERNAME=env.spacemail_username,
        MAIL_PASSWORD=env.spacemail_password,  # type: ignore
        MAIL_FROM="Your App <noreply@nadhirdev.com>",
        MAIL_PORT=env.spacemail_port,
        MAIL_SERVER=env.spacemail_host,
        MAIL_FROM_NAME="Mediora",
        MAIL_STARTTLS=True,
        MAIL_SSL_TLS=False,
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True,
    )
else:
    conf = ConnectionConfig(
        MAIL_USERNAME=env.mailtrap_username,
        MAIL_PASSWORD=env.mailtrap_password,  # type: ignore
        MAIL_FROM="Mediora@company.com",
        MAIL_PORT=env.mailtrap_port,
        MAIL_SERVER=env.mailtrap_host,
        MAIL_FROM_NAME="Mediora",
        MAIL_STARTTLS=True,
        MAIL_SSL_TLS=False,
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True,
    )

import httpx


async def send_mail(
    *,
    receiver: str,
    subject: str,
    msg_plain: str,
    msg_html: str | None = None,
):
    url = "https://api.resend.com/emails"

    headers = {
        "Authorization": f"Bearer {env.resend_api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "from": "Mediora <onboarding@nadhirdev.com>",
        "to": [receiver],
        "subject": subject,
        "html": msg_html,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)


async def send_password_reset_token_email(email: str, token: str) -> None:

    subject = "your password reset"
    link = f"{token}"

    msg_html = f"""<h2>Password Reset Request</h2>
<p>Hello,</p>
<p>We received a request to reset the password for your account.</p>
<p><b>Your password reset code is:</b></p>
<h1 style="letter-spacing: 4px;">{link}</h1>
<p>This code will expire in <b>15 minutes</b>.</p>
<p>If you did not request a password reset, you can safely ignore this account.</p>
<hr />
"""
    msg_plain = f"""Password Reset Request
Hello,
We received a request to reset the password for your account.
Your password reset code is: {link}
This code will expire in 15 minutes.
If you did not request a password reset, you can safely ignore this account.
"""

    await send_mail(receiver=email, subject=subject, msg_plain=msg_plain, msg_html=msg_html)  # type: ignore


async def send_email_verification_otp_code(email: Email, code: str) -> None:
    subject = f"Verify your email for Mediora"
    link = f"{env.url}/auth/verify-email{code}"
    msg_html = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Verify your email</title>
  </head>
  <body style="margin:0;padding:0;background:#f6f7fb;font-family:Arial,Helvetica,sans-serif;">
    <div style="max-width:560px;margin:0 auto;padding:24px;">
      <div style="background:#ffffff;border-radius:12px;padding:24px;box-shadow:0 2px 10px rgba(0,0,0,.06);">
        <h2 style="margin:0 0 12px;font-size:20px;color:#111827;">
          Verify your email
        </h2>

        <p style="margin:0 0 16px;font-size:14px;line-height:20px;color:#374151;">
   
          Use the code below to verify your email for <strong>Mediora</strong>.
        </p>

        <div style="margin:18px 0 18px;padding:14px 16px;border:1px solid #e5e7eb;border-radius:10px;background:#f9fafb;">
          <div style="font-size:12px;color:#6b7280;margin-bottom:6px;">Verification code</div>
          <div style="font-size:26px;letter-spacing:6px;font-weight:700;color:#111827;">
            {code}
          </div>
        </div>

        <p style="margin:0 0 16px;font-size:14px;line-height:20px;color:#374151;">
          This code expires in <strong>{10} minutes</strong>.
        </p>

        <p style="margin:0;font-size:13px;line-height:18px;color:#6b7280;">
          If you didn’t request this, you can safely ignore this email.
        </p>

        <hr style="border:none;border-top:1px solid #e5e7eb;margin:20px 0;" />

        <p style="margin:0;font-size:12px;line-height:16px;color:#9ca3af;">
          — Mediora Team
        </p>
      </div>
    </div>
  </body>
</html>
"""
    msg_plain = f"""Hi ,

Your verification code for Mediora is: {code}

Or you can directly go to: {link}

This code expires in {15} minutes.

If you didn’t request this, you can ignore this email.

— Mediora Team
"""
    await send_mail(
        receiver=email, subject=subject, msg_html=msg_html, msg_plain=msg_plain
    )
