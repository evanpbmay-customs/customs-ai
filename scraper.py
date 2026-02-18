import requests
import json
import time
from bs4 import BeautifulSoup

def fetch_ruling(ruling_number):
    url = f"https://rulings.cbp.gov/ruling/{ruling_number}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            text = soup.get_text(separator=" ", strip=True)
            if len(text) > 200:
                return {"ruling_number": ruling_number, "url": url, "text": text[:3000]}
    except Exception as e:
        pass
    return None

def scrape_rulings(max_rulings=5000):
    rulings = []
    print("Fetching CBP rulings by ruling number...")
    
    # NY rulings start with N, HQ rulings start with H
    # Recent NY rulings are in the N300000-N350000 range
    prefixes = ["N3", "N2", "H2"]
    
    for prefix in prefixes:
        start = int(prefix[1:]) * 100000
        for i in range(start, start + 200):
            ruling_number = f"{prefix[0]}{i:06d}"
            ruling = fetch_ruling(ruling_number)
            if ruling:
                rulings.append(ruling)
                print(f"Got ruling {ruling_number} - total: {len(rulings)}")
            
            if len(rulings) >= max_rulings:
                break
            time.sleep(0.5)
        
        if len(rulings) >= max_rulings:
            break
    
    with open("rulings.json", "w") as f:
        json.dump(rulings, f, indent=2)
    print(f"Done! Saved {len(rulings)} rulings")

if __name__ == "__main__":
    scrape_rulings(max_rulings=5000)