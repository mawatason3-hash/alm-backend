import aiosmtplib
import os
import random
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

GMAIL_USER = os.environ.get("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.environ.get(
    "GMAIL_APP_PASSWORD", ""
)


def is_email_configured() -> bool:
    return bool(GMAIL_USER and GMAIL_APP_PASSWORD)


async def send_otp_email(
    to_email: str,
    voter_name: str,
    otp_code: str
) -> bool:
    try:
        print(f"Attempting to send OTP to: {to_email}")
        print(f"Gmail user: {GMAIL_USER}")
        print(f"Password set: {bool(GMAIL_APP_PASSWORD)}")

        if not GMAIL_USER or not GMAIL_APP_PASSWORD:
            print("ERROR: Gmail credentials not set")
            return False

        message = MIMEMultipart("alternative")
        message["Subject"] = f"Your ALM Voting Code: {otp_code}"
        message["From"] = f"ALM Voting System <{GMAIL_USER}>"
        message["To"] = to_email

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family:Arial,sans-serif;
                     background:#f5f5f5;padding:40px;">
          <div style="max-width:500px;margin:0 auto;
                      background:#fff;
                      border-radius:12px;
                      padding:40px;
                      text-align:center;">
            <h2 style="color:#1a1a2e;">
              ALM Voting System
            </h2>
            <p style="color:#555;">
              Association of Liberians in Musanze
            </p>
            <p style="color:#333;font-size:16px;
                      margin-top:24px;">
              Hello {voter_name},
            </p>
            <p style="color:#555;">
              Your one-time verification code is:
            </p>
            <div style="background:#1a1a2e;
                        border-radius:12px;
                        padding:32px;
                        margin:24px 0;">
              <div style="font-size:40px;
                          font-weight:bold;
                          color:#c4a84e;
                          letter-spacing:10px;">
                {otp_code}
              </div>
            </div>
            <p style="color:#888;font-size:13px;">
              This code expires in 10 minutes.
              Never share this code with anyone.
            </p>
            <hr style="border:none;
                       border-top:1px solid #eee;
                       margin:24px 0;"/>
            <p style="color:#aaa;font-size:11px;">
              ALM General Elections
            </p>
          </div>
        </body>
        </html>
        """

        html_part = MIMEText(html_content, "html")
        message.attach(html_part)

        print("Connecting to Gmail SMTP...")

        # Use explicit SMTP connection with timeout
        smtp = aiosmtplib.SMTP(
            hostname="smtp.gmail.com",
            port=587,
            timeout=30
        )

        await smtp.connect()
        print("Connected to SMTP")

        await smtp.starttls()
        print("TLS started")

        await smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        print("Logged in to Gmail")

        await smtp.send_message(message)
        print(f"Email sent successfully to {to_email}")

        await smtp.quit()

        return True

    except aiosmtplib.SMTPAuthenticationError as e:
        print(f"Gmail auth error: {e}")
        print("Check GMAIL_APP_PASSWORD is correct")
        return False
    except aiosmtplib.SMTPConnectError as e:
        print(f"Gmail connect error: {e}")
        return False
    except Exception as e:
        print(f"Gmail send error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_otp() -> str:
    return ''.join(random.choices(string.digits, k=6))