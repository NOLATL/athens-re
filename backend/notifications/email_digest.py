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
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)


# ── HTML template helpers ─────────────────────────────────────────────────────

_STYLE = """
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #0f172a; color: #e2e8f0; margin: 0; padding: 0; }
  .wrap { max-width: 700px; margin: 0 auto; padding: 32px 24px; }
  h1 { font-size: 22px; color: #f8fafc; margin-bottom: 4px; }
  .sub { font-size: 13px; color: #94a3b8; margin-bottom: 32px; }
  h2 { font-size: 15px; color: #8b5cf6; text-transform: uppercase;
       letter-spacing: 0.08em; border-bottom: 1px solid #1e293b;
       padding-bottom: 8px; margin-top: 32px; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th { text-align: left; color: #64748b; font-weight: 600;
       padding: 6px 10px; border-bottom: 1px solid #1e293b; }
  td { padding: 8px 10px; border-bottom: 1px solid #0f172a; vertical-align: middle; }
  tr:nth-child(even) td { background: #1e293b; }
  .none { color: #475569; font-style: italic; padding: 16px 10px; }
  .score-critical { color: #ef4444; font-weight: 700; }
  .score-high     { color: #f97316; font-weight: 700; }
  .score-watch    { color: #eab308; font-weight: 700; }
  .footer { margin-top: 40px; font-size: 11px; color: #475569;
            border-top: 1px solid #1e293b; padding-top: 16px; line-height: 1.6; }
  .rank { color: #64748b; font-size: 11px; font-weight: 600; }
  .prev-price { color: #94a3b8; text-decoration: line-through; }
"""


def _score_class(score: int) -> str:
    if score >= 70:
        return "score-critical"
    if score >= 50:
        return "score-high"
    return "score-watch"


def _cf_dot_html(cash_flow: dict | None) -> str:
    """Green ● if cash flow positive, red ● if negative, gray ● if unknown."""
    if not cash_flow:
        return '<span style="color:#475569;font-size:16px;" title="Cash flow unavailable">●</span>'
    mcf = cash_flow.get("monthly_cash_flow")
    if mcf is None:
        return '<span style="color:#475569;font-size:16px;" title="Cash flow unavailable">●</span>'
    if mcf >= 0:
        return f'<span style="color:#16a34a;font-size:16px;" title="+${mcf:,.0f}/mo cash flow">●</span>'
    return f'<span style="color:#dc2626;font-size:16px;" title="-${abs(mcf):,.0f}/mo cash flow">●</span>'


def _score_badge_html(score: float | None) -> str:
    if score is None:
        return '<span style="color:#475569;">—</span>'
    if score >= 70:
        c = "#16a34a"
    elif score >= 50:
        c = "#8b5cf6"
    else:
        c = "#dc2626"
    return (
        f'<span style="font-weight:800;color:{c};background:{c}18;'
        f'border:1px solid {c}40;border-radius:4px;padding:2px 8px;'
        f'font-size:12px;white-space:nowrap;">{score:.0f}/100</span>'
    )


def _cap_rate_cell(cash_flow: dict | None) -> str:
    if not cash_flow:
        return "—"
    cap = cash_flow.get("cap_rate_pct")
    if cap is None:
        return "—"
    if cap >= 6:
        color = "#16a34a"
    elif cap >= 4:
        color = "#8b5cf6"
    else:
        color = "#dc2626"
    return f'<span style="color:{color};font-weight:700;">{cap:.1f}%</span>'


def _property_link_html(address: str, app_url: str) -> str:
    if not app_url:
        return f'<span style="font-weight:600;color:#e2e8f0;">{address}</span>'
    url = f"{app_url.rstrip('/')}/?property={quote_plus(address)}"
    return f'<a href="{url}" style="color:#8b5cf6;text-decoration:none;font-weight:600;">{address}</a>'


def _listing_rows_html(listings: list[dict], app_url: str = "", include_prev_price: bool = False) -> str:
    if not listings:
        colspan = 5 if not include_prev_price else 6
        return f'<tr><td class="none" colspan="{colspan}">None today.</td></tr>'

    def sort_key(p):
        r = p.get("rank")
        return (r if r is not None else 9999, -(p.get("composite_score") or 0))

    rows = []
    for p in sorted(listings, key=sort_key):
        cf = p.get("cash_flow") or {}
        rank = p.get("rank")
        dot = _cf_dot_html(cf or None)
        rank_str = f'<span class="rank">#{rank}</span>' if rank else '<span class="rank">—</span>'
        score_badge = _score_badge_html(p.get("composite_score"))
        cap = _cap_rate_cell(cf or None)
        address_cell = _property_link_html(p.get("address", "—"), app_url)
        price = p.get("price", "—")

        cells = [
            f'<td style="text-align:center;white-space:nowrap;">{dot}&nbsp;{rank_str}</td>',
            f'<td>{address_cell}</td>',
            f'<td style="white-space:nowrap;font-weight:700;color:#a78bfa;">{price}</td>',
        ]
        if include_prev_price:
            prev = p.get("previous_price", "—")
            cells.append(f'<td class="prev-price" style="white-space:nowrap;">{prev}</td>')
        cells += [
            f'<td style="text-align:center;">{score_badge}</td>',
            f'<td style="text-align:center;">{cap}</td>',
        ]
        rows.append(f"<tr>{''.join(cells)}</tr>")
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


def _build_html(listing_events: dict, new_parcels: list[dict], app_url: str = "") -> str:
    true_new = list(listing_events.get("true_new", []))
    price_drop = list(listing_events.get("price_drop", []))
    today = date.today().strftime("%B %d, %Y")
    np_ = len(new_parcels)

    app_link = f'<p style="margin-top:20px;"><a href="{app_url}" style="color:#8b5cf6;font-weight:700;">Open Athens RE →</a></p>' if app_url else ""

    new_head = (
        "<thead><tr>"
        "<th style='width:60px;'></th>"
        "<th>Address</th>"
        "<th>Price</th>"
        "<th style='text-align:center;'>Score</th>"
        "<th style='text-align:center;'>Est. Cap</th>"
        "</tr></thead>"
    )
    drop_head = (
        "<thead><tr>"
        "<th style='width:60px;'></th>"
        "<th>Address</th>"
        "<th>Current</th>"
        "<th>Was</th>"
        "<th style='text-align:center;'>Score</th>"
        "<th style='text-align:center;'>Est. Cap</th>"
        "</tr></thead>"
    )
    parcel_head = (
        "<thead><tr>"
        "<th>Address</th><th>Score</th><th>Tier</th><th>Top Signals</th><th>Owner</th>"
        "</tr></thead>"
    )

    new_rows = _listing_rows_html(true_new, app_url)
    drop_rows = _listing_rows_html(price_drop, app_url, include_prev_price=True)
    parcel_rows = _parcels_rows(new_parcels)

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><style>{_STYLE}</style></head>
<body><div class="wrap">
  <h1>Athens RE Intelligence</h1>
  <p class="sub">Nightly update — {today} &nbsp;·&nbsp;
    {len(true_new)} new listing{"s" if len(true_new) != 1 else ""} &nbsp;·&nbsp;
    {len(price_drop)} price drop{"s" if len(price_drop) != 1 else ""} &nbsp;·&nbsp;
    {np_} distressed parcel{"s" if np_ != 1 else ""}</p>

  <h2>New Listings</h2>
  <table>{new_head}<tbody>{new_rows}</tbody></table>

  <h2>Price Drops</h2>
  <table>{drop_head}<tbody>{drop_rows}</tbody></table>

  <h2>New Distressed Parcels</h2>
  <table>{parcel_head}<tbody>{parcel_rows}</tbody></table>

  {app_link}
  <p class="footer">
    ● green = positive cash flow &nbsp;·&nbsp; ● red = negative cash flow &nbsp;·&nbsp; #rank = global rank by investment score<br>
    Score and cap rate are estimated and assumption-based. Verify before underwriting.<br>
    Athens RE Investment Platform — automated nightly digest.<br>
    To unsubscribe, remove NOTIFY_EMAIL from your environment config.
  </p>
</div></body></html>"""


def _build_plain(listing_events: dict, new_parcels: list[dict]) -> str:
    true_new = list(listing_events.get("true_new", []))
    price_drop = list(listing_events.get("price_drop", []))
    today = date.today().strftime("%Y-%m-%d")

    def sort_key(p):
        r = p.get("rank")
        return (r if r is not None else 9999, -(p.get("composite_score") or 0))

    def cf_dot(p):
        mcf = (p.get("cash_flow") or {}).get("monthly_cash_flow")
        if mcf is None:
            return "[ ]"
        return "[+]" if mcf >= 0 else "[-]"

    def fmt_row(p, include_prev=False):
        rank = f"#{p['rank']:<3}" if p.get("rank") else "    "
        score = f"score={p['composite_score']:.0f}" if p.get("composite_score") is not None else "       "
        cap_val = (p.get("cash_flow") or {}).get("cap_rate_pct")
        cap = f"cap={cap_val:.1f}%" if cap_val is not None else "       "
        price = p.get("price", "—")
        if include_prev:
            price = f"{price} (was {p.get('previous_price', '—')})"
        return f"  {cf_dot(p)} {rank}  {p.get('address', '—'):<50}  {price:<16}  {score}  {cap}"

    lines = [f"Athens RE Nightly Update — {today}", ""]

    lines.append(f"NEW LISTINGS ({len(true_new)})")
    lines.append("-" * 60)
    if true_new:
        for p in sorted(true_new, key=sort_key):
            lines.append(fmt_row(p))
    else:
        lines.append("  None today.")
    lines.append("")

    lines.append(f"PRICE DROPS ({len(price_drop)})")
    lines.append("-" * 60)
    if price_drop:
        for p in sorted(price_drop, key=sort_key):
            lines.append(fmt_row(p, include_prev=True))
    else:
        lines.append("  None today.")
    lines.append("")

    lines.append(f"NEW DISTRESSED PARCELS ({len(new_parcels)})")
    lines.append("-" * 60)
    if new_parcels:
        for p in new_parcels:
            signals = "; ".join((p.get("signals") or [])[:3])
            lines.append(f"  {p.get('address', '—'):<50}  score={p.get('distress_score', 0)}  {signals}")
    else:
        lines.append("  None today.")

    lines.append("")
    lines.append("[+] = positive cash flow  [-] = negative  [ ] = unknown")
    lines.append("#rank = global investment score rank across all current listings")
    lines.append("Score and cap rate are estimated and assumption-based.")
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
    listing_events,
    new_parcels: list[dict],
    app_url: str = "",
) -> bool:
    """
    Send the nightly digest email.

    Args:
        listing_events: Dict with keys "true_new" and "price_drop" (lists of enriched
                        listing dicts). Legacy list input is treated as true_new.
        new_parcels:    List of new distressed parcel dicts.
        app_url:        Optional URL to the deployed app; used to build deep links.

    Returns:
        True if the email was sent successfully.
    """
    from backend.config import EMAIL_PROVIDER, NOTIFY_EMAIL

    if not NOTIFY_EMAIL:
        logger.warning("NOTIFY_EMAIL not set — skipping digest email")
        return False

    if isinstance(listing_events, list):
        listing_events = {"true_new": listing_events, "price_drop": []}
    elif not isinstance(listing_events, dict):
        listing_events = {"true_new": [], "price_drop": []}

    true_new = len(listing_events.get("true_new", []))
    price_drop = len(listing_events.get("price_drop", []))
    np_ = len(new_parcels)
    today = date.today().strftime("%Y-%m-%d")
    subject = (
        f"Athens RE — {true_new} new, {price_drop} price drop{'s' if price_drop != 1 else ''}, "
        f"{np_} distressed [{today}]"
    )

    html = _build_html(listing_events, new_parcels, app_url)
    plain = _build_plain(listing_events, new_parcels)

    if EMAIL_PROVIDER == "sendgrid":
        return _send_sendgrid(subject, html, plain)
    return _send_smtp(subject, html, plain)
