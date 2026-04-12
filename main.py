import time
import json
import re
import requests
import pytesseract
from PIL import ImageGrab
import pyautogui
import pyperclip
import keyboard

# -----------------------------------------------
# CONFIG
# -----------------------------------------------
CACHE_FILE = "words.json"
PASTE_DELAY = 2  # seconds to wait before pasting so user can focus textbox
LIBRETRANSLATE_URL = "https://libretranslate.com/translate"
SOURCE_LANG = "pl"
TARGET_LANG = "es"

# Tesseract path - installed for current user only
pytesseract.pytesseract.tesseract_cmd = r"C:\Users\patri\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"

# -----------------------------------------------
# WORDS TO IGNORE
# These are Instaling UI strings, not vocab words.
# OCR may pick them up - we skip them entirely.
# -----------------------------------------------
IGNORED_WORDS = {
    "synonim",
    "synonym",
    "przyklad",
    "przyklady",
    "definicja",
    "definition",
    "tlumaczenie",
    "przetlumacz",
}

# -----------------------------------------------
# CACHE - load and save
# words.json is used as a translation cache only.
# It is never manually edited - the API fills it.
# -----------------------------------------------
def load_cache(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_cache(path, cache):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=4)

# -----------------------------------------------
# VALIDATE OCR OUTPUT
# Returns (True, cleaned_word) or (False, reason)
# -----------------------------------------------
def validate_word(word):
    word = word.strip().lower()

    # Empty or whitespace only
    if not word:
        return False, "empty string"

    # Too short to be a real word (single char, noise)
    if len(word) < 2:
        return False, f"too short: '{word}'"

    # Contains digits - likely OCR noise or a number
    if any(c.isdigit() for c in word):
        return False, f"contains digits: '{word}'"

    # Mostly non-alphabetic characters - likely OCR garbage
    alpha_ratio = sum(c.isalpha() for c in word) / len(word)
    if alpha_ratio < 0.7:
        return False, f"too many non-alpha characters: '{word}'"

    # Instaling UI strings - not vocab words
    if word in IGNORED_WORDS:
        return False, f"ignored UI string: '{word}'"

    # Check if any ignored word is contained in the OCR result
    # e.g. OCR reads "Synonim:" or "[ Synonim ]"
    for ignored in IGNORED_WORDS:
        if ignored in word:
            return False, f"contains ignored string '{ignored}': '{word}'"

    return True, word

# -----------------------------------------------
# TRANSLATE via LibreTranslate API (free, no key)
# -----------------------------------------------
def translate(word):
    try:
        response = requests.post(
            LIBRETRANSLATE_URL,
            data={
                "q": word,
                "source": SOURCE_LANG,
                "target": TARGET_LANG,
                "format": "text"
            },
            timeout=10
        )
        result = response.json()
        if "translatedText" in result:
            return result["translatedText"].strip().lower()
        else:
            print(f"API error: {result}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}")
        return None

# -----------------------------------------------
# LOOKUP - check cache first, then API
# -----------------------------------------------
def lookup(word, cache):
    word = word.strip().lower()

    # Check cache first
    if word in cache:
        print(f"Cache hit: '{word}' -> '{cache[word]}'")
        return cache[word]

    # Not in cache - call API
    print(f"Not in cache, calling LibreTranslate for '{word}'...")
    translation = translate(word)

    if translation:
        cache[word] = translation
        save_cache(CACHE_FILE, cache)
        print(f"Translated and cached: '{word}' -> '{translation}'")
    else:
        print(f"Could not translate '{word}'.")

    return translation

# -----------------------------------------------
# REGION SELECTION
# User presses ENTER at each corner position
# -----------------------------------------------
def get_screen_region():
    print("Move your cursor to the TOP-LEFT corner of the word area, then press ENTER.")
    keyboard.wait("enter")
    x1, y1 = pyautogui.position()
    print(f"Top-left corner set: ({x1}, {y1})")

    print("Move your cursor to the BOTTOM-RIGHT corner of the word area, then press ENTER.")
    keyboard.wait("enter")
    x2, y2 = pyautogui.position()
    print(f"Bottom-right corner set: ({x2}, {y2})")

    return (x1, y1, x2, y2)

# -----------------------------------------------
# SCREENSHOT + OCR
# -----------------------------------------------
def read_text_from_region(region):
    screenshot = ImageGrab.grab(bbox=region)
    text = pytesseract.image_to_string(screenshot, lang="pol")
    text = text.strip().lower()
    return text

# -----------------------------------------------
# PASTE ANSWER
# Copies the full translation to clipboard and
# pastes it in one shot with Ctrl+V.
# Works with all characters including accented ones.
# No per-character delay needed anymore.
# -----------------------------------------------
def paste_answer(answer):
    print(f"Pasting answer: '{answer}'")
    pyperclip.copy(answer)
    pyautogui.hotkey("ctrl", "v")

# -----------------------------------------------
# MAIN
# -----------------------------------------------
def main():
    print("=== Instaling Bot ===")
    cache = load_cache(CACHE_FILE)
    print(f"Loaded {len(cache)} cached words from {CACHE_FILE}")

    region = get_screen_region()
    print(f"Monitoring region: {region}")

    print("\nClick on the answer textbox in Instaling to focus it.")
    print("Then press ENTER here to read the word and paste the answer.")
    print("Press ESC at any time to quit.\n")

    while True:
        if keyboard.is_pressed("esc"):
            print("Exiting.")
            break

        print("Press ENTER to read the current word...")
        keyboard.wait("enter")

        if keyboard.is_pressed("esc"):
            print("Exiting.")
            break

        raw = read_text_from_region(region)
        print(f"OCR raw output: '{raw}'")

        valid, result = validate_word(raw)
        if not valid:
            print(f"Skipping - {result}\n")
            continue

        word = result
        print(f"Word to translate: '{word}'")

        translation = lookup(word, cache)

        if translation:
            print(f"Pasting in {PASTE_DELAY} seconds. Make sure the textbox is focused...")
            time.sleep(PASTE_DELAY)
            paste_answer(translation)
            print("Done.\n")
        else:
            print("Could not get a translation. Skipping.\n")

if __name__ == "__main__":
    main()
