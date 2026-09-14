
import json
import mimetypes
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

from .config import sender_email

DEFAULT_CONFIG = Path.cwd() / "resume.config.json"
DEFAULT_TEMPLATE = Path.cwd() / "cold-email.txt"
DEFAULT_SUBJECT = "Quick question about {company_name}"


def load_recipients(path: Path) -> list[dict[str, str]]:
    return json.loads(path.read_text(encoding="utf-8"))


def render(template: str, values: dict[str, str]) -> str:
    return template.format(**values)


def message_for(
    sender: str,
    recipient: dict[str, str],
    subject_template: str,
    body_template: str,
    attachment: Path | None,
) -> EmailMessage:
    values = dict(recipient)
    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient["email"]
    message["Subject"] = render(subject_template, values)
    message.set_content(render(body_template, values))
    if attachment is not None:
        content = attachment.read_bytes()
        mime_type, _ = mimetypes.guess_type(attachment.name)
        maintype, subtype = (mime_type or "application/octet-stream").split("/", maxsplit=1)
        message.add_attachment(content, maintype=maintype, subtype=subtype, filename=attachment.name)
    return message


def smtp_client(host: str, port: int, security: str) -> smtplib.SMTP:
    if security == "ssl":
        return smtplib.SMTP_SSL(host, port, timeout=30)
    client = smtplib.SMTP(host, port, timeout=30)
    if security == "starttls":
        client.starttls()
    return client


def main() -> None:
    recipients_path = Path(input("Recipients JSON file: ").strip())
    attachment_value = input("Resume attachment path (leave blank for preview only): ").strip()
    attachment = Path(attachment_value) if attachment_value else None
    send = input("Send emails? [y/N]: ").strip().casefold() in {"y", "yes"}

    sender = sender_email(DEFAULT_CONFIG)
    recipients = load_recipients(recipients_path)
    body_template = DEFAULT_TEMPLATE.read_text(encoding="utf-8")
    messages = [
        message_for(sender, recipient, DEFAULT_SUBJECT, body_template, attachment)
        for recipient in recipients
    ]

    if not send:
        for message in messages:
            print(f"To: {message['To']}\nSubject: {message['Subject']}\n\n{message.get_body(preferencelist=('plain',)).get_content()}")
            print("---")
        print(f"Dry run: {len(messages)} email(s) not sent.")
        return

    if attachment is None:
        raise SystemExit("Sending requires a resume attachment because the default template promises one.")
    host = os.environ.get("SMTP_HOST")
    if not host:
        raise SystemExit("Sending requires SMTP_HOST.")
    password = os.environ.get("SMTP_PASSWORD")
    if not password:
        raise SystemExit("Sending requires SMTP_PASSWORD.")
    username = os.environ.get("SMTP_USERNAME", sender)
    port = int(os.environ.get("SMTP_PORT", "587"))
    security = os.environ.get("SMTP_SECURITY", "starttls")

    with smtp_client(host, port, security) as client:
        client.login(username, password)
        for message in messages:
            client.send_message(message)
            print(f"Sent: {message['To']}")


if __name__ == "__main__":
    main()
