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
SOURCE_LANG = "pl"
TARGET_LANG = "de"

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
# Cache key is the full raw hint string from OCR,
# so "w; w srodku; wewnatrz; za" is cached as one entry.
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
# PREPARE OCR TEXT FOR TRANSLATION
# Keeps all hints but normalizes separators to
# commas so the API gets full context.
# "w; w srodku; wewnatrz; za" -> "w, w srodku, wewnatrz, za"
# The API uses all hints together to pick the right
# translation, then we take only the first result word.
# -----------------------------------------------
def prepare_for_translation(text):
    text = text.strip().lower()
    # Replace semicolons, pipes, newlines with commas for the API
    text = re.sub(r"[;|\n]+", ",", text)
    # Collapse multiple commas/spaces
    text = re.sub(r",\s*,", ",", text)
    text = text.strip(" ,")
    return text

# -----------------------------------------------
# VALIDATE OCR OUTPUT
# Validates the raw OCR text before sending.
# Returns (True, text) or (False, reason).
# Single letter words like "w" (in) are valid Polish.
# -----------------------------------------------
def validate_word(text):
    text = text.strip().lower()

    # Empty or whitespace only
    if not text:
        return False, "empty string"

    # Contains digits - likely OCR noise or a number
    if any(c.isdigit() for c in text):
        return False, f"contains digits: '{text}'"

    # Mostly non-alphabetic characters - likely OCR garbage
    alpha_chars = sum(c.isalpha() for c in text)
    if len(text) > 0 and alpha_chars / len(text) < 0.5:
        return False, f"too many non-alpha characters: '{text}'"

    # Instaling UI strings - not vocab words
    text_first = re.split(r"[;,|\n]", text)[0].strip()
    if text_first in IGNORED_WORDS:
        return False, f"ignored UI string: '{text_first}'"

    for ignored in IGNORED_WORDS:
        if ignored in text_first:
            return False, f"contains ignored string '{ignored}': '{text_first}'"

    return True, text

# -----------------------------------------------
# EXTRACT FIRST WORD FROM TRANSLATION RESULT
# API may return "in, inside, within, behind"
# We only want the first word: "en"
# -----------------------------------------------
def extract_first_word(translation):
    # Split on spaces, commas, semicolons and take first non-empty chunk
    parts = re.split(r"[\s,;]+", translation.strip())
    parts = [p.strip() for p in parts if p.strip()]
    if parts:
        return parts[0]
    return translation.strip()

# -----------------------------------------------
# TRANSLATE via MyMemory API (free, no key needed)
# Sends the full hint string for better context.
# 5000 words/day free limit - plenty for Instaling.
# -----------------------------------------------
def translate(text):
    try:
        response = requests.get(
            "https://api.mymemory.translated.net/get",
            params={
                "q": text,
                "langpair": f"{SOURCE_LANG}|{TARGET_LANG}",
            },
            timeout=10
        )
        result = response.json()
        if result.get("responseStatus") == 200:
            translated = result["responseData"]["translatedText"].strip().lower()
            return translated
        else:
            print(f"API error: {result.get('responseDetails', 'unknown error')}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}")
        return None

# -----------------------------------------------
# LOOKUP - check cache first, then API
# Cache key is the normalized full hint string.
# -----------------------------------------------
def lookup(raw_text, cache):
    key = raw_text.strip().lower()

    # Check cache first
    if key in cache:
        print(f"Cache hit: '{key}' -> '{cache[key]}'")
        return cache[key]

    # Prepare full hint string for translation
    query = prepare_for_translation(raw_text)
    print(f"Sending to API: '{query}'")

    full_translation = translate(query)
    if not full_translation:
        print(f"Could not translate '{query}'.")
        return None

    print(f"API returned: '{full_translation}'")

    # Extract just the first word from the translation
    first_word = extract_first_word(full_translation)
    print(f"Using first word: '{first_word}'")

    cache[key] = first_word
    save_cache(CACHE_FILE, cache)
    print(f"Cached: '{key}' -> '{first_word}'")

    return first_word

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
    return text

# -----------------------------------------------
# PASTE ANSWER
# Copies the full translation to clipboard and
# pastes it in one shot with Ctrl+V.
# Works with all characters including accented ones.
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
        print(f"OCR raw output: '{raw.strip()}'")

        valid, result = validate_word(raw.strip())
        if not valid:
            print(f"Skipping - {result}\n")
            continue

        translation = lookup(result, cache)

        if translation:
            print(f"Pasting in {PASTE_DELAY} seconds. Make sure the textbox is focused...")
            time.sleep(PASTE_DELAY)
            paste_answer(translation)
            print("Done.\n")
        else:
            print("Could not get a translation. Skipping.\n")

if __name__ == "__main__":
    main()
