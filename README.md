# Facebook Marketplace Alerts

Scrapes Facebook Marketplace listings and sends email notifications with results. Supports multiple searches with filters for price, location, vehicle details, and more.

## Prerequisites

- Python 3.10+
- Google Chrome installed
- A [Mailgun](https://www.mailgun.com/) account with a verified sending domain

## Setup

1. **Create a virtual environment and install dependencies:**

   ```bash
   cd marketplace-notifications
   python -m venv ../.venv
   source ../.venv/bin/activate   # On Windows: ..\.venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Set up Mailgun and create a `.env` file.**

   Sign up at [mailgun.com](https://www.mailgun.com/) and verify a sending
   domain. Then copy `.env.example` to `.env` in the
   `marketplace-notifications/` directory and fill in your Mailgun values:

   ```bash
   cp .env.example .env
   ```

   The variables you need to provide are:

   - `MAILGUN_API_KEY` — your Mailgun private API key.
   - `MAILGUN_DOMAIN` — the sending domain you verified in Mailgun.
   - `MAILGUN_FROM_ADDRESS` — the address alerts will be sent from (must be
     on your Mailgun domain).

3. **Create your config file** by copying the example:

   ```bash
   cp config.example.yaml config.yaml
   ```

   Edit `config.yaml` to set your `recipient_email` (the address that will
   receive alerts), search queries, location, price range, and any other
   filters. See `config.example.yaml` for all available options.

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