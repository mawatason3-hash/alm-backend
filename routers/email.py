import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
import os
import random
import string

BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
SENDER_EMAIL = os.environ.get(
    "GMAIL_USER",
    "mawatason3@gmail.com"
)
SENDER_NAME = "ALM Voting System"


def get_brevo_client():
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = BREVO_API_KEY
    return sib_api_v3_sdk.TransactionalEmailsApi(
        sib_api_v3_sdk.ApiClient(configuration)
    )


def is_email_configured() -> bool:
    return bool(BREVO_API_KEY)


async def send_otp_email(
    to_email: str,
    voter_name: str,
    otp_code: str
) -> bool:
    try:
        print(f"Sending OTP via Brevo to: {to_email}")
        print(f"API key set: {bool(BREVO_API_KEY)}")
        
        if not BREVO_API_KEY:
            print("ERROR: BREVO_API_KEY not configured")
            return False
        
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
            <h2 style="color:#1a1a2e;margin-bottom:4px;">
              ALM Voting System
            </h2>
            <p style="color:#888;font-size:12px;
                      margin-bottom:24px;">
              Association of Liberians in Musanze
            </p>
            <p style="color:#333;font-size:15px;">
              Hello {voter_name},
            </p>
            <p style="color:#555;margin-bottom:20px;">
              Your one-time verification code is:
            </p>
            <div style="background:#1a1a2e;
                        border-radius:12px;
                        padding:32px;
                        margin:20px 0;">
              <div style="font-size:42px;
                          font-weight:bold;
                          color:#c4a84e;
                          letter-spacing:12px;">
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
            <p style="color:#bbb;font-size:11px;">
              ALM General Elections — Official Communication
            </p>
          </div>
        </body>
        </html>
        """
        
        api_instance = get_brevo_client()
        
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{
                "email": to_email,
                "name": voter_name
            }],
            sender={
                "email": SENDER_EMAIL,
                "name": SENDER_NAME
            },
            subject=f"Your ALM Voting Code: {otp_code}",
            html_content=html_content
        )
        
        response = api_instance.send_transac_email(
            send_smtp_email
        )
        
        print(f"Brevo response: {response}")
        print(f"Email sent successfully to {to_email}")
        return True
        
    except ApiException as e:
        print(f"Brevo API error: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"Email error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_otp() -> str:
    return ''.join(random.choices(string.digits, k=6))