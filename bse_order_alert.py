#!/usr/bin/env python3
"""
BSE Order Announcement Alert

Monitors BSE's "Company Update -> Award of Order / Receipt of Order"
corporate announcements and sends email alerts for new filings.
"""

import json
import os
import re
import smtplib
import requests
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


# ============================================================
# CONFIGURATION
# ============================================================

SEEN_FILE = "seen_announcements.json"

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
ALERT_TO = os.getenv("ALERT_TO")


# ============================================================
# BSE API CONFIGURATION
# ============================================================

BSE_API_URL = (
    "https://api.bseindia.com/"
    "BseIndiaAPI/api/AnnSubCategoryGetData/w"
)

BSE_BASE_URL = "https://www.bseindia.com"

# BSE was timing out at 30 seconds, so we increased this.
REQUEST_TIMEOUT = 90


# ============================================================
# ORDER KEYWORDS
# ============================================================

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
]


# ============================================================
# LOAD / SAVE SEEN ANNOUNCEMENTS
# ============================================================

def load_seen_announcements():
    """Load previously seen announcements from JSON file."""

    if os.path.exists(SEEN_FILE):

        with open(SEEN_FILE, "r", encoding="utf-8") as f:

            try:
                return set(json.load(f))

            except json.JSONDecodeError:
                return set()

    return set()


def save_seen_announcements(seen_set):
    """Save seen announcements to JSON file."""

    with open(SEEN_FILE, "w", encoding="utf-8") as f:

        json.dump(
            sorted(list(seen_set)),
            f,
            indent=2,
            ensure_ascii=False
        )


# ============================================================
# TEXT NORMALISATION
# ============================================================

def normalise_text(value):
    """
    Normalise BSE text for reliable keyword matching.

    Example:

    Award_of_Order_Receipt_of_Order

    becomes:

    award of order receipt of order
    """

    if value is None:
        return ""

    text = str(value).lower()

    # Replace underscores, hyphens and slashes with spaces
    text = re.sub(r"[_\-/]+", " ", text)

    # Remove other special characters
    text = re.sub(r"[^a-z0-9]+", " ", text)

    # Remove duplicate spaces
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def contains_order_keyword(*values):
    """
    Check whether supplied BSE fields contain
    an order-related keyword.
    """

    combined_text = normalise_text(
        " ".join(str(v or "") for v in values)
    )

    return any(
        keyword in combined_text
        for keyword in ORDER_KEYWORDS
    )


# ============================================================
# BSE FIELD HELPER
# ============================================================

def first_value(ann, *keys):
    """
    Return the first non-empty value from possible
    BSE field names.
    """

    for key in keys:

        value = ann.get(key)

        if value is not None and str(value).strip():

            return value

    return ""


# ============================================================
# FETCH BSE ANNOUNCEMENTS
# ============================================================

def fetch_today_announcements():
    """
    Fetch the latest BSE corporate announcements.

    We intentionally fetch only the first page because the
    BSE feed is sorted with the latest announcements first.
    The workflow runs every 5 minutes, so downloading every
    announcement from the entire day is unnecessary and can
    exceed GitHub Actions' execution limit.
    """

    today = datetime.now()
    date_str = today.strftime("%Y%m%d")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/134.0.0.0 Safari/537.3"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.5",
        "Origin": BSE_BASE_URL,
        "Referer": BSE_BASE_URL + "/",
        "Connection": "keep-alive",
    }

    params = {
        "pageno": 1,
        "strCat": "-1",
        "subcategory": "-1",
        "strPrevDate": date_str,
        "strToDate": date_str,
        "strSearch": "P",
        "strScrip": "",
        "strType": "C",
    }

    try:
        print("Fetching latest BSE announcements...")

        response = requests.get(
            BSE_API_URL,
            params=params,
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        data = response.json()

        table = data.get("Table", [])

        if not table:
            raise RuntimeError(
                "BSE API returned no announcements."
            )

        print(
            f"BSE returned {len(table)} announcements "
            "from the latest page."
        )

        return table

    except requests.exceptions.Timeout:
        raise RuntimeError(
            f"BSE API request timed out after "
            f"{REQUEST_TIMEOUT} seconds."
        )

    except requests.exceptions.RequestException as e:
        raise RuntimeError(
            f"BSE API request failed: {e}"
        )

    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"BSE API returned invalid JSON: {e}"
        )


# ============================================================
# FILTER ORDER ANNOUNCEMENTS
# ============================================================

def filter_order_announcements(announcements):
    """
    Filter BSE announcements using the actual
    BSE API field names.

    Known BSE fields include:

    CATEGORYNAME
    SUBCATNAME
    NEWSSUB
    HEADLINE
    SCRIP_CD
    SLONGNAME
    News_submission_dt
    DissemDT
    ATTACHMENTNAME
    NEWSID
    """

    order_announcements = []


    for ann in announcements:


        # ----------------------------------------------------
        # CATEGORY
        # ----------------------------------------------------

        category = first_value(

            ann,

            "CATEGORYNAME",

            "category",

            "CATEGORY",
        )


        # ----------------------------------------------------
        # SUBCATEGORY
        # ----------------------------------------------------

        subcategory = first_value(

            ann,

            "SUBCATNAME",

            "subcategory",

            "SUB_CATEGORY",
        )


        # ----------------------------------------------------
        # NEWS SUBJECT
        # ----------------------------------------------------

        news_sub = first_value(

            ann,

            "NEWSSUB",

            "headline",

            "HEADLINE",
        )


        # ----------------------------------------------------
        # HEADLINE
        # ----------------------------------------------------

        headline = first_value(

            ann,

            "HEADLINE",

            "headline",

            "NEWSSUB",
        )


        # ----------------------------------------------------
        # COMPANY UPDATE ONLY
        # ----------------------------------------------------

        if (
            "company update"
            not in normalise_text(category)
        ):

            continue


        # ----------------------------------------------------
        # ORDER / CONTRACT FILTER
        # ----------------------------------------------------

        if not contains_order_keyword(

            subcategory,

            news_sub,

            headline

        ):

            continue


        # ----------------------------------------------------
        # COMPANY CODE
        # ----------------------------------------------------

        scrip_code = first_value(

            ann,

            "SCRIP_CD",

            "scrip_code",
        )


        # ----------------------------------------------------
        # COMPANY NAME
        # ----------------------------------------------------

        scrip_name = first_value(

            ann,

            "SLONGNAME",

            "SCRIP_NAME",

            "scrip_name",
        )


        # ----------------------------------------------------
        # DATE
        # ----------------------------------------------------

        announcement_date = first_value(

            ann,

            "News_submission_dt",

            "DissemDT",

            "NEWS_DT",

            "ANNOUNCEMENT_DATE",
        )


        # ----------------------------------------------------
        # NEWS ID
        # ----------------------------------------------------

        news_id = first_value(

            ann,

            "NEWSID",

            "newsid",
        )


        # ----------------------------------------------------
        # PDF ATTACHMENT
        # ----------------------------------------------------

        attachment = first_value(

            ann,

            "ATTACHMENTNAME",

            "pdf_url",
        )


        # ----------------------------------------------------
        # UNIQUE ID
        # ----------------------------------------------------

        if str(news_id).strip():

            unique_id = str(
                news_id
            ).strip()

        else:

            unique_id = (
                f"{scrip_code}|"
                f"{news_sub}|"
                f"{announcement_date}"
            )


        # ----------------------------------------------------
        # PDF URL
        # ----------------------------------------------------

        if attachment:

            attachment = str(
                attachment
            ).strip()


            if attachment.startswith(
                "http://"
            ) or attachment.startswith(
                "https://"
            ):

                pdf_url = attachment


            elif attachment.startswith("/"):

                pdf_url = (
                    BSE_BASE_URL
                    + attachment
                )


            else:

                pdf_url = (
                    BSE_BASE_URL
                    + "/xml-data/corpfiling/"
                    + "AttachLive/"
                    + attachment
                )

        else:

            pdf_url = ""


        # ----------------------------------------------------
        # STORE ANNOUNCEMENT
        # ----------------------------------------------------

        order_announcements.append({

            "id": unique_id,

            "scrip_code": str(
                scrip_code
            ),

            "scrip_name": str(
                scrip_name
            ),

            "headline": str(
                headline
            ),

            "subcategory": str(
                subcategory
            ),

            "category": str(
                category
            ),

            "date": str(
                announcement_date
            ),

            "pdf_url": pdf_url,

        })


    return order_announcements


# ============================================================
# SEND EMAIL
# ============================================================

def send_email_alert(new_announcements):
    """
    Send email alert for new order announcements.
    """

    # Check SMTP configuration
    if not all([

        SMTP_HOST,

        SMTP_USER,

        SMTP_PASS,

        ALERT_TO

    ]):

        print(
            "Error: Missing SMTP configuration. "
            "Check GitHub Secrets."
        )

        return False


    if not new_announcements:

        print(
            "No new announcements to alert."
        )

        return True


    # --------------------------------------------------------
    # EMAIL SUBJECT
    # --------------------------------------------------------

    subject = (
        "BSE Order Alert: "
        f"{len(new_announcements)} "
        "new announcement(s)"
    )


    # --------------------------------------------------------
    # EMAIL BODY
    # --------------------------------------------------------

    body_lines = [

        (
            f"Found {len(new_announcements)} "
            "new order-related announcement(s) "
            "on BSE:\n"
        ),

        "=" * 60,

    ]


    for ann in new_announcements:


        body_lines.append(

            f"\nCompany: "
            f"{ann['scrip_name']} "
            f"({ann['scrip_code']})"

        )


        body_lines.append(

            f"Headline: "
            f"{ann['headline']}"

        )


        body_lines.append(

            f"Subcategory: "
            f"{ann['subcategory']}"

        )


        body_lines.append(

            f"Date: "
            f"{ann['date']}"

        )


        if ann["pdf_url"]:

            body_lines.append(

                f"PDF: "
                f"{ann['pdf_url']}"

            )


        body_lines.append(
            "-" * 40
        )


    body_lines.append(

        "\nAlert generated at "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    )


    body_lines.append(

        "Source: BSE Corporate Announcements "
        "(Company Update -> "
        "Award/Receipt of Order)"

    )


    body = "\n".join(
        body_lines
    )


    # --------------------------------------------------------
    # CREATE EMAIL
    # --------------------------------------------------------

    msg = MIMEMultipart()

    msg["From"] = SMTP_USER

    msg["To"] = ALERT_TO

    msg["Subject"] = subject


    msg.attach(

        MIMEText(
            body,
            "plain",
            "utf-8"
        )

    )


    # --------------------------------------------------------
    # SEND EMAIL
    # --------------------------------------------------------

    try:

        with smtplib.SMTP(

            SMTP_HOST,

            SMTP_PORT,

            timeout=30

        ) as server:

            server.starttls()

            server.login(
                SMTP_USER,
                SMTP_PASS
            )

            server.send_message(
                msg
            )


        print(
            f"Email sent successfully "
            f"to {ALERT_TO}"
        )


        return True


    except Exception as e:

        print(
            f"Error sending email: {e}"
        )

        return False


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        f"[{datetime.now()}] "
        "Starting BSE Order Announcement check..."
    )


    # --------------------------------------------------------
    # LOAD SEEN
    # --------------------------------------------------------

    seen = load_seen_announcements()


    print(
        f"Loaded {len(seen)} "
        "previously seen announcements"
    )


    # --------------------------------------------------------
    # FETCH BSE
    # --------------------------------------------------------

    # If BSE cannot be reached, this raises an error
    # instead of falsely treating the result as zero.

    all_announcements = (
        fetch_today_announcements()
    )


    print(
        f"Fetched "
        f"{len(all_announcements)} "
        "total announcements for today"
    )


    # --------------------------------------------------------
    # FILTER
    # --------------------------------------------------------

    order_announcements = (
        filter_order_announcements(
            all_announcements
        )
    )


    print(
        f"Found "
        f"{len(order_announcements)} "
        "order-related announcements"
    )


    # --------------------------------------------------------
    # FIND NEW ANNOUNCEMENTS
    # --------------------------------------------------------

    new_announcements = []


    for ann in order_announcements:

        if ann["id"] not in seen:

            new_announcements.append(
                ann
            )


    print(
        f"New announcements: "
        f"{len(new_announcements)}"
    )


    # --------------------------------------------------------
    # EMAIL NEW ANNOUNCEMENTS
    # --------------------------------------------------------

    if new_announcements:

        if send_email_alert(
            new_announcements
        ):

            # Only mark as seen AFTER
            # email was successfully sent.

            for ann in new_announcements:

                seen.add(
                    ann["id"]
                )


            save_seen_announcements(
                seen
            )


            print(
                "Seen announcements updated"
            )


        else:

            print(
                "Email failed - seen "
                "announcements NOT updated "
                "(will retry next run)"
            )


            raise RuntimeError(
                "Email delivery failed"
            )


    else:

        print(
            "No new order announcements "
            "to report"
        )


    print(
        f"[{datetime.now()}] "
        "Check complete"
    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    main()
