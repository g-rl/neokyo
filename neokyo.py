import os
import csv
import requests
import subprocess
import platform
from bs4 import BeautifulSoup
from colorama import Fore, Style, init
from urllib.parse import urlparse
from deep_translator import GoogleTranslator

init(autoreset=True)

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

def fetch_page_html(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.text

def translate_to_english(text):
    try:
        return GoogleTranslator(source='auto', target='en').translate(text)
    except Exception as e:
        print(Fore.YELLOW + f"[translation warning] could not translate title: {e}")
        return text 

def scrape_product_data(url):
    html = fetch_page_html(url)
    soup = BeautifulSoup(html, "html.parser")

    item_data = {}

    product_section = soup.find("div", class_=lambda x: x and "product" in x.lower())

    title_tag = None
    if product_section:
        title_tag = product_section.find("h6") or product_section.find("p")
    if not title_tag:
        title_tag = soup.find("h6", string=True)
    
    raw_title = title_tag.get_text(strip=True) if title_tag else "n/a"
    translated_title = translate_to_english(raw_title) if raw_title != "n/a" else "n/a"

    item_data["title_original"] = raw_title
    item_data["title"] = translated_title.lower()

    item_data["seller"] = soup.find(string="Seller").find_next().get_text(strip=True).lower() if soup.find(string="Seller") else "n/a"
    item_data["item_id"] = soup.find(string="Item ID").find_next().get_text(strip=True).lower() if soup.find(string="Item ID") else "n/a"
    item_data["condition"] = soup.find(string="Condition").find_next().get_text(strip=True).lower() if soup.find(string="Condition") else "n/a"
    item_data["shipping"] = soup.find(string="Domestic Shipping").find_next().get_text(strip=True).lower() if soup.find(string="Domestic Shipping") else "n/a"

    price_container = soup.find("strong", class_="font-gothamRounded text-green price")
    if price_container:
        price_span = price_container.find("span", class_="product-price")
        if price_span:
            price_yen = int("".join(filter(str.isdigit, price_span.get_text())))
            item_data["price_yen"] = price_yen
        else:
            item_data["price_yen"] = 0
    else:
        item_data["price_yen"] = 0

    img_tag = soup.find("img", class_="cloudzoom")
    item_data["image_url"] = img_tag["src"] if img_tag and "src" in img_tag.attrs else None

    return item_data

def display_data(item_data, currency=None):
    padding = 20
    print(f"{Fore.WHITE}{' ' * padding}{Fore.MAGENTA}{item_data['title']}{Fore.WHITE}{' ' * padding}\n")
    print(f"{Fore.WHITE}original title: {Fore.MAGENTA}{Style.BRIGHT}{item_data['title_original']}")
    print(f"{Fore.WHITE}seller: {Fore.MAGENTA}{Style.BRIGHT}{item_data['seller']}")
    print(f"{Fore.WHITE}item id: {Fore.MAGENTA}{Style.BRIGHT}{item_data['item_id']}")
    print(f"{Fore.WHITE}condition: {Fore.MAGENTA}{Style.BRIGHT}{item_data['condition']}")
    print(f"{Fore.WHITE}shipping: {Fore.MAGENTA}{Style.BRIGHT}{item_data['shipping']}")

    price_yen = item_data["price_yen"]
    price_display = f"{price_yen}¥"

    if currency and currency in CURRENCY_RATES:
        converted = round(price_yen * CURRENCY_RATES[currency])
        symbol = CURRENCY_SYMBOLS.get(currency, "")
        price_display += f" ({symbol}{converted})"

    print(f"{Fore.WHITE}price: {Fore.MAGENTA}{Style.BRIGHT}{price_display}")

    if item_data.get("image_url"):
        print(f"{Fore.WHITE}image url: {Fore.MAGENTA}{Style.BRIGHT}{item_data['image_url']}")
    print(Fore.CYAN + "\n")

def save_product_files(item_data, url, currency=None):
    safe_title = "".join(c for c in item_data['title'] if c.isalnum() or c in (' ', '_')).strip().replace(" ", "_")
    folder_name = os.path.join("products", safe_title or "product")
    
    if os.path.exists(folder_name):
        print(Fore.RED + f"data for this item already exists: {folder_name}\n")
        return

    os.makedirs(folder_name, exist_ok=True)

    price_yen = item_data.get("price_yen", 0)
    converted_price = None
    converted_symbol = ""

    if currency and currency in CURRENCY_RATES:
        converted_price = round(price_yen * CURRENCY_RATES[currency])
        converted_symbol = CURRENCY_SYMBOLS.get(currency, "")

    data_path = os.path.join(folder_name, "item_data.txt")
    with open(data_path, "w", encoding="utf-8") as file:
        file.write(f"translated title: {item_data.get('title', 'n/a')}\n")
        file.write(f"original title: {item_data.get('title_original', 'n/a')}\n")
        file.write(f"seller: {item_data.get('seller', 'n/a')}\n")
        file.write(f"item id: {item_data.get('item_id', 'n/a')}\n")
        file.write(f"condition: {item_data.get('condition', 'n/a')}\n")
        file.write(f"shipping: {item_data.get('shipping', 'n/a')}\n")
        file.write(f"price: {price_yen}¥\n")
        if converted_price is not None:
            file.write(f"converted price: {converted_symbol}{converted_price}\n")
        if item_data.get("image_url"):
            file.write(f"image url: {item_data['image_url']}\n")
        file.write(f"url: {url}\n")
    print(Fore.GREEN + f"saved product data to: {data_path}")

    if item_data.get("image_url"):
        image_url = item_data["image_url"]
        image_ext = os.path.splitext(image_url)[1].split("?")[0] or ".jpg"
        image_path = os.path.join(folder_name, f"image{image_ext}")
        try:
            img_data = requests.get(image_url, headers={"User-Agent": "Mozilla/5.0"}).content
            with open(image_path, "wb") as img_file:
                img_file.write(img_data)
            print(Fore.GREEN + f"saved image to: {image_path}")
        except Exception as e:
            print(Fore.RED + f"failed to save image: {e}")

    # csv stuff
    csv_path = os.path.join("products", "data.csv")
    csv_exists = os.path.exists(csv_path)

    with open(csv_path, mode="a", newline="", encoding="utf-8") as csvfile:
        fieldnames = [
            "translated_title", "original_title", "seller", "item_id", "condition",
            "shipping", "price_yen", "converted_price", "converted_currency",
            "image_url", "url"
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        if not csv_exists:
            writer.writeheader()

        writer.writerow({
            "translated_title": item_data.get("title", "n/a"),
            "original_title": item_data.get("title_original", "n/a"),
            "seller": item_data.get("seller", "n/a"),
            "item_id": item_data.get("item_id", "n/a"),
            "condition": item_data.get("condition", "n/a"),
            "shipping": item_data.get("shipping", "n/a"),
            "price_yen": price_yen,
            "converted_price": converted_price if converted_price is not None else "",
            "converted_currency": currency if converted_price is not None else "",
            "image_url": item_data.get("image_url", ""),
            "url": url
        })
    print(Fore.GREEN + f"appended product to: {csv_path}")

    try:
        if platform.system() == "Windows":
            os.startfile(folder_name)
        elif platform.system() == "Darwin":  
            subprocess.run(["open", folder_name])
        else:  
            subprocess.run(["xdg-open", folder_name])
    except Exception as e:
        print(Fore.YELLOW + f"could not open folder automatically: {e}")

def main():
    print(Fore.MAGENTA + Style.BRIGHT + "\nneokyo product checker - github.com/g-rl\n")
    while True:
        user_input = input(Fore.WHITE + "enter product url or type 'exit': " + Fore.MAGENTA).strip()
        if user_input.lower() == "exit":
            print(Fore.CYAN + "\n◈ see u later..\n")
            break

        parts = user_input.split()
        url = parts[0]
        currency = parts[1].lower() if len(parts) > 1 and parts[1].lower() != "yen" else None

        if not url.startswith("https://neokyo.com/en/product"):
            print(Fore.RED + "link must start with neokyo.com/en/product\n")
            continue

        print(Fore.WHITE + "\nfetching data, one sec...\n")
        try:
            item_data = scrape_product_data(url)
            display_data(item_data, currency)

            if item_data["price_yen"] > 0:
                save_product_files(item_data, url, currency)
            else:
                print(Fore.YELLOW + "no price found. skipping file save.")

        except Exception as e:
            print(Fore.RED + f"error: {e}\n")

if __name__ == "__main__":
    main()
