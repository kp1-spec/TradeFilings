"""Email a digest of newly collected transactions.

Reads SMTP settings from environment variables (set as GitHub Secrets):
  SMTP_HOST (default smtp.gmail.com), SMTP_PORT (default 587),
  SMTP_USER, SMTP_PASS (a Gmail App Password, not your login password),
  DIGEST_TO (where to send), DASHBOARD_URL (optional link).
Alert threshold comes from config.json (alert_min_amount).
"""
import os
import json
import smtplib
from email.message import EmailMessage

CONFIG = os.path.join(os.path.dirname(__file__), "..", "config.json")


def load_config():
    with open(CONFIG) as f:
        return json.load(f)


def money(n):
    return "${:,.0f}".format(n)


def render(new_tx, cfg):
    thr = cfg.get("alert_min_amount", 0)
    watch = {t.upper() for t in cfg.get("watch_tickers", [])}
    big = [t for t in new_tx if t["amount_low"] >= thr or (t.get("ticker") or "").upper() in watch]
    lines = []
    if big:
        lines.append(f"{len(big)} transaction(s) at or above {money(thr)} or on your watchlist:\n")
        for t in sorted(big, key=lambda x: -x["amount_low"]):
            lines.append(f"  {t['filer']} ({t.get('state_district') or t['source']})  {t['tx_type']}  "
                         f"{t.get('ticker') or ''} {t['asset']}\n"
                         f"     {money(t['amount_low'])} to {money(t['amount_high'])}, traded {t['tx_date']}, "
                         f"filed {t['filing_date']}\n     {t['doc_url']}")
    lines.append(f"\nAll new transactions this run: {len(new_tx)}")
    for t in new_tx:
        if t in big:
            continue
        lines.append(f"  {t['filing_date']}  {t['filer']}  {t['tx_type']}  {t.get('ticker') or ''} "
                     f"{t['asset'][:50]}  {money(t['amount_low'])}+")
    url = os.environ.get("DASHBOARD_URL")
    if url:
        lines.append(f"\nDashboard: {url}")
    return "\n".join(lines), len(big)


def send(new_tx):
    cfg = load_config()
    if not new_tx and not cfg.get("email_when_empty", False):
        print("No new transactions; skipping email.")
        return
    body, n_big = render(new_tx, cfg)
    msg = EmailMessage()
    msg["Subject"] = f"Trade filings: {len(new_tx)} new, {n_big} above threshold"
    msg["From"] = os.environ["SMTP_USER"]
    msg["To"] = os.environ.get("DIGEST_TO", os.environ["SMTP_USER"])
    msg.set_content(body)
    with smtplib.SMTP(os.environ.get("SMTP_HOST", "smtp.gmail.com"), int(os.environ.get("SMTP_PORT", "587"))) as s:
        s.starttls()
        s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
        s.send_message(msg)
    print(f"Emailed digest: {len(new_tx)} new, {n_big} above threshold")
