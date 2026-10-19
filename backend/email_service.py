"""
email_service.py - CineWise Password Recovery Email Service
===========================================================
Handles sending password recovery emails via SMTP, with a documented
development fallback mode when SMTP credentials are not configured.

Environment Variables:
  SMTP_HOST     : Hostname of the SMTP server (e.g., smtp.gmail.com, smtp.sendgrid.net)
  SMTP_PORT     : SMTP port (default: 587 for STARTTLS, 465 for SSL)
  SMTP_USER     : SMTP account username / email address
  SMTP_PASS     : SMTP password or app-specific password
  SMTP_FROM     : Sender email address (default: CineWise <noreply@cinewise.app>)
  APP_URL       : Base URL of the CineWise frontend (default: http://localhost:5173)
"""

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger("cinewise.email")


def is_smtp_configured() -> bool:
    """Check if valid SMTP configuration is provided in the environment."""
    host = os.environ.get("SMTP_HOST", "").strip()
    user = os.environ.get("SMTP_USER", "").strip()
    pwd = os.environ.get("SMTP_PASS", "").strip()
    return bool(host and user and pwd)


def get_app_url() -> str:
    """Get the CineWise application frontend URL."""
    return os.environ.get("APP_URL", "http://localhost:5173").rstrip("/")


def send_password_reset_email(to_email: str, user_name: str, raw_token: str) -> dict:
    """
    Send a secure password reset email with a 15-minute token.

    Parameters
    ----------
    to_email : str
        Recipient email address.
    user_name : str
        Recipient user's display name.
    raw_token : str
        Cryptographically secure single-use reset token.

    Returns
    -------
    dict
        Status containing delivery information or development testing mode details.
    """
    app_url = get_app_url()
    reset_url = f"{app_url}/?page=reset-password&token={raw_token}"
    display_name = user_name or "Film Lover"

    if not is_smtp_configured():
        logger.info(
            f"[CineWise Auth] SMTP credentials not set. Running in development test mode for: {to_email}"
        )
        return {
            "sent": False,
            "mode": "development",
            "message": "SMTP is not configured on the server. Development test mode active.",
            "dev_reset_url": reset_url,
            "instructions": "Configure SMTP_HOST, SMTP_PORT, SMTP_USER, and SMTP_PASS in .env for production email delivery.",
        }

    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")
    smtp_from = os.environ.get("SMTP_FROM", f"CineWise <{smtp_user}>")

    # Construct HTML and Plain-text message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Reset Your CineWise Password"
    msg["From"] = smtp_from
    msg["To"] = to_email

    text_body = f"""Hello {display_name},

We received a request to reset your password for your CineWise account.
Click the link below or copy and paste it into your browser:

{reset_url}

This link is valid for 15 minutes and can only be used once.
If you did not make this request, you can safely ignore this email. Your password remains unchanged.

Warm regards,
The CineWise Team
AI-Powered Movie Discovery & Recommendation Platform
"""

    html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Reset Your CineWise Password</title>
</head>
<body style="margin:0;padding:0;background-color:#13131a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#f0f0f5;">
  <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color:#13131a;padding:40px 10px;">
    <tr>
      <td align="center">
        <table width="560" border="0" cellspacing="0" cellpadding="0" style="background-color:#1c1c24;border-radius:12px;border:1px solid #2d2d3a;overflow:hidden;box-shadow:0 8px 30px rgba(0,0,0,0.5);">
          <!-- Header -->
          <tr>
            <td style="padding:32px 40px;background:linear-gradient(135deg, #1c1c24 0%, #252533 100%);border-bottom:1px solid #2d2d3a;text-align:center;">
              <div style="font-size:26px;font-weight:700;color:#e8b84b;letter-spacing:0.5px;">
                Cine<span style="color:#ffffff;">Wise</span>
              </div>
              <div style="font-size:12px;color:#a0a0b8;letter-spacing:1px;text-transform:uppercase;margin-top:4px;">
                AI-Powered Movie Discovery &amp; Recommendation Platform
              </div>
            </td>
          </tr>
          <!-- Body -->
          <tr>
            <td style="padding:40px;">
              <h2 style="margin:0 0 16px 0;font-size:20px;font-weight:600;color:#ffffff;">
                Password Reset Request
              </h2>
              <p style="margin:0 0 16px 0;font-size:15px;line-height:1.6;color:#c0c0d0;">
                Hello <strong>{display_name}</strong>,
              </p>
              <p style="margin:0 0 24px 0;font-size:14px;line-height:1.6;color:#a0a0b8;">
                We received a request to reset your CineWise account password. Click the button below to choose a new password:
              </p>
              <div style="text-align:center;margin:32px 0;">
                <a href="{reset_url}" target="_blank" style="display:inline-block;padding:14px 32px;background:#e8b84b;color:#13131a;font-weight:700;font-size:15px;text-decoration:none;border-radius:6px;box-shadow:0 4px 14px rgba(232,184,75,0.35);">
                  Reset Password
                </a>
              </div>
              <p style="margin:24px 0 8px 0;font-size:12px;line-height:1.6;color:#808095;">
                Or paste this link into your browser:
              </p>
              <p style="margin:0 0 24px 0;font-size:12px;word-break:break-all;color:#e8b84b;background:#15151e;padding:10px 14px;border-radius:4px;border:1px solid #252535;">
                {reset_url}
              </p>
              <div style="margin-top:32px;padding-top:20px;border-top:1px solid #262635;font-size:12px;color:#707085;line-height:1.6;">
                <strong>Security note:</strong> This reset link expires in <strong>15 minutes</strong> and can only be used once. If you did not request a password reset, no action is required and your account remains safe.
              </div>
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td style="padding:20px 40px;background-color:#15151e;text-align:center;font-size:11px;color:#606075;border-top:1px solid #20202d;">
              &copy; CineWise · Content-Based AI Movie Discovery
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            server.ehlo()
            server.starttls()
            server.ehlo()

        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_from, [to_email], msg.as_string())
        server.quit()
        logger.info(f"[CineWise Auth] Password reset email delivered successfully to: {to_email}")
        return {"sent": True, "mode": "smtp", "message": "Password reset email delivered successfully."}
    except Exception as e:
        logger.error(f"[CineWise Auth] Failed to deliver SMTP reset email: {e}")
        return {
            "sent": False,
            "mode": "smtp_error",
            "error": str(e),
            "message": "Failed to send reset email due to SMTP server error.",
            "dev_reset_url": reset_url,  # fallback for testing
        }
