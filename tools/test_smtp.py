"""
Simple SMTP test script for local verification of OTP email sending logic.
Usage:
  set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM in environment
  python tools/test_smtp.py recipient@example.com

If SMTP_* are not set, the script will report missing configuration.
"""
import os
import sys
from email.message import EmailMessage
import smtplib


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/test_smtp.py recipient@example.com")
        return
    recipient = sys.argv[1]
    smtp_host = os.getenv('SMTP_HOST')
    smtp_port = os.getenv('SMTP_PORT')
    smtp_user = os.getenv('SMTP_USER')
    smtp_pass = os.getenv('SMTP_PASS')
    smtp_from = os.getenv('SMTP_FROM') or smtp_user

    if not (smtp_host and smtp_user and smtp_pass):
        print('SMTP configuration missing. Set SMTP_HOST, SMTP_USER, SMTP_PASS (and optionally SMTP_PORT, SMTP_FROM)')
        return

    msg = EmailMessage()
    msg['Subject'] = 'ALM Test OTP'
    msg['From'] = smtp_from
    msg['To'] = recipient
    msg.set_content('This is a test message from ALM OTP SMTP test script.')

    port = int(smtp_port) if smtp_port else 465
    try:
        with smtplib.SMTP_SSL(smtp_host, port, timeout=10) as smtp:
            smtp.login(smtp_user, smtp_pass)
            smtp.send_message(msg)
        print(f'Successfully sent test email to {recipient} via {smtp_host}:{port}')
    except Exception as e:
        print('Failed to send test email:', e)


if __name__ == '__main__':
    main()
