import requests
from bs4 import BeautifulSoup
import json
import os
import time
from datetime import datetime

BASE_URL = "https://rulings.cbp.gov/ruling/"
OUTPUT_FILE = "C:/customs_ai2/rulings.json"
PROGRESS_FILE = "C:/customs_ai2/scraper_progress.json"
SAVE_EVERY = 100
DELAY = 0.3

# All ruling ranges to cover
# NY rulings: N000001 - N350000
# HQ rulings: H000001 - H330000
# Older HQ: 800000 - 999999

def build_ruling_list():
    rulings = []
    # NY rulings
    for i in range(1, 350001):
        rulings.append(f"N{str(i).zfill(6)}")
    # HQ rulings
    for i in range(1, 330001):
        rulings.append(f"H{str(i).zfill(6)}")
    # Older numeric rulings
    for i in range(800000, 1000000):
        rulings.append(str(i))
    return rulings

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    return {"last_index": 0, "scraped_count": 0, "started": datetime.now().isoformat()}

def save_progress(index, count):
    with open(PROGRESS_FILE, "w") as f:
        json.dump({
            "last_index": index,
            "scraped_count": count,
            "last_updated": datetime.now().isoformat()
        }, f)

def load_existing_rulings():
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r") as f:
            return json.load(f)
    return []

def save_rulings(rulings):
    with open(OUTPUT_FILE, "w") as f:
        json.dump(rulings, f)

def fetch_ruling(ruling_number):
    try:
        url = f"{BASE_URL}{ruling_number}"
        headers = {"User-Agent": "Mozilla/5.0 (research tool)"}
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return None
        soup = BeautifulSoup(response.text, "html.parser")
        content = soup.get_text(separator=" ", strip=True)
        if len(content) < 200:
            return None
        return {
            "ruling_number": ruling_number,
            "url": url,
            "text": content[:3000]
        }
    except Exception:
        return None

def main():
    print(f"Building ruling list...")
    all_rulings = build_ruling_list()
    total = len(all_rulings)
    print(f"Total rulings to attempt: {total:,}")

    progress = load_progress()
    start_index = progress["last_index"]
    existing_rulings = load_existing_rulings()
    scraped_count = len(existing_rulings)

    print(f"Resuming from index {start_index:,} ({scraped_count:,} rulings already collected)")
    print(f"Starting at {datetime.now().strftime('%H:%M:%S')}")
    print("-" * 50)

    batch = []
    
    for i in range(start_index, total):
        ruling_number = all_rulings[i]
        result = fetch_ruling(ruling_number)
        
        if result:
            batch.append(result)
            scraped_count += 1
        
        # Save every SAVE_EVERY rulings
        if len(batch) >= SAVE_EVERY:
            existing_rulings.extend(batch)
            save_rulings(existing_rulings)
            save_progress(i + 1, scraped_count)
            batch = []
            elapsed = datetime.now().strftime('%H:%M:%S')
            print(f"[{elapsed}] Progress: {i+1:,}/{total:,} attempted | {scraped_count:,} collected")

        time.sleep(DELAY)

    # Save any remaining
    if batch:
        existing_rulings.extend(batch)
        save_rulings(existing_rulings)
        save_progress(total, scraped_count)

    print(f"\nDone! Total rulings collected: {scraped_count:,}")

if __name__ == "__main__":
    main()