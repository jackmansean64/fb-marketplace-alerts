import argparse
import os
import re
import random
import smtplib
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import schedule
from bs4 import BeautifulSoup as soup
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

from config import AlertFrequency, SearchConfig, load_config


def send_email(config, all_results: dict[str, list[dict]]):
    """Send a single HTML email containing results for all searches."""
    load_dotenv()
    password = os.getenv("GOOGLE_APP_PASSWORD")

    message = MIMEMultipart("alternative")
    message["Subject"] = "New Facebook Marketplace Listings"
    message["From"] = config.email.sender_email
    message["To"] = config.email.receiver_email

    html_parts = ["<html><body>"]
    total = 0
    for search_query, listings in all_results.items():
        total += len(listings)
        html_parts.append(f"<h2>{search_query} — {len(listings)} listings</h2><ul>")
        for listing in listings:
            details = " — ".join(listing["details"]) if listing.get("details") else ""
            location = listing.get("location", "")
            loc_str = f" ({location})" if location else ""
            html_parts.append(
                f"<li><a href='{listing['url']}'>{details} - {listing['price']}{loc_str}</a></li>"
            )
        html_parts.append("</ul>")
    html_parts.append("</body></html>")

    if total == 0:
        print("No listings found across all searches. Skipping email.")
        return

    part = MIMEText("".join(html_parts), "html")
    message.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(config.email.sender_email, password)
        server.sendmail(
            config.email.sender_email, config.email.receiver_email, message.as_string()
        )
    print(f"Email sent with {total} total listings.")


def create_driver() -> webdriver.Chrome:
    """Create and return a Selenium WebDriver with anti-detection flags."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1920,16384")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.7680.80 Safari/537.36"
    )
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
    )
    return driver


def count_listings_in_dom(driver) -> int:
    """Count unique marketplace listing links currently in the DOM."""
    return driver.execute_script("""
        const links = document.querySelectorAll('a[href*="/marketplace/item/"]');
        const urls = new Set();
        links.forEach(a => urls.add(a.href.split('?')[0]));
        return urls.size;
    """)


def scrape_search(driver, search: SearchConfig) -> list[dict]:
    """Run a single search and return the parsed listings."""
    url = search.build_url()
    print(f"\nSearching for: {search.query}\n{url}")
    driver.get(url)

    # Simulate human-like initial wait
    time.sleep(random.uniform(3, 6))

    # Close the pop-up if it appears
    try:
        close_button = driver.find_element(By.CSS_SELECTOR, 'div[aria-label="Close"]')
        close_button.click()
        time.sleep(random.uniform(0.5, 1.5))
    except Exception:
        pass

    # Scroll down with human-like behavior until we have enough listings
    print("Loading results", end="", flush=True)
    last_height = driver.execute_script("return document.body.scrollHeight")
    stale_count = 0
    max_stale = 5
    while True:
        current_count = count_listings_in_dom(driver)
        if current_count >= search.max_listings:
            print(f" {current_count} listings loaded.", end="")
            break

        scroll_amount = random.randint(800, 2000)
        driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        time.sleep(random.uniform(0.3, 0.8))

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(2, 5))

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            stale_count += 1
            if stale_count >= max_stale:
                break
        else:
            stale_count = 0
        last_height = new_height
        print(".", end="", flush=True)
    print(" done.")

    # Parse the HTML
    html = driver.page_source
    market_soup = soup(html, "html.parser")

    # Extract listings by finding marketplace item links
    listing_links = market_soup.find_all("a", href=re.compile(r"/marketplace/item/\d+"))

    listings: list[dict] = []
    seen_urls: set[str] = set()
    for link in listing_links:
        if len(listings) >= search.max_listings:
            break

        href = link.get("href", "")
        full_url = "https://www.facebook.com" + href.split("?")[0]

        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        spans = link.find_all("span")
        texts = list(dict.fromkeys(s.text.strip() for s in spans if s.text.strip()))

        price = texts[0] if texts else "N/A"
        details = [t for t in texts if not t.startswith("CA$")]
        location = texts[2] if len(texts) > 2 else ""

        # Filter by allowed locations (case-insensitive substring match)
        if search.allowed_locations:
            loc_lower = location.lower()
            if not any(allowed.lower() in loc_lower for allowed in search.allowed_locations):
                continue

        # Filter by required title keywords (case-insensitive substring match)
        if search.required_in_title:
            title = texts[1].lower() if len(texts) > 1 else ""
            if not any(req.lower() in title for req in search.required_in_title):
                continue

        listings.append({"details": details, "price": price, "location": location, "url": full_url})

    print(f"Found {len(listings)} listings for '{search.query}'.")
    return listings


# ---------------------------------------------------------------------------
# Scheduling
# ---------------------------------------------------------------------------

FREQUENCY_HOURS = {
    AlertFrequency.HOURLY: 1,
    AlertFrequency.DAILY: 24,
    AlertFrequency.WEEKLY: 168,
    AlertFrequency.MONTHLY: 720,
}


def run_once():
    """Run all searches and send the alert email once."""
    config = load_config()
    print(f"\n{'=' * 60}")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting scrape run")
    print(f"Running {len(config.searches)} search(es)...")
    print(f"{'=' * 60}")

    driver = create_driver()
    try:
        all_results: dict[str, list[dict]] = {}
        for search in config.searches:
            listings = scrape_search(driver, search)
            all_results[search.query] = listings
    finally:
        driver.quit()

    send_email(config, all_results)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Run complete.")


def run_scheduled():
    """Run once immediately, then repeat on the configured schedule."""
    config = load_config()
    hours = FREQUENCY_HOURS[config.alert_frequency]

    print(f"Alert frequency: {config.alert_frequency.value} (every {hours}h)")
    print(f"Running initial scrape now, then repeating every {hours} hour(s).")
    print("Press Ctrl+C to stop.\n")

    # Run immediately on startup
    run_once()

    # Schedule future runs
    schedule.every(hours).hours.do(run_once)

    try:
        while True:
            next_run = schedule.next_run()
            if next_run:
                print(f"\nNext run at: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            # Sleep in short intervals so Ctrl+C is responsive
            while not schedule.idle_seconds() or schedule.idle_seconds() > 0:
                schedule.run_pending()
                time.sleep(30)
    except KeyboardInterrupt:
        print("\nShutting down scheduler.")


def main():
    parser = argparse.ArgumentParser(description="Facebook Marketplace Alerts")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single scrape and exit (no background scheduling)",
    )
    args = parser.parse_args()

    if args.once:
        run_once()
    else:
        run_scheduled()


if __name__ == "__main__":
    main()
