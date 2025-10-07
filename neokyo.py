from colorama import Fore, Style, init
from utils.config_util import load_config
from utils.scrape_util import scrape_product_data
from utils.display_util import display_data
from utils.io_util import save_product_files
from utils.currency_util import CURRENCY_RATES
import time

init(autoreset=True)

def main():
    print(Fore.MAGENTA + Style.BRIGHT + "\nneokyo product checker - github.com/g-rl\n")
    config = load_config()
    default_currency = config.get("default_currency")

    CURRENCY_RATES.update(config["conversion"]["custom_rates"])

    if default_currency and default_currency.lower() not in CURRENCY_RATES:
        print(Fore.YELLOW + f"[config warning] unknown default_currency '{default_currency}' — ignoring.")
        default_currency = None

    while True:
        user_input = input(Fore.WHITE + "enter product url(s) or type 'exit': " + Fore.MAGENTA).strip()
        if user_input.lower() == "exit":
            print(Fore.CYAN + "\n◈ see u later..\n")
            break

        parts = user_input.split()
        currency = parts[-1].lower() if len(parts) > 1 and parts[-1].lower() in CURRENCY_RATES else default_currency
        urls = parts[0] if len(parts) == 1 else " ".join(parts[:-1]) if parts[-1].lower() in CURRENCY_RATES else user_input

        url_list = [u.strip() for u in urls.split(",") if u.strip()]

        if not url_list:
            print(Fore.RED + "no valid urls provided.\n")
            continue

        for i, url in enumerate(url_list, start=1):
            if not url.startswith("https://neokyo.com/en/product"):
                print(Fore.RED + f"[{i}] invalid link (must start with https://neokyo.com/en/product): {url}\n")
                continue

            print(Fore.WHITE + f"\n[{i}/{len(url_list)}] fetching data for: {url}\n")
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
                print(Fore.RED + f"error while scraping {url}: {e}\n")
                if config["debug"]["log_errors"]:
                    with open(config["debug"]["log_file"], "a", encoding="utf-8") as log:
                        log.write(f"[error] {url} — {e}\n")

        print(Fore.CYAN + "\n✅ finished processing..\n")

if __name__ == "__main__":
    main()
