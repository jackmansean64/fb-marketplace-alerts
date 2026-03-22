import os

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup as soup
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import time
import random
import re
from dotenv import load_dotenv

# Function to send email
def send_email(new_listings):
    load_dotenv()
    sender_email = "jackmansean64@gmail.com"
    receiver_email = "jackmansean64@gmail.com"
    password = os.getenv('GOOGLE_APP_PASSWORD')

    message = MIMEMultipart("alternative")
    message["Subject"] = "New Facebook Marketplace Listings"
    message["From"] = sender_email
    message["To"] = receiver_email

    html = f"<html><body><h2>{len(new_listings)} Listings Found:</h2><ul>"
    for listing in new_listings:
        details = " — ".join(listing['details']) if listing.get('details') else ""
        html += f"<li><a href='{listing['url']}'>{details} - {listing['price']}</a></li>"
    html += "</ul></body></html>"

    part = MIMEText(html, "html")
    message.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message.as_string())

# Set up Selenium WebDriver with anti-detection flags
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--window-size=1920,16384")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.7680.80 Safari/537.36")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option("useAutomationExtension", False)
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)
driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
    "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
})

# Set up base URL and search parameters
base_url = "https://www.facebook.com/marketplace/victoria/search?"
search_params = {
    # "minPrice": 100,
    # "maxPrice": 100000,
    "daysSinceListed": 30,
    # "minMileage": 0,
    "maxMileage": 150000,
    # "minYear": 1990,
    # "maxYear": 2025,
    "query": "Prius V",
    "exact": "false",
    "category_id": 546583916084032
}
url = base_url + "&".join([f"{key}={value}" for key, value in search_params.items()])

# Visit the website
print(f"Searching for: {search_params['query']}\n{url}")
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

# Scroll down with human-like behavior
print("Loading results", end="", flush=True)
last_height = driver.execute_script("return document.body.scrollHeight")
stale_count = 0
max_stale = 5
while True:
    # Scroll in random increments instead of jumping straight to bottom
    scroll_amount = random.randint(800, 2000)
    driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
    time.sleep(random.uniform(0.3, 0.8))

    # Then scroll to bottom to trigger lazy load
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
market_soup = soup(html, 'html.parser')
driver.quit()

# Extract listings by finding marketplace item links (stable URL pattern)
listing_links = market_soup.find_all('a', href=re.compile(r'/marketplace/item/\d+'))

new_listings = []
seen_urls = set()
for link in listing_links:
    href = link.get('href', '')
    full_url = "https://www.facebook.com" + href.split('?')[0]

    # Skip duplicate listings
    if full_url in seen_urls:
        continue
    seen_urls.add(full_url)

    # Extract text content from within the link — deduplicate spans
    spans = link.find_all('span')
    texts = list(dict.fromkeys(s.text.strip() for s in spans if s.text.strip()))

    # Price is first text, remaining non-price texts are details (title, mileage, location, etc.)
    price = texts[0] if texts else "N/A"
    details = [t for t in texts if not t.startswith("CA$")]

    new_listings.append({"details": details, "price": price, "url": full_url})

# Send email alerts if new listings are found
if new_listings:
    print(f"Found {len(new_listings)} listings. Sending email...")
    send_email(new_listings)
    print("Email sent.")
else:
    print("No new listings found.")
