import time, requests
from bs4 import BeautifulSoup
from colorama import Fore
from utils.translate_util import translate_to_language

def fetch_page_html(url, config):
    headers = {"User-Agent": config["network"]["user_agent"]}
    attempts = config["retry_attempts"]

    for attempt in range(attempts):
        try:
            response = requests.get(url, headers=headers, timeout=config["timeout_seconds"], proxies=config["network"]["proxy"])
            response.raise_for_status()
            time.sleep(config["network"]["delay_between_requests"])
            return response.text
        except Exception as e:
            if config["debug"]["verbose_mode"]:
                print(Fore.YELLOW + f"[retry {attempt+1}/{attempts}] {e}")
            if attempt == attempts - 1:
                raise
            time.sleep(1)

def scrape_product_data(url, config):
    html = fetch_page_html(url, config)
    soup = BeautifulSoup(html, "html.parser")
    item = {}

    product_section = soup.find("div", class_=lambda x: x and "product" in x.lower())
    title_tag = product_section.find("h6") if product_section else None
    title_tag = title_tag or product_section.find("p") if product_section else None
    title_tag = title_tag or soup.find("h6", string=True)

    raw_title = title_tag.get_text(strip=True) if title_tag else "n/a"
    translated_title = translate_to_language(raw_title, config) if config["scraping"]["translate_title"] else raw_title

    item["title_original"] = raw_title
    item["title"] = translated_title.lower()

    def find_field(label):
        tag = soup.find(string=label)
        return tag.find_next().get_text(strip=True) if tag else "n/a"

    if config["scraping"]["include_seller"]:
        item["seller"] = find_field("Seller")
    if config["scraping"]["include_condition"]:
        item["condition"] = find_field("Condition")
    if config["scraping"]["include_shipping"]:
        item["shipping"] = find_field("Domestic Shipping")
    item["item_id"] = find_field("Item ID")

    price_tag = soup.find("span", class_="product-price")
    item["price_yen"] = int("".join(filter(str.isdigit, price_tag.get_text()))) if price_tag else 0

    img_tag = soup.find("img", class_="cloudzoom")
    if config["scraping"]["include_image_url"]:
        item["image_url"] = img_tag["src"] if img_tag and "src" in img_tag.attrs else None

    return item
