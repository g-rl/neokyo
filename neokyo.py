
import os
import csv
import requests
import subprocess
import platform
import yaml
import time
from bs4 import BeautifulSoup
from colorama import Fore, Style, init
from urllib.parse import urlparse
from deep_translator import GoogleTranslator

init(autoreset=True)

CONFIG_PATH = "config.yml"

DEFAULT_CONFIG = {
    "default_currency": "gbp",
    "default_language": "en",
    "fallback_language": "ja",
    "retry_attempts": 3,
    "timeout_seconds": 10,
    "output": {
        "open_folder": True,
        "save_images": True,
        "save_csv": True,
        "save_txt": True,
        "print_data": True,
        "print_summary": True,
        "folder_name_style": "translated",  # "original", "translated", "item_id"
        "overwrite_existing": False
    },
    "conversion": {
        "precision": 2,
        "symbol_spacing": True,
        "show_both_prices": True,
        "custom_rates": {}
    },
    "scraping": {
        "translate_title": True,
        "include_image_url": True,
        "include_seller": True,
        "include_condition": True,
        "include_shipping": True,
        "use_fallback_selectors": True
    },
    "display": {
        "padding": 20,
        "theme": "neon",
        "show_headers": True,
        "title_uppercase": True,
        "truncate_long_titles": True,
        "max_title_length": 70,
        "separator_line": True
    },
    "files": {
        "base_dir": "products",
        "csv_name": "data.csv",
        "image_prefix": "img_",
        "image_format": "jpg",
        "naming_convention": "safe"
    },
    "network": {
        "user_agent": "Mozilla/5.0 (Neokyo-Scraper)",
        "proxy": None,
        "delay_between_requests": 1.5
    },
    "debug": {
        "log_errors": True,
        "log_file": "error.log",
        "show_stack_traces": False,
        "verbose_mode": False
    }
}

CURRENCY_RATES = {
    "gbp": 0.0056,
    "usd": 0.0071,
    "eur": 0.0065,
    "cad": 0.0094,
    "aud": 0.0100,
    "chf": 0.0066
}

CURRENCY_SYMBOLS = {
    "gbp": "£",
    "usd": "$",
    "eur": "€",
    "cad": "C$",
    "aud": "A$",
    "chf": "CHF"
}

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                user_config = yaml.safe_load(f) or {}
            return merge_dicts(DEFAULT_CONFIG, user_config)
        except Exception as e:
            print(Fore.YELLOW + f"[config warning] could not read config.yml: {e}")
    return DEFAULT_CONFIG


def merge_dicts(base, custom):
    merged = base.copy()
    for k, v in custom.items():
        if isinstance(v, dict) and k in merged:
            merged[k] = merge_dicts(merged[k], v)
        else:
            merged[k] = v
    return merged

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


def translate_to_language(text, config):
    target_lang = config["default_language"]
    if not target_lang or target_lang.lower() in ("none", ""):
        return text
    try:
        return GoogleTranslator(source='auto', target=target_lang).translate(text)
    except Exception as e:
        if config["debug"]["log_errors"]:
            with open(config["debug"]["log_file"], "a", encoding="utf-8") as log:
                log.write(f"[translation failed] {text}\n")
        try:
            return GoogleTranslator(source='auto', target=config["fallback_language"]).translate(text)
        except Exception:
            return text


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

def display_data(item, currency, config):
    padding = config["display"]["padding"]
    title = item['title']

    if config["display"]["truncate_long_titles"]:
        max_len = config["display"]["max_title_length"]
        title = (title[:max_len] + "...") if len(title) > max_len else title

    if config["display"]["title_uppercase"]:
        title = title.upper()

    print(Fore.MAGENTA + " " * padding + title)
    if config["display"]["separator_line"]:
        print(Fore.WHITE + "-" * (len(title) + padding))

    for key, val in item.items():
        if key not in ["title", "title_original"]:
            print(f"{Fore.WHITE}{key}: {Fore.MAGENTA}{val}")

    yen = item.get("price_yen", 0)
    if currency and currency in CURRENCY_RATES:
        rate = CURRENCY_RATES[currency]
        rate = config["conversion"]["custom_rates"].get(currency, rate)
        converted = round(yen * rate, config["conversion"]["precision"])
        sym = CURRENCY_SYMBOLS.get(currency, "")
        space = " " if config["conversion"]["symbol_spacing"] else ""
        if config["conversion"]["show_both_prices"]:
            print(f"{Fore.WHITE}price: {Fore.MAGENTA}{yen}¥ ({sym}{space}{converted})")
        else:
            print(f"{Fore.WHITE}price: {Fore.MAGENTA}{sym}{space}{converted}")
    print()

def safe_name(name):
    return "".join(c for c in name if c.isalnum() or c in (" ", "_")).strip().replace(" ", "_")


def save_product_files(item, url, currency, config):
    base_dir = config["files"]["base_dir"]
    os.makedirs(base_dir, exist_ok=True)

    if config["output"]["folder_name_style"] == "item_id":
        folder = item.get("item_id", "product")
    elif config["output"]["folder_name_style"] == "original":
        folder = item.get("title_original", "product")
    else:
        folder = item.get("title", "product")

    folder = safe_name(folder) if config["files"]["naming_convention"] == "safe" else folder
    folder_path = os.path.join(base_dir, folder)

    if os.path.exists(folder_path) and not config["output"]["overwrite_existing"]:
        print(Fore.RED + f"data for this item already exists: {folder_path}\n")
        return

    os.makedirs(folder_path, exist_ok=True)

    # save TXT
    if config["output"]["save_txt"]:
        with open(os.path.join(folder_path, "item.txt"), "w", encoding="utf-8") as f:
            for k, v in item.items():
                f.write(f"{k}: {v}\n")
            f.write(f"url: {url}\n")
        print(Fore.GREEN + f"saved product data to: {folder_path}/item.txt")

    # save image
    if item.get("image_url") and config["output"]["save_images"]:
        try:
            img = requests.get(item["image_url"], timeout=10).content
            ext = f".{config['files']['image_format']}"
            img_path = os.path.join(folder_path, f"{config['files']['image_prefix']}1{ext}")
            with open(img_path, "wb") as imgfile:
                imgfile.write(img)
            print(Fore.GREEN + f"saved image to: {img_path}")
        except Exception as e:
            print(Fore.RED + f"failed to save image: {e}")

    # save CSV
    if config["output"]["save_csv"]:
        csv_path = os.path.join(base_dir, config["files"]["csv_name"])
        csv_exists = os.path.exists(csv_path)
        with open(csv_path, mode="a", newline="", encoding="utf-8") as csvfile:
            fieldnames = ["title", "title_original", "seller", "item_id", "condition", "shipping", "price_yen", "image_url", "url"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not csv_exists:
                writer.writeheader()
            writer.writerow({**item, "url": url})
        print(Fore.GREEN + f"appended product to: {csv_path}")

    # open folder
    if config["output"]["open_folder"]:
        try:
            if platform.system() == "Windows":
                os.startfile(folder_path)
            elif platform.system() == "Darwin":
                subprocess.run(["open", folder_path])
            else:
                subprocess.run(["xdg-open", folder_path])
        except Exception as e:
            print(Fore.YELLOW + f"could not open folder automatically: {e}")

def main():
    print(Fore.MAGENTA + Style.BRIGHT + "\nneokyo product checker - github.com/g-rl\n")
    config = load_config()
    default_currency = config.get("default_currency")

    # merge in custom conversion rates
    CURRENCY_RATES.update(config["conversion"]["custom_rates"])

    if default_currency and default_currency.lower() not in CURRENCY_RATES:
        print(Fore.YELLOW + f"[config warning] unknown default_currency '{default_currency}' — ignoring.")
        default_currency = None

    while True:
        user_input = input(Fore.WHITE + "enter product url or type 'exit': " + Fore.MAGENTA).strip()
        if user_input.lower() == "exit":
            print(Fore.CYAN + "\n◈ see u later..\n")
            break

        parts = user_input.split()
        url = parts[0]
        currency = parts[1].lower() if len(parts) > 1 else default_currency

        if currency and currency not in CURRENCY_RATES:
            print(Fore.RED + f"currency '{currency}' not recognized.\n")
            continue

        if not url.startswith("https://neokyo.com/en/product"):
            print(Fore.RED + "link must start with https://neokyo.com/en/product\n")
            continue

        print(Fore.WHITE + "\nfetching data, one sec...\n")
        try:
            item = scrape_product_data(url, config)
            if config["output"]["print_data"]:
                display_data(item, currency, config)

            if item["price_yen"] > 0:
                save_product_files(item, url, currency, config)
            else:
                print(Fore.YELLOW + "no price found. skipping file save.")
        except Exception as e:
            if config["debug"]["show_stack_traces"]:
                raise
            print(Fore.RED + f"error: {e}\n")
            if config["debug"]["log_errors"]:
                with open(config["debug"]["log_file"], "a", encoding="utf-8") as log:
                    log.write(f"[error] {e}\n")


if __name__ == "__main__":
    main()
