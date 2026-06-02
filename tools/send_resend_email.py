"""
Send a test email using Resend HTTP API.
Usage:
  python tools/send_resend_email.py recipient@example.com
It will load the Resend API key from the `RESEND_API_KEY` env var (or `SMTP_PASS` as fallback)
from the parent `alm-backend/.env` file.
"""
import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load .env located in alm-backend (parent directory of this script)
base_dir = Path(__file__).resolve().parent.parent
env_path = base_dir / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

if len(sys.argv) < 2:
    print("Usage: python tools/send_resend_email.py recipient@example.com")
    sys.exit(1)

recipient = sys.argv[1]
api_key = os.getenv('RESEND_API_KEY') or os.getenv('SMTP_PASS')
from_addr = os.getenv('SMTP_FROM') or f"no-reply@{os.getenv('FRONTEND_URL','example.com').replace('http://','').replace('https://','') }"

if not api_key:
    print('Resend API key not found in RESEND_API_KEY or SMTP_PASS env vars.')
    sys.exit(1)

urls = [
    'https://api.resend.com/v1/emails',
    'https://api.resend.com/v1/messages',
    'https://api.resend.com/emails',
    'https://api.resend.com/messages',
]
headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json',
}

payload = {
    'from': from_addr,
    'to': recipient,
    'subject': 'ALM Test OTP via Resend API',
    'text': 'This is a test message sent via Resend HTTP API for ALM OTP verification.'
}

success = False
for url in urls:
    print(f'Trying {url} ...')
    try:
        resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=15)
        try:
            body = resp.json()
        except Exception:
            body = resp.text
        print('Status:', resp.status_code)
        print('Response:', body)
        if resp.status_code >= 200 and resp.status_code < 300:
            print(f'Successfully sent test email to {recipient} via {url}')
            success = True
            break
    except Exception as e:
        print(f'Error sending to {url}:', e)

if not success:
    print('All endpoints failed; check API key and network connectivity.')
    sys.exit(1)
