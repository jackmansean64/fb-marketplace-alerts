import os

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup as soup
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import time
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

    html = "<html><body><h2>New Listings Found:</h2><ul>"
    for listing in new_listings:
        html += f"<li><a href='{listing['url']}'>{listing['title']} - {listing['price']}</a></li>"
    html += "</ul></body></html>"

    part = MIMEText(html, "html")
    message.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message.as_string())

# Set up Selenium WebDriver
chrome_options = Options()
chrome_options.add_argument("--headless")  # Run in headless mode for faster execution
service = Service(r'C:\Git\marketplace-alerts\marketplace-notifications\chromedriver-win64\chromedriver.exe')  # Path to your chromedriver executable
driver = webdriver.Chrome(service=service, options=chrome_options)

# Set up base URL and search parameters
base_url = "https://www.facebook.com/marketplace/victoria/search?"
search_params = {
    # "minPrice": 100,
    # "maxPrice": 100000,
    "daysSinceListed": 1,
    # "minMileage": 0,
    # "maxMileage": 500000,
    # "minYear": 1990,
    # "maxYear": 2025,
    "query": "Men's golf irons",
    "exact": "false"
}
url = base_url + "&".join([f"{key}={value}" for key, value in search_params.items()])

# Visit the website
driver.get(url)

# Close the pop-up if it appears
time.sleep(5)  # Allow time for the page to load
try:
    close_button = driver.find_element(By.CSS_SELECTOR, 'div[aria-label="Close"]')
    close_button.click()
except Exception as e:
    print("No pop-up found.")

# Scroll down to load more results
scroll_count = 4
scroll_delay = 2
for _ in range(scroll_count):
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(scroll_delay)

# Parse the HTML
html = driver.page_source
market_soup = soup(html, 'html.parser')
driver.quit()

html = market_soup.prettify()

# Extract all the necessary info and insert into lists
titles_div = market_soup.find_all('span', class_='x1lliihq x6ikm8r x10wlt62 x1n2onr6')
prices_div = market_soup.find_all('span', class_='x193iq5w xeuugli x13faqbe x1vvkbs x1xmvt09 x1lliihq x1s928wv xhkezso x1gmr53x x1cpjm7i x1fgarty x1943h6x xudqn12 x676frb x1lkfr7t x1lbecb7 x1s688f xzsf02u')
urls_div = market_soup.find_all('a', class_='x1i10hfl xjbqb8w x1ejq31n xd10rxx x1sy0etr x17r0tee x972fbf xcfux6l x1qhh985 xm0m39n x9f619 x1ypdohk xt0psk2 xe8uvvx xdj266r x11i5rnm xat24cr x1mh8g0r xexx8yu x4uap5 x18d9i69 xkhd6sd x16tdsg8 x1hl2dhg xggy1nq x1a2a7pz x1heor9g x1sur9pj xkrqix3 x1lku1pv')

titles_list = [title.text.strip() for title in titles_div]
prices_list = [price.text.strip() for price in prices_div]
urls_list = ["https://www.facebook.com" + url.get('href') for url in urls_div]

new_listings = []
for title, price, url in zip(titles_list, prices_list, urls_list):
    new_listings.append({"title": title, "price": price, "url": url})

# Send email alerts if new listings are found
if new_listings:
    send_email(new_listings)
else:
    print("No new listings found.")
