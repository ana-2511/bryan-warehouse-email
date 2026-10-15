"""
Weekly email to Bryan: "Action required by Bryan for Unshipped orders and Unaccounted inventory".
Every Monday 11:00 AM IST from GitHub Actions.

Opens Bryan's dashboard (its own Netlify site), waits for Zoho + the Unaccounted Item sheet to load,
captures the Pending Outgoing / Ageing Unshipped cards and the Ageing Range of Unaccounted Item
(sharp, never cropped) and emails them in the template, with two attachments:
  - Unaccounted-Inventory-Details (Excel, from the Unaccounted Item Google Sheet)
  - Unshipped-Orders-VVI_FBM (CSV, from Zoho)

GitHub secrets:   SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, MAIL_FROM (optional)
GitHub variable:  BRYAN_DASHBOARD_URL  (e.g. https://bryan-warehouse.netlify.app)
Recipients are set below.
"""

import os
import smtplib
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import make_msgid

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# ---------------------------------------------------------------- people
# Fill in any address left as "" (blank addresses are skipped, nothing breaks).
BRYAN = "bryan.f@ergode.com"
RUPESH = "rupesh@ergodeinc.com"
ANKUSH = "ankush.l@ergode.com"
KRISHNA = ""   # TODO: Krishna's email address
PANKAJ = ""    # TODO: Pankaj's email address
ROHITASH = "rohitash.s@virventures.com"
AKASH = "akash.sonar@virventures.com"
VIJAY = "vijay.sharma@ergode.com"

DASHBOARD_URL = (os.environ.get("DASHBOARD_URL") or "https://warehousedashboardvirventures.netlify.app/").rstrip("/") + "/"
# Bryan's own website (separate Netlify project). Set the repository variable BRYAN_DASHBOARD_URL.
BRYAN_URL = (os.environ.get("BRYAN_DASHBOARD_URL") or "https://REPLACE-ME.netlify.app").rstrip("/") + "/"
SHEET_ID = "1uqQ2PrTUmTE1Z4bLQEujYE7X4TTvQyntQcsU8ASdv68"
IST = timezone(timedelta(hours=5, minutes=30))
OUT_DIR = "shots"

REPORTS = {
    "bryan": {
        "url": BRYAN_URL,
        "to": [BRYAN],
        "cc": [RUPESH, ANKUSH, KRISHNA, PANKAJ, ROHITASH, AKASH, VIJAY],
        "sections": [("unshipped", "Ageing Unshipped"),
                     ("unaccounted", "Ageing Range of Unaccounted Item")],
        "wait": """() => {
            const t = id => ((document.getElementById(id) || {}).innerText || '');
            return /Synced|unavailable/i.test(t('dataStatus')); }""",
        "live": lambda st: "Live Data Synced" in st.get("status", ""),
    },
}


# ---------------------------------------------------------------- capture
def capture(report: dict) -> dict:
    """Open the page, wait for live data, save one PNG per section + a full page."""
    os.makedirs(OUT_DIR, exist_ok=True)
    status = {"status": "did not load"}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        # 1100px wide: close to the width the email shows the images at (1000px), so text is
        # not shrunk. Scale 2 = crisp text.
        page = browser.new_page(viewport={"width": 1100, "height": 1000}, device_scale_factor=2)

        for attempt in (1, 2, 3):
            try:
                page.goto(report["url"], wait_until="load", timeout=120_000)
                page.wait_for_function(report["wait"], timeout=120_000)
            except PWTimeout:
                print(f"Attempt {attempt}: page did not finish loading in time.")
                continue
            status = {"status": page.evaluate(
                "() => ((document.getElementById('dataStatus') || {}).innerText || '').trim()")}
            if report["live"](status):
                break
            print(f"Attempt {attempt}: partial data {status}, retrying.")

        # Let fonts load and animations finish, and keep the sticky header out of section shots.
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(2500)
        page.add_style_tag(content="header{position:static !important}")

        for key, heading in report["sections"]:
            # the smallest block under <main> that holds the heading = the whole card / card row
            loc = page.locator("main > div").filter(has_text=heading).first
            if loc.count() == 0:
                print(f"Section '{heading}' not found, skipped.")
                continue
            loc.scroll_into_view_if_needed()
            page.wait_for_timeout(500)
            loc.screenshot(path=f"{OUT_DIR}/{key}.png", animations="disabled")

        page.screenshot(path=f"{OUT_DIR}/full-page.png", full_page=True, animations="disabled")
        browser.close()
    return status


def download(url: str, must_contain: str = "") -> bytes | None:
    for attempt in (1, 2, 3):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                ctype = r.headers.get("Content-Type") or ""
                if r.status == 200 and must_contain in ctype:
                    return r.read()
                print(f"Download attempt {attempt}: unexpected response {r.status} {ctype}")
        except Exception as e:  # noqa: BLE001
            print(f"Download attempt {attempt} failed: {e}")
    return None


# ---------------------------------------------------------------- email helpers
P = 'style="margin:0 0 14px;line-height:1.5"'
H = 'style="margin:22px 0 8px;font-size:15px"'


def img(cids: dict, key: str, alt: str) -> str:
    if key not in cids:
        return ""
    return (f'<img src="cid:{cids[key][1:-1]}" alt="{alt}" width="1000" '
            f'style="width:100%;max-width:1000px;height:auto;display:block;'
            f'border:1px solid #D0D7DE;border-radius:6px;margin:8px 0 18px 0">')


def warning_html(live: bool, status: dict) -> str:
    if live:
        return ""
    return ('<p style="color:#B42318;margin:0 0 14px"><b>Note:</b> some dashboard data did not load live '
            f'at capture time ({status.get("status")}). Please check the live dashboard for current figures.</p>')


def body_bryan(cids, now, live, status, attached):
    files = "".join(f"<li>{name}</li>" for name in attached)
    files_html = (f'<p style="margin:0 0 6px">Attached for your action:</p>'
                  f'<ul style="margin:0 0 14px;padding-left:20px;line-height:1.6">{files}</ul>') if attached else ""
    html = f"""<html><body style="font-family:Arial,Helvetica,sans-serif;font-size:14px;color:#1F2328">
{warning_html(live, status)}
<p {P}>Hi Bryan,</p>
<p {P}>Please find the pending details of Unshipped and Unaccounted Inventory for your reference and necessary action.</p>

<p {H}><b>1. Unshipped Inventory</b></p>
<p {P}>It is important to ensure that all unshipped inventory is dispatched at the earliest. We request you to maintain a 24-hour turnaround time (TAT) for processing and shipping these orders. Delays in shipment can negatively impact our marketplace On-Time Delivery Rate (OTDR) metrics and may result in negative customer feedback.</p>
{img(cids, "unshipped", "Pending Outgoing and Ageing Unshipped")}

<p {H}><b>2. Unaccounted Inventory</b></p>
<p {P}>Vendors expect unaccounted inventory to be returned within seven days. Timely identification and processing of this inventory are essential to ensure it is returned to the respective vendors within the expected timeline. Additionally, the sooner the inventory is accounted for and made available in the system, the sooner we can list the products and make them available for sale.</p>
{img(cids, "unaccounted", "Ageing Range of Unaccounted Item")}
{files_html}
<p {P}>Live dashboard with the full unaccounted inventory details: <a href="{BRYAN_URL}">{BRYAN_URL}</a></p>

<p {P}>Our objective is to keep both unshipped and unaccounted inventory levels as low as possible through timely processing, regular monitoring, and prompt action.</p>
<p {P}>Your support in maintaining these timelines and ensuring consistent follow-up will be greatly appreciated.</p>
<p {P}>Best regards,<br>Warehouse Team - Virventures</p>
</body></html>"""
    text = ("Hi Bryan,\n\nPlease find the pending details of Unshipped and Unaccounted Inventory for your "
            "reference and necessary action. The dashboard images are in the HTML version of this email, "
            "and the unaccounted inventory details are attached.\n\n"
            f"Live dashboard: {BRYAN_URL}\n\nBest regards,\nWarehouse Team - Virventures")
    return "Action required by Bryan for Unshipped orders and Unaccounted inventory", html, text


def build_email(name: str, status: dict):
    report = REPORTS[name]
    now = datetime.now(IST)
    live = report["live"](status)
    smtp_user = os.environ["SMTP_USER"]

    shots = {k: f"{OUT_DIR}/{k}.png" for k, _ in report["sections"] if os.path.exists(f"{OUT_DIR}/{k}.png")}
    cids = {k: make_msgid(domain="virventures.dashboard") for k in shots}

    attachments = []  # (bytes, maintype, subtype, filename)
    # attachments: unaccounted details (Excel) + unshipped orders (CSV)
    if True:
        xlsx = download(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx", "spreadsheet")
        if xlsx:
            attachments.append((xlsx, "application",
                                "vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                f"Unaccounted-Inventory-Details-{now:%Y-%m-%d}.xlsx"))
        zoho = download(BRYAN_URL + ".netlify/functions/get-zoho?format=csv", "csv")
        if zoho:
            attachments.append((zoho, "text", "csv", f"Unshipped-Orders-VVI_FBM-{now:%Y-%m-%d}.csv"))
        subject, html, text = body_bryan(cids, now, live, status, [a[3] for a in attachments])

    to = [e for e in report["to"] if e]
    cc = [e for e in report["cc"] if e]
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.environ.get("MAIL_FROM") or f"Warehouse Team - Virventures <{smtp_user}>"
    msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")
    related = msg.get_payload()[1]
    for k, path in shots.items():
        with open(path, "rb") as f:
            related.add_related(f.read(), maintype="image", subtype="png", cid=cids[k])
    for data, main, sub, fname in attachments:
        msg.add_attachment(data, maintype=main, subtype=sub, filename=fname)
    return msg, to + cc


def send(msg: EmailMessage, recipients: list):
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT") or 587)
    user, password = os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"]
    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=60) as s:
            s.login(user, password)
            s.send_message(msg, to_addrs=recipients)
    else:
        with smtplib.SMTP(host, port, timeout=60) as s:
            s.starttls()
            s.login(user, password)
            s.send_message(msg, to_addrs=recipients)


if __name__ == "__main__":
    which = "bryan"
    if which not in REPORTS:
        sys.exit(f"Unknown email '{which}'. Use one of: {', '.join(REPORTS)}")
    OUT_DIR = os.path.join("shots", which)
    st = capture(REPORTS[which])
    print(f"[{which}] capture status:", st)
    if os.environ.get("SKIP_EMAIL") == "1":
        print("SKIP_EMAIL=1, screenshots saved only.")
        sys.exit(0)
    message, rcpts = build_email(which, st)
    send(message, rcpts)
    print(f"[{which}] sent to {len(rcpts)} recipient(s).")
