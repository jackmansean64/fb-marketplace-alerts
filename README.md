# Facebook Marketplace Alerts

Scrapes Facebook Marketplace listings and sends email notifications with results. Supports multiple searches with filters for price, location, vehicle details, and more.

## Prerequisites

- Python 3.10+
- Google Chrome installed
- A Gmail account with a [Google App Password](https://support.google.com/accounts/answer/185833) for sending emails

## Setup

1. **Create a virtual environment and install dependencies:**

   ```bash
   cd marketplace-notifications
   python -m venv ../.venv
   source ../.venv/bin/activate   # On Windows: ..\.venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Create a `.env` file** in the `marketplace-notifications/` directory:

   ```
   GOOGLE_APP_PASSWORD = "your-google-app-password"
   ```

3. **Create your config file** by copying the example:

   ```bash
   cp config.example.yaml config.yaml
   ```

   Edit `config.yaml` to set your email addresses, search queries, location, price range, and any other filters. See `config.example.yaml` for all available options.

## Usage

**Background mode (default)** — runs immediately, then repeats on the configured `alert_frequency`:

```bash
cd marketplace-notifications
python main.py
```

**Single run** — scrape once and exit:

```bash
python main.py --once
```

Press `Ctrl+C` to stop background mode.

The script will:
1. Load your searches from `config.yaml`
2. Open a headless Chrome browser and scrape Facebook Marketplace for each search
3. Send a single email with all results to the configured receiver email
4. In background mode, repeat steps 1–3 on the configured schedule