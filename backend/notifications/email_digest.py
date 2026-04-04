"""
Email digest sender for the Athens RE nightly batch pipeline.

Supports two providers:
  smtp     — stdlib smtplib (Gmail with app password, or any SMTP relay)
  sendgrid — SendGrid Web API v3 (requires `sendgrid` package)

Config is read from environment variables via backend.config.
"""
import logging
import smtplib
import ssl
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


# ── HTML template helpers ─────────────────────────────────────────────────────

_STYLE = """
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #0f172a; color: #e2e8f0; margin: 0; padding: 0; }
  .wrap { max-width: 680px; margin: 0 auto; padding: 32px 24px; }
  h1 { font-size: 22px; color: #f8fafc; margin-bottom: 4px; }
  .sub { font-size: 13px; color: #94a3b8; margin-bottom: 32px; }
  h2 { font-size: 15px; color: #8b5cf6; text-transform: uppercase;
       letter-spacing: 0.08em; border-bottom: 1px solid #1e293b;
       padding-bottom: 8px; margin-top: 32px; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th { text-align: left; color: #64748b; font-weight: 600;
       padding: 6px 10px; border-bottom: 1px solid #1e293b; }
  td { padding: 8px 10px; border-bottom: 1px solid #0f172a; vertical-align: top; }
  tr:nth-child(even) td { background: #1e293b; }
  .score-critical { color: #ef4444; font-weight: 700; }
  .score-high     { color: #f97316; font-weight: 700; }
  .score-watch    { color: #eab308; font-weight: 700; }
  .none           { color: #475569; font-style: italic; padding: 16px 10px; }
  .footer         { margin-top: 40px; font-size: 11px; color: #475569;
                    border-top: 1px solid #1e293b; padding-top: 16px; }
"""


def _score_class(score: int) -> str:
    if score >= 70:
        return "score-critical"
    if score >= 50:
        return "score-high"
    return "score-watch"


def _listings_rows(listings: list[dict]) -> str:
    if not listings:
        return '<tr><td class="none" colspan="5">No new listings today.</td></tr>'
    rows = []
    for p in listings:
        cap = ""
        cf = p.get("cash_flow", {})
        if cf:
            cap = f"{cf.get('cap_rate_pct', 0):.1f}%"
        rows.append(
            f"<tr>"
            f"<td>{p.get('address', '—')}</td>"
            f"<td>{p.get('price', '—')}</td>"
            f"<td>{p.get('type', '—')}</td>"
            f"<td>{p.get('beds', '—')} BR</td>"
            f"<td>{cap or '—'}</td>"
            f"</tr>"
        )
    return "\n".join(rows)


def _parcels_rows(parcels: list[dict]) -> str:
    if not parcels:
        return '<tr><td class="none" colspan="5">No new distressed parcels today.</td></tr>'
    rows = []
    for p in parcels:
        score = p.get("distress_score", 0)
        signals = p.get("signals", [])
        top_signals = "; ".join(signals[:3]) if signals else "—"
        css = _score_class(score)
        rows.append(
            f"<tr>"
            f"<td>{p.get('address', '—')}</td>"
            f"<td class='{css}'>{score}</td>"
            f"<td>{p.get('distress_tier', '—').title()}</td>"
            f"<td>{top_signals}</td>"
            f"<td>{p.get('owner_name', '—')}</td>"
            f"</tr>"
        )
    return "\n".join(rows)


def _build_html(new_listings: list[dict], new_parcels: list[dict], app_url: str = "") -> str:
    today = date.today().strftime("%B %d, %Y")
    nl = len(new_listings)
    np_ = len(new_parcels)

    listing_rows = _listings_rows(new_listings)
    parcel_rows = _parcels_rows(new_parcels)

    app_link = f'<p><a href="{app_url}" style="color:#8b5cf6">Open Athens RE →</a></p>' if app_url else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><style>{_STYLE}</style></head>
<body><div class="wrap">
  <h1>Athens RE Intelligence</h1>
  <p class="sub">Nightly update — {today} &nbsp;·&nbsp;
    {nl} new listing{"s" if nl != 1 else ""}, {np_} new distressed parcel{"s" if np_ != 1 else ""}</p>

  <h2>New MLS Listings</h2>
  <table>
    <thead><tr>
      <th>Address</th><th>Price</th><th>Type</th><th>Beds</th><th>Cap Rate</th>
    </tr></thead>
    <tbody>{listing_rows}</tbody>
  </table>

  <h2>New Distressed Parcels</h2>
  <table>
    <thead><tr>
      <th>Address</th><th>Score</th><th>Tier</th><th>Top Signals</th><th>Owner</th>
    </tr></thead>
    <tbody>{parcel_rows}</tbody>
  </table>

  {app_link}
  <p class="footer">Athens RE Investment Platform — automated nightly digest.<br>
  To unsubscribe, remove NOTIFY_EMAIL from your environment config.</p>
</div></body></html>"""


def _build_plain(new_listings: list[dict], new_parcels: list[dict]) -> str:
    today = date.today().strftime("%Y-%m-%d")
    lines = [f"Athens RE Nightly Update — {today}", ""]

    lines.append(f"NEW LISTINGS ({len(new_listings)})")
    lines.append("-" * 40)
    if new_listings:
        for p in new_listings:
            lines.append(f"  {p.get('address', '—')}  {p.get('price', '—')}  {p.get('type', '—')}")
    else:
        lines.append("  None today.")

    lines.append("")
    lines.append(f"NEW DISTRESSED PARCELS ({len(new_parcels)})")
    lines.append("-" * 40)
    if new_parcels:
        for p in new_parcels:
            signals = "; ".join((p.get("signals") or [])[:3])
            lines.append(
                f"  {p.get('address', '—')}  score={p.get('distress_score', 0)}  {signals}"
            )
    else:
        lines.append("  None today.")

    return "\n".join(lines)


# ── SMTP sender ───────────────────────────────────────────────────────────────

def _send_smtp(subject: str, html: str, plain: str) -> bool:
    from backend.config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, NOTIFY_EMAIL, FROM_EMAIL

    if not all([SMTP_USER, SMTP_PASS, NOTIFY_EMAIL]):
        logger.error("SMTP send skipped — SMTP_USER, SMTP_PASS, or NOTIFY_EMAIL not configured")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = NOTIFY_EMAIL
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(FROM_EMAIL, NOTIFY_EMAIL, msg.as_string())
        logger.info("Email digest sent via SMTP to %s", NOTIFY_EMAIL)
        return True
    except smtplib.SMTPException as e:
        logger.error("SMTP send failed: %s", e)
        return False


# ── SendGrid sender ───────────────────────────────────────────────────────────

def _send_sendgrid(subject: str, html: str, plain: str) -> bool:
    from backend.config import SENDGRID_API_KEY, NOTIFY_EMAIL, FROM_EMAIL

    if not all([SENDGRID_API_KEY, NOTIFY_EMAIL]):
        logger.error("SendGrid send skipped — SENDGRID_API_KEY or NOTIFY_EMAIL not configured")
        return False

    try:
        import sendgrid
        from sendgrid.helpers.mail import Mail, Content, To

        sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)
        message = Mail(
            from_email=FROM_EMAIL,
            to_emails=To(NOTIFY_EMAIL),
            subject=subject,
        )
        message.content = [
            Content("text/plain", plain),
            Content("text/html", html),
        ]
        response = sg.client.mail.send.post(request_body=message.get())
        if response.status_code in (200, 202):
            logger.info("Email digest sent via SendGrid to %s", NOTIFY_EMAIL)
            return True
        else:
            logger.error("SendGrid returned status %d", response.status_code)
            return False
    except ImportError:
        logger.error("sendgrid package not installed — run: pip install sendgrid")
        return False
    except Exception as e:
        logger.error("SendGrid send failed: %s", e)
        return False


# ── Public API ────────────────────────────────────────────────────────────────

def send_digest(
    new_listings: list[dict],
    new_parcels: list[dict],
    app_url: str = "",
) -> bool:
    """
    Send the nightly digest email.

    Args:
        new_listings:  List of new MLS listing dicts (same format as properties.json entries).
        new_parcels:   List of new distressed parcel dicts.
        app_url:       Optional URL to the deployed app (included as a link in the email).

    Returns:
        True if the email was sent successfully.
    """
    from backend.config import EMAIL_PROVIDER, NOTIFY_EMAIL

    if not NOTIFY_EMAIL:
        logger.warning("NOTIFY_EMAIL not set — skipping digest email")
        return False

    today = date.today().strftime("%Y-%m-%d")
    nl, np_ = len(new_listings), len(new_parcels)
    subject = f"Athens RE — {nl} new listing{'s' if nl != 1 else ''}, {np_} new distressed parcel{'s' if np_ != 1 else ''} [{today}]"

    html = _build_html(new_listings, new_parcels, app_url)
    plain = _build_plain(new_listings, new_parcels)

    if EMAIL_PROVIDER == "sendgrid":
        return _send_sendgrid(subject, html, plain)
    return _send_smtp(subject, html, plain)
