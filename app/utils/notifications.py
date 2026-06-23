import requests, smtplib
from email.mime.text import MIMEText

def send_slack_message(webhook_url: str, text: str):
    requests.post(webhook_url, json={"text": text})

def send_email(smtp_server: str, sender: str, recipient: str, subject: str, body: str):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    with smtplib.SMTP(smtp_server) as server:
        server.sendmail(sender, [recipient], msg.as_string())
