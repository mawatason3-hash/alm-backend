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
        if not GMAIL_USER or not GMAIL_APP_PASSWORD:
            print("Gmail not configured")
            return False

        message = MIMEMultipart("alternative")
        message["Subject"] = f"Your ALM Voting OTP: {otp_code}"
        message["From"] = f"ALM Voting System <{GMAIL_USER}>"
        message["To"] = to_email

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, sans-serif; 
                     background: #f5f5f5; padding: 40px;">
          <div style="max-width: 500px; margin: 0 auto;
                      background: #fff; border-radius: 12px;
                      padding: 40px; text-align: center;">
            <h2 style="color: #1a1a2e; margin-bottom: 8px;">
              ALM Voting System
            </h2>
            <p style="color: #555; margin-bottom: 32px;">
              Association of Liberians in Musanze
            </p>
            <p style="color: #333; font-size: 16px;">
              Hello {voter_name},
            </p>
            <p style="color: #555; margin-bottom: 24px;">
              Your one-time verification code is:
            </p>
            <div style="background: #1a1a2e; 
                        border-radius: 12px;
                        padding: 24px; 
                        margin: 24px 0;">
              <div style="font-size: 36px; 
                          font-weight: bold;
                          color: #c4a84e; 
                          letter-spacing: 8px;">
                {otp_code}
              </div>
            </div>
            <p style="color: #888; font-size: 13px;">
              This code expires in 10 minutes.
              Do not share this code with anyone.
            </p>
            <hr style="border: none; 
                       border-top: 1px solid #eee;
                       margin: 24px 0;"/>
            <p style="color: #aaa; font-size: 11px;">
              ALM General Elections — Official Communication
            </p>
          </div>
        </body>
        </html>
        """

        html_part = MIMEText(html_content, "html")
        message.attach(html_part)

        await aiosmtplib.send(
            message,
            hostname="smtp.gmail.com",
            port=587,
            start_tls=True,
            username=GMAIL_USER,
            password=GMAIL_APP_PASSWORD,
        )

        print(f"OTP email sent to {to_email}")
        return True

    except Exception as e:
        print(f"Email send error: {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_otp() -> str:
    return ''.join(random.choices(string.digits, k=6))