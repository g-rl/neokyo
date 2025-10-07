import os, csv, platform, subprocess, requests
from colorama import Fore
from utils.csv_util import export_clean_excel

def safe_name(name):
    return "".join(c for c in name if c.isalnum() or c in (" ", "_")).strip().replace(" ", "_")

def save_product_files(item, url, currency, config):
    base_dir = config["files"]["base_dir"]
    os.makedirs(base_dir, exist_ok=True)

    style = config["output"]["folder_name_style"]
    if style == "item_id":
        folder = item.get("item_id", "product")
    elif style == "original":
        folder = item.get("title_original", "product")
    else:
        folder = item.get("title", "product")

    folder = safe_name(folder) if config["files"]["naming_convention"] == "safe" else folder
    folder_path = os.path.join(base_dir, folder)

    if os.path.exists(folder_path) and not config["output"]["overwrite_existing"]:
        print(Fore.RED + f"data for this item already exists: {folder_path}\n")
        return

    os.makedirs(folder_path, exist_ok=True)

    # Save TXT
    if config["output"]["save_txt"]:
        with open(os.path.join(folder_path, "item.txt"), "w", encoding="utf-8") as f:
            for k, v in item.items():
                f.write(f"{k}: {v}\n")
            f.write(f"url: {url}\n")
        print(Fore.GREEN + f"saved product data to: {folder_path}/item.txt")

    # Save image
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

    # Save CSV
    if config["output"]["save_csv"]:
        csv_path = os.path.join(base_dir, config["files"]["csv_name"])
        csv_exists = os.path.exists(csv_path)
        with open(csv_path, mode="a", newline="", encoding="utf-8") as csvfile:
            fieldnames = [
                "title", "title_original", "seller", "item_id", "condition", "shipping",
                "price_yen", "converted_price", "converted_currency", "image_url", "url"
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not csv_exists:
                writer.writeheader()
            writer.writerow({**item, "url": url})
        print(Fore.GREEN + f"appended product to: {csv_path}\n")

        try:
            export_clean_excel(csv_path, "neokyo.xlsx")
            print(Fore.CYAN + "excel created: neokyo.xlsx")
        except Exception as e:
            print(Fore.YELLOW + f"could not create clean excel file: {e}")

    # Open folder automatically
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
