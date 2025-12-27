import time
import os
import smtplib
from email.mime.text import MIMEText
import requests

def send_email_alert(recipient: str, subject: str, body: str):
    """
    Sends an URGENT email via SMTP.
    """
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")

    if smtp_user and smtp_pass:
        try:
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = smtp_user
            msg['To'] = recipient

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
            print(f"\n[ACTION] EMAIL SENT to {recipient}")
            return "Email Sent (Real)"
        except Exception as e:
            print(f"\n[ACTION FAILED] Email Error: {e}")
            return "Email Failed"
    else:
        # Dry Run
        print(f"\n[ACTION] DRY-RUN EMAIL to {recipient}")
        print(f"Subject: {subject}")
        print(f"Body: {body}\n")
        return "Dry-Run Sent"

def trigger_slack_notification(channel: str, message: str):
    """
    Sends a Real Slack Webhook.
    """
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    
    if webhook_url:
        try:
            payload = {"text": message, "channel": channel}
            requests.post(webhook_url, json=payload)
            print(f"\n[ACTION] SLACK ALERT SENT to {channel}")
            return "Slack Sent (Real)"
        except Exception as e:
            print(f"\n[ACTION FAILED] Slack Error: {e}")
            return "Slack Failed"
    else:
        print(f"\n[ACTION] DRY-RUN SLACK to {channel}: {message}\n")
        return "Dry-Run Slack"

def update_erp_shipment_status(shipment_id: str, new_status: str, note: str):
    """
    Simulates updating the internal ERP.
    """
    # ERP tends to be custom, usually a REST PUT
    erp_url = os.getenv("ERP_API_URL")
    if erp_url:
        # requests.put(...)
        pass
        
    print(f"\n[ACTION] ERP UPDATE: Shipment {shipment_id} -> Status: {new_status}")
    print(f"Note: {note}\n")
    return "ERP Updated"
