# BSE Order Alert

A Python-based open-source tool that monitors BSE corporate announcements and sends email alerts when new order, contract, or work-order related announcements are detected.

## Overview

**BSE Order Alert** monitors the Bombay Stock Exchange (BSE) corporate announcements feed and identifies announcements related to orders and contracts.

The application checks the latest BSE announcements, filters them for relevant order-related keywords, keeps track of announcements that have already been processed, and sends an email alert when a new matching announcement is found.

The project can run automatically using GitHub Actions.

## Features

* Monitor BSE corporate announcements
* Focus on Company Update announcements
* Detect order and contract related announcements
* Support keywords such as:

  * Award of Order
  * Receipt of Order
  * Award of Contract
  * Receipt of Contract
  * Order Received
  * Order Awarded
  * Work Order
  * Purchase Order
  * Letter of Award
  * Letter of Intent
* Avoid duplicate alerts
* Send email notifications through SMTP
* Store previously processed announcement IDs
* Run automatically with GitHub Actions
* Manual workflow execution supported
* Configurable through environment variables and GitHub Secrets

## How It Works

The application follows this process:

1. Fetch the latest BSE corporate announcements.
2. Filter announcements belonging to the Company Update category.
3. Search announcement fields for order and contract related keywords.
4. Generate a unique identifier for each matching announcement.
5. Compare the identifier with previously processed announcements.
6. Send an email when a new matching announcement is found.
7. Mark the announcement as processed only after successful email delivery.

This prevents an announcement from being lost from the alert system if email delivery fails.

## Requirements

* Python 3.11 or compatible Python 3.x version
* Internet connection
* SMTP email account
* GitHub account if using GitHub Actions

## Installation

Clone the repository:

```bash
git clone https://github.com/ruperi/bse-order-alert.git
cd bse-order-alert
```

Install the required Python packages:

```bash
pip install -r requirements.txt
```

## Configuration

The application reads email configuration from environment variables.

| Variable    | Description                        |
| ----------- | ---------------------------------- |
| `SMTP_HOST` | SMTP server hostname               |
| `SMTP_PORT` | SMTP server port                   |
| `SMTP_USER` | SMTP username/email                |
| `SMTP_PASS` | SMTP password or app password      |
| `ALERT_TO`  | Email address that receives alerts |

### Example

```text
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your-email@example.com
SMTP_PASS=your-app-password
ALERT_TO=alerts@example.com
```

**Never commit real passwords, API keys, or other credentials to the repository.**

## Running Locally

After configuring the required environment variables, run:

```bash
python bse_order_alert.py
```

The program will retrieve the latest BSE announcements and check for new order-related announcements.

## GitHub Actions

The repository includes a GitHub Actions workflow:

```text
.github/workflows/bse-order-alert.yml
```

The workflow can run automatically on a schedule or manually using GitHub's **Run workflow** option.

Email credentials should be configured as GitHub Actions Secrets:

```text
SMTP_HOST
SMTP_PORT
SMTP_USER
SMTP_PASS
ALERT_TO
```

The workflow passes these values to the Python application without storing the actual credentials in the source code.

## Duplicate Detection

The project uses:

```text
seen_announcements.json
```

to store identifiers for announcements that have already been processed.

This prevents the same announcement from generating repeated email alerts.

## Email Alerts

When a new matching announcement is detected, the email contains information such as:

* Company name
* BSE scrip code
* Announcement headline
* Subcategory
* Announcement date
* BSE PDF attachment URL, when available

## BSE Data Source

The application retrieves corporate announcement data from the BSE India corporate announcements API.

The project is an independent open-source tool and is not affiliated with or endorsed by BSE.

## Disclaimer

This project is provided for informational and educational purposes only.

BSE announcements and alerts should not be considered investment advice. Always review the original company announcement and perform your own research before making financial or investment decisions.

## Contributing

Contributions, bug reports, suggestions, and improvements are welcome.

To contribute:

1. Fork the repository.
2. Create a feature branch.
3. Make your changes.
4. Test your changes.
5. Commit your changes.
6. Open a pull request.

## Licence

This project is licensed under the **MIT License**.

See the [LICENSE](LICENSE) file for the complete licence text.
