#!/usr/bin/env python3
import argparse
import html
import os
import re
import socket
import smtplib
import ssl
import sys
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

from pipeline_config import ROOT, default_notify_recipients, get_series_dir, load_local_env


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def recipients():
    configured = default_notify_recipients()
    return configured or []


def write_pending(subject: str, body: str, series_dir: Path):
    notifications = series_dir / "notifications"
    notifications.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = notifications / f"{stamp}_email_pending.md"
    out_path.write_text(f"# {subject}\n\n{body}\n", encoding="utf-8")
    print(f"SMTP is not fully configured. Wrote pending notification: {out_path}")


def format_inline(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    return escaped


def markdown_to_html(body: str) -> str:
    lines = body.strip().splitlines()
    html_parts = []
    in_list = False
    in_code = False
    code_lines = []
    paragraph = []

    def flush_paragraph():
        nonlocal paragraph
        if paragraph:
            text = " ".join(item.strip() for item in paragraph).strip()
            if text:
                html_parts.append(f"<p>{format_inline(text)}</p>")
            paragraph = []

    def close_list():
        nonlocal in_list
        if in_list:
            html_parts.append("</ul>")
            in_list = False

    def flush_code():
        nonlocal in_code, code_lines
        if in_code:
            code = html.escape("\n".join(code_lines).strip("\n"))
            html_parts.append(f"<pre><code>{code}</code></pre>")
            code_lines = []
            in_code = False

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_paragraph()
            close_list()
            if in_code:
                flush_code()
            else:
                in_code = True
                code_lines = []
            continue

        if in_code:
            code_lines.append(line)
            continue

        if not stripped:
            flush_paragraph()
            close_list()
            continue

        if stripped.startswith("## "):
            flush_paragraph()
            close_list()
            html_parts.append(f"<h2>{format_inline(stripped[3:])}</h2>")
            continue

        if stripped.startswith("# "):
            flush_paragraph()
            close_list()
            html_parts.append(f"<h1>{format_inline(stripped[2:])}</h1>")
            continue

        if stripped.startswith("- "):
            flush_paragraph()
            if not in_list:
                html_parts.append("<ul>")
                in_list = True
            html_parts.append(f"<li>{format_inline(stripped[2:])}</li>")
            continue

        paragraph.append(stripped)

    flush_paragraph()
    close_list()
    flush_code()
    return "\n".join(html_parts)


def render_email_html(subject: str, body: str) -> str:
    content = markdown_to_html(body)
    escaped_subject = html.escape(subject)
    return f"""\
<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escaped_subject}</title>
  </head>
  <body style="margin:0;padding:24px;background:#f3f5f7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#18212b;">
    <div style="max-width:720px;margin:0 auto;background:#ffffff;border:1px solid #d9e0e7;border-radius:16px;overflow:hidden;">
      <div style="padding:20px 24px;background:#18212b;color:#ffffff;">
        <div style="font-size:12px;letter-spacing:0.08em;text-transform:uppercase;opacity:0.72;">Storyforge</div>
        <div style="margin-top:8px;font-size:28px;line-height:1.2;font-weight:700;">{escaped_subject}</div>
      </div>
      <div style="padding:24px;">
        <div style="font-size:15px;line-height:1.65;">
          {content}
        </div>
      </div>
    </div>
  </body>
</html>
"""


def send_email(subject: str, body: str):
    to_list = recipients()
    if not to_list:
        print("No PIPELINE_NOTIFY_EMAIL configured; skipping email delivery.")
        return False

    username = os.getenv("SMTP_USERNAME") or os.getenv("EMAIL_SENDER")
    password = os.getenv("SMTP_PASSWORD") or os.getenv("EMAIL_PASSWORD")
    from_email = os.getenv("SMTP_FROM_EMAIL") or os.getenv("EMAIL_SENDER") or username
    host = os.getenv("SMTP_HOST")
    if not host and username and username.lower().endswith("@gmail.com"):
        host = "smtp.gmail.com"
    port = int(os.getenv("SMTP_PORT", "587"))
    use_tls = env_bool("SMTP_USE_TLS", True)

    if not (host and username and password and from_email):
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = from_email
    message["To"] = ", ".join(to_list)
    message.set_content(body)
    message.add_alternative(render_email_html(subject, body), subtype="html")

    try:
        if use_tls:
            context = ssl.create_default_context()
            with smtplib.SMTP(host, port, timeout=60) as server:
                server.starttls(context=context)
                server.login(username, password)
                server.send_message(message)
        else:
            with smtplib.SMTP_SSL(host, port, timeout=60) as server:
                server.login(username, password)
                server.send_message(message)
    except (OSError, socket.gaierror, smtplib.SMTPException) as exc:
        print(f"Email delivery failed: {exc}")
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description="Send or queue a storyforge pipeline update.")
    parser.add_argument("--subject", required=True)
    parser.add_argument("--body-file", required=True)
    parser.add_argument(
        "--series-dir",
        default=None,
        help="Series directory where pending notifications should be written.",
    )
    args = parser.parse_args()

    load_local_env()
    body = Path(args.body_file).read_text(encoding="utf-8")
    series_dir = Path(args.series_dir) if args.series_dir else get_series_dir()
    if not series_dir.is_absolute():
        series_dir = (ROOT / series_dir).resolve()

    if send_email(args.subject, body):
        print(f"Sent email update to {', '.join(recipients())}")
        return 0

    write_pending(args.subject, body, series_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
