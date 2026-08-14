#!/usr/bin/env python3
"""
BSE Order Announcement Alert

Monitors BSE's "Company Update -> Award of Order / Receipt of Order"
corporate announcements and sends email alerts for new filings.
"""

import json
import os
import sys
import smtplib
import tempfile
import requests
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configuration
SEEN_FILE = "seen_announcements.json"
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
ALERT_TO = os.getenv("ALERT_TO")

# BSE API Configuration
BSE_API_URL = "https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w"
BSE_BASE_URL = "https://www.bseindia.com"
REQUEST_TIMEOUT = 90  # seconds

# Keywords to match in announcement headlines/subcategories
ORDER_KEYWORDS = [
    "award of order",
    "receipt of order",
    "award of contract",
    "receipt of contract",
    "order received",
    "order awarded",
    "work order",
    "purchase order",
    "letter of award",
    "letter of intent",
    "loa",
    "loi",
]


def load_seen_announcements():
    """Load previously seen announcements from JSON file."""
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            try:
                return set(json.load(f))
            except json.JSONDecodeError:
                return set()
    return set()


def save_seen_announcements(seen_set):
    """Save seen announcements to JSON file."""
    with open(SEEN_FILE, "w") as f:
        json.dump(sorted(list(seen_set)), f, indent=2)


def is_order_related(headline, subcategory):
    """Check if announcement is related to order/contract awards."""
    text = f"{headline} {subcategory}".lower()
    return any(keyword in text for keyword in ORDER_KEYWORDS)


def fetch_today_announcements():
    """Fetch today's corporate announcements from BSE API directly."""
    today = datetime.now()
    date_str = today.strftime("%Y%m%d")

    # Headers to mimic browser request
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.3",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.5",
        "Origin": BSE_BASE_URL,
        "Referer": BSE_BASE_URL + "/",
        "Connection": "keep-alive",
    }

    # Parameters matching the bse library's announcements method
    params = {
        "pageno": 1,
        "strCat": "-1",       # All categories
        "subcategory": "-1",  # All subcategories
        "strPrevDate": date_str,
        "strToDate": date_str,
        "strSearch": "P",
        "strscrip": "",
        "strType": "C",       # 'C' for equity segment
    }

    all_announcements = []
    page_no = 1

    try:
        while True:
            params["pageno"] = page_no
            response = requests.get(
                BSE_API_URL,
                params=params,
                headers=headers,
                timeout=REQUEST_TIMEOUT
            )

            if not response.ok:
                print(f"HTTP error: {response.status_code} - {response.reason}")
                break

            try:
                data = response.json()
            except json.JSONDecodeError:
                print("Failed to parse JSON response")
                break

            # Check if we got valid data
            table = data.get("Table", [])
            if not table:
                break

            all_announcements.extend(table)

            # Check if there are more pages using Table1[0]['ROWCNT']
            table1 = data.get("Table1", [])
            if table1 and "ROWCNT" in table1[0]:
                total_rows = table1[0]["ROWCNT"]
                if len(all_announcements) >= total_rows:
                    break
            else:
                # If no ROWCNT, assume this is the last page if less than 50 items
                if len(table) < 50:
                    break

            page_no += 1

            # Safety limit to avoid infinite loops
            if page_no > 100:
                print("Warning: Reached max page limit (100)")
                break

    except requests.exceptions.Timeout:
        print(f"Error fetching announcements: Request timed out after {REQUEST_TIMEOUT}s")
        return []
    except requests.exceptions.RequestException as e:
        print(f"Error fetching announcements: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []

    return all_announcements


def filter_order_announcements(announcements):
    """Filter announcements for order/contract related ones."""
    order_announcements = []

    for ann in announcements:
        # Handle different possible field names from BSE API
        headline = ann.get("headline", "") or ann.get("HEADLINE", "") or ""
        subcategory = ann.get("subcategory", "") or ann.get("SUB_CATEGORY", "") or ""
        category = ann.get("category", "") or ann.get("CATEGORY", "") or ""
        scrip_code = ann.get("scrip_code", "") or ann.get("SCRIP_CD", "") or ""
        scrip_name = ann.get("scrip_name", "") or ann.get("SCRIP_NAME", "") or ""
        announcement_date = ann.get("announcement_date", "") or ann.get("ANNOUNCEMENT_DATE", "") or ""
        pdf_url = ann.get("pdf_url", "") or ann.get("ATTACHMENTNAME", "") or ""

        # Only keep "Company Update" category
        if "company update" not in category.lower():
            continue

        if is_order_related(headline, subcategory):
            # Create a unique identifier for deduplication
            unique_id = f"{scrip_code}|{headline}|{announcement_date}"

            order_announcements.append({
                "id": unique_id,
                "scrip_code": scrip_code,
                "scrip_name": scrip_name,
                "headline": headline,
                "subcategory": subcategory,
                "category": category,
                "date": announcement_date,
                "pdf_url": pdf_url,
            })

    return order_announcements


def send_email_alert(new_announcements):
    """Send email alert for new order announcements."""
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASS, ALERT_TO]):
        print("Error: Missing SMTP configuration. Check environment variables.")
        return False

    if not new_announcements:
        print("No new announcements to alert.")
        return True

    # Build email content
    subject = f"🔔 BSE Order Alert: {len(new_announcements)} new announcement(s)"

    body_lines = [
        f"Found {len(new_announcements)} new order-related announcement(s) on BSE:\n",
        "=" * 60,
    ]

    for ann in new_announcements:
        body_lines.append(f"\n📊 Company: {ann['scrip_name']} ({ann['scrip_code']})")
        body_lines.append(f"📌 Headline: {ann['headline']}")
        body_lines.append(f"📂 Subcategory: {ann['subcategory']}")
        body_lines.append(f"📅 Date: {ann['date']}")
        if ann['pdf_url']:
            body_lines.append(f"📎 PDF: https://www.bseindia.com{ann['pdf_url']}")
        body_lines.append("-" * 40)

    body_lines.append(f"\n\n---\nAlert generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    body_lines.append("Source: BSE Corporate Announcements (Company Update -> Award/Receipt of Order)")

    body = "\n".join(body_lines)

    # Create message
    msg = MIMEMultipart()
    msg["From"] = SMTP_USER
    msg["To"] = ALERT_TO
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        print(f"Email sent successfully to {ALERT_TO}")
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


def main():
    print(f"[{datetime.now()}] Starting BSE Order Announcement check...")

    # Load previously seen announcements
    seen = load_seen_announcements()
    print(f"Loaded {len(seen)} previously seen announcements")

    # Fetch today's announcements
    all_announcements = fetch_today_announcements()
    print(f"Fetched {len(all_announcements)} total announcements for today")

    # Filter for order-related announcements
    order_announcements = filter_order_announcements(all_announcements)
    print(f"Found {len(order_announcements)} order-related announcements")

    # Find new announcements
    new_announcements = []
    for ann in order_announcements:
        if ann["id"] not in seen:
            new_announcements.append(ann)
            seen.add(ann["id"])

    print(f"New announcements: {len(new_announcements)}")

    # Send email if there are new announcements
    if new_announcements:
        if send_email_alert(new_announcements):
            # Save updated seen list only if email succeeded
            save_seen_announcements(seen)
            print("Seen announcements updated")
        else:
            print("Email failed - seen announcements NOT updated (will retry next run)")
    else:
        print("No new order announcements to report")

    print(f"[{datetime.now()}] Check complete")


if __name__ == "__main__":
    main()
