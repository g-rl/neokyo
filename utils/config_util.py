import os, yaml
from colorama import Fore

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
        "folder_name_style": "translated",
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

def merge_dicts(base, custom):
    merged = base.copy()
    for k, v in custom.items():
        if isinstance(v, dict) and k in merged:
            merged[k] = merge_dicts(merged[k], v)
        else:
            merged[k] = v
    return merged

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                user_config = yaml.safe_load(f) or {}
            return merge_dicts(DEFAULT_CONFIG, user_config)
        except Exception as e:
            print(Fore.YELLOW + f"[config warning] could not read config.yml: {e}")
    return DEFAULT_CONFIG
