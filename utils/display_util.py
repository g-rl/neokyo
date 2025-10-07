from colorama import Fore
from utils.currency_util import CURRENCY_RATES, CURRENCY_SYMBOLS

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
        rate = config["conversion"]["custom_rates"].get(currency, CURRENCY_RATES[currency])
        converted = round(yen * rate, config["conversion"]["precision"])
        sym = CURRENCY_SYMBOLS.get(currency, "")
        space = " " if config["conversion"]["symbol_spacing"] else ""
        converted_str = f"{sym}{space}{converted}"

        item["converted_price"] = converted
        item["converted_currency"] = currency

        if config["conversion"]["show_both_prices"]:
            print(f"{Fore.WHITE}price: {Fore.MAGENTA}{yen}¥ ({converted_str})")
        else:
            print(f"{Fore.WHITE}price: {Fore.MAGENTA}{converted_str}")
    print()
