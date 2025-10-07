from deep_translator import GoogleTranslator
from colorama import Fore

def translate_to_language(text, config):
    target_lang = config["default_language"]
    if not target_lang or target_lang.lower() in ("none", ""):
        return text
    try:
        return GoogleTranslator(source='auto', target=target_lang).translate(text)
    except Exception:
        if config["debug"]["log_errors"]:
            with open(config["debug"]["log_file"], "a", encoding="utf-8") as log:
                log.write(f"[translation failed] {text}\n")
        try:
            return GoogleTranslator(source='auto', target=config["fallback_language"]).translate(text)
        except Exception:
            return text
