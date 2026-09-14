#!/usr/bin/env python3
"""
Runs on a schedule via GitHub Actions (see .github/workflows/update-jackpots.yml).
Scrapes current jackpot estimates from national-lottery.co.uk and writes them to
jackpots.json at the repo root, which the app fetches directly (same-origin, so
no CORS issue once it's hosted).

If a game's figure can't be confidently found, its PREVIOUS value in jackpots.json
is kept rather than being wiped or guessed — so the app is never worse off than
before, it just doesn't get an update that cycle.

See the honesty note in lottery_check.py — this scraper was written from page
text seen via search, not verified against live markup. If it stops finding
figures, check the Action's log output (it prints what it did find) and send
me the result in chat to patch the parsing.
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
GAMES_URL = "https://www.national-lottery.co.uk/games"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; personal-lottery-tracker)"}


def parse_money_to_millions(text):
    m = re.search(r"£\s?([\d,.]+)\s?([MBK])", text, re.IGNORECASE)
    if not m:
        return None
    value = float(m.group(1).replace(",", ""))
    unit = m.group(2).upper()
    if unit == "B":
        return value * 1000
    if unit == "K":
        return value / 1000
    return value


def fetch_jackpots():
    found = {"lotto": None, "em": None, "pb": None}
    try:
        resp = requests.get(GAMES_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"Fetch failed: {e}", file=sys.stderr)
        return found

    soup = BeautifulSoup(resp.text, "html.parser")
    page_text = soup.get_text(" ", strip=True)

    anchors = {
        "lotto": ("2.00", "lotto"),
        "em": ("2.50", "euromillions"),
        "pb": ("4.00", "powerball"),
    }
    for key, (price, slug) in anchors.items():
        m = re.search(rf"Play for £{re.escape(price)},\s*{re.escape(slug)}\b", page_text, re.IGNORECASE)
               if not m:
            idx = page_text.lower().find(slug)
            if idx != -1:
                print(f"DEBUG {key}: anchor regex failed, but found '{slug}' at position {idx}:")
                print(f"  context: ...{page_text[max(0,idx-100):idx+150]}...")
            else:
                print(f"DEBUG {key}: '{slug}' not found anywhere on the page.")
            continue
        window = page_text[max(0, m.start() - 250): m.start()]
        matches = re.findall(r"£\s?([\d,.]+)\s?([MBK])", window, re.IGNORECASE)
        if matches:
            value, unit = matches[-1]
            value = float(value.replace(",", ""))
            found[key] = value * 1000 if unit.upper() == "B" else (value / 1000 if unit.upper() == "K" else value)

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
