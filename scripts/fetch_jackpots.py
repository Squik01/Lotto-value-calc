#!/usr/bin/env python3
"""
Runs on a schedule via GitHub Actions (see .github/workflows/update-jackpots.yml).
Scrapes current jackpot estimates from national-lottery.com (a plain, server-
rendered results site — NOT the official national-lottery.co.uk, which loads
jackpot figures via JavaScript that a plain fetch can't see) and writes them
to jackpots.json at the repo root, which the app fetches directly.

If a game's figure can't be confidently found, its PREVIOUS value in
jackpots.json is kept rather than being wiped or guessed.

Lotto and EuroMillions parsing is confirmed against real page text. Powerball
parsing is a best-effort guess at the phrasing and prints debug context if it
fails, so it can be corrected precisely on the next round if needed.
"""

import re
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
JACKPOTS_FILE = ROOT / "jackpots.json"
RESULTS_URL = "https://www.national-lottery.com/results"
POWERBALL_URL = "https://www.national-lottery.com/powerball/results"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; personal-lottery-tracker)"}


def get_page_text(url):
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    return soup.get_text(" ", strip=True)


def word_amount_to_millions(number_str, unit):
    value = float(number_str.replace(",", ""))
    unit = (unit or "").lower()
    if unit in ("billion", "b"):
        return value * 1000
    if unit in ("thousand", "k"):
        return value / 1000
    if unit in ("million", "m", ""):
        return value
    return value


def fetch_jackpots():
    found = {"lotto": None, "em": None, "pb": None}

    try:
        page_text = get_page_text(RESULTS_URL)
    except requests.RequestException as e:
        print(f"Fetch failed for {RESULTS_URL}: {e}", file=sys.stderr)
        page_text = ""

    if page_text:
        lotto_m = re.search(
            r"Lotto jackpot:\s*£\s?([\d,.]+)\s*(Million|Billion|Thousand|M|K|B)?",
            page_text, re.IGNORECASE
        )
        if lotto_m:
            found["lotto"] = word_amount_to_millions(lotto_m.group(1), lotto_m.group(2))
        else:
            idx = page_text.lower().find("lotto")
            print(f"DEBUG lotto: pattern not found. Context near 'lotto': "
                  f"...{page_text[max(0,idx-80):idx+150] if idx != -1 else 'NOT ON PAGE'}...")

        em_m = re.search(
            r"EuroMillions draw:\s*£\s?([\d,.]+)\s*(Million|Billion|Thousand|M|K|B)?",
            page_text, re.IGNORECASE
        )
        if em_m:
            found["em"] = word_amount_to_millions(em_m.group(1), em_m.group(2))
        else:
            idx = page_text.lower().find("euromillions")
            print(f"DEBUG em: pattern not found. Context near 'euromillions': "
                  f"...{page_text[max(0,idx-80):idx+150] if idx != -1 else 'NOT ON PAGE'}...")

    try:
        pb_text = get_page_text(POWERBALL_URL)
    except requests.RequestException as e:
        print(f"Fetch failed for {POWERBALL_URL}: {e}", file=sys.stderr)
        pb_text = ""

    if pb_text:
        pb_m = re.search(
            r"[Jj]ackpot[:\s]*£\s?([\d,.]+)\s*(Million|Billion|Thousand|M|K|B)?",
            pb_text
        )
        if pb_m:
            found["pb"] = word_amount_to_millions(pb_m.group(1), pb_m.group(2))
        else:
            idx = pb_text.lower().find("jackpot")
            print(f"DEBUG pb: pattern not found. Context near 'jackpot': "
                  f"...{pb_text[max(0,idx-80):idx+150] if idx != -1 else 'NOT ON PAGE'}...")

    return found


def load_existing():
    if JACKPOTS_FILE.exists():
        try:
            return json.loads(JACKPOTS_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"lotto": 3.8, "em": 76.0, "pb": 500.0, "updated": None, "stale": []}


def main():
    existing = load_existing()
    scraped = fetch_jackpots()

    stale = []
    for key in ("lotto", "em", "pb"):
        if scraped.get(key) is not None:
            existing[key] = scraped[key]
            print(f"{key}: updated to £{scraped[key]}m")
        else:
            stale.append(key)
            print(f"{key}: could not confirm this run, kept previous value (£{existing.get(key)}m)")

    existing["stale"] = stale
    existing["updated"] = datetime.now(timezone.utc).isoformat()

    JACKPOTS_FILE.write_text(json.dumps(existing, indent=2))
    print(f"Wrote {JACKPOTS_FILE}")


if __name__ == "__main__":
    main()
