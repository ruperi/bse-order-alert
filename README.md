# BSE Order Alert

A Python-based open-source tool for monitoring BSE announcements and tracking new announcements that require attention.

## Overview

**BSE Order Alert** is designed to periodically check BSE announcements and identify announcements that have not been seen previously.

The project keeps track of previously processed announcements using a local JSON file, helping prevent the same announcements from being repeatedly reported.

## Features

* Monitor BSE announcements
* Detect new announcements
* Keep track of previously seen announcements
* Python-based implementation
* Automated execution using GitHub Actions
* Lightweight and easy to customise
* Open-source under the MIT License

## Project Structure

```text
bse-order-alert/
├── .github/
│   └── workflows/
│       └── bse-order-alert.yml
├── bse_order_alert.py
├── requirements.txt
├── seen_announcements.json
├── LICENSE
└── README.md
```

## Requirements

* Python 3.x
* Internet connection
* Python packages listed in `requirements.txt`

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

## Usage

Run the Python script:

```bash
python bse_order_alert.py
```

The script checks for announcements and uses `seen_announcements.json` to keep track of announcements that have already been processed.

## Automated Execution

The repository includes a GitHub Actions workflow under:

```text
.github/workflows/bse-order-alert.yml
```

This allows the project to run automatically through GitHub Actions rather than requiring the script to be started manually each time.

## Data Tracking

The file:

```text
seen_announcements.json
```

stores information about announcements that have already been processed.

This helps the application identify new announcements during subsequent runs.

## Customisation

You can modify `bse_order_alert.py` to adapt the project to your own workflow, notification requirements, filtering logic, or additional BSE announcement types.

## Contributing

Contributions and suggestions are welcome.

To contribute:

1. Fork the repository.
2. Create a new branch.
3. Make your changes.
4. Test your changes.
5. Submit a pull request.

## Disclaimer

This project is provided for informational and educational purposes. Users should independently verify information obtained from BSE announcements before making any financial or investment decisions.

## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.
