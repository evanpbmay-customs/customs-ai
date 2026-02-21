import requests
import json
import os
from datetime import datetime, timedelta

OUTPUT_FILE = "C:/customs_ai2/tariff_updates.json"
FR_API = "https://www.federalregister.gov/api/v1/documents.json"

def fetch_recent_actions(days_back=365):
    since_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    results = []
    
    search_configs = [
        {"term": "tariff", "types": ["PRESDOCU"]},
        {"term": "import duties", "types": ["PRESDOCU"]},
        {"term": "section 301", "types": ["PRESDOCU", "RULE"]},
        {"term": "reciprocal tariff", "types": ["PRESDOCU"]},
        {"term": "trade act proclamation", "types": ["PRESDOCU"]},
    ]
    
    for config in search_configs:
        try:
            params = {
                "conditions[term]": config["term"],
                "conditions[type][]": config["types"],
                "conditions[publication_date][gte]": since_date,
                "fields[]": ["title", "publication_date", "document_number",
                            "html_url", "abstract", "type", "subtype"],
                "per_page": 20,
                "order": "newest"
            }
            
            response = requests.get(FR_API, params=params, timeout=15)
            if response.status_code != 200:
                continue
                
            data = response.json()
            for doc in data.get("results", []):
                title = doc.get("title", "").lower()
                trade_keywords = ["tariff", "duty", "duties", "trade", "import",
                                  "section 301", "section 232", "section 201",
                                  "reciprocal", "customs", "harmonized"]
                if any(kw in title for kw in trade_keywords):
                    if not any(r["document_number"] == doc.get("document_number") for r in results):
                        results.append({
                            "title": doc.get("title", ""),
                            "date": doc.get("publication_date", ""),
                            "document_number": doc.get("document_number", ""),
                            "url": doc.get("html_url", ""),
                            "abstract": doc.get("abstract", "")[:500] if doc.get("abstract") else "",
                            "type": doc.get("type", ""),
                            "subtype": doc.get("subtype", ""),
                        })
        except Exception as e:
            print(f"Error fetching '{config['term']}': {e}")
            continue
    
    results.sort(key=lambda x: x["date"], reverse=True)
    print(f"\nFiltered documents:")
    for r in results[:20]:
        print(f"  {r['date']} | {r['title'][:80]}")
    print()
    return results[:20]

def analyze_actions_with_gpt(actions):
    if not actions:
        return []
    
    try:
        from openai import OpenAI
        from dotenv import load_dotenv
        load_dotenv('C:/customs_ai2/.env')
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        actions_text = "\n\n".join([
            f"Title: {a['title']}\nDate: {a['date']}\nURL: {a['url']}\nAbstract: {a['abstract']}"
            for a in actions
        ])
        
        prompt = f"""You are a US customs and trade compliance expert helping importers understand recent tariff changes.

ALL of the following documents are Presidential Proclamations or Executive Orders that modify US import tariffs or trade policy. They are ALL significant for importers.

For EACH document, write a plain-English summary of what it means for importers.

DOCUMENTS:
{actions_text}

Respond with ONLY a valid JSON array. No markdown, no backticks, no explanation.
Every item must have significant set to true.

Format:
[
  {{
    "summary": "Plain English: what changed and who is affected",
    "affected": "specific products or countries affected",
    "type": "increase or decrease or new or modification or suspension",
    "date": "YYYY-MM-DD",
    "url": "the document url",
    "significant": true
  }}
]"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=3000
        )
        
        text = response.choices[0].message.content.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        start = text.find("[")
        end = text.rfind("]") + 1
        if start == -1 or end == 0:
            print(f"No JSON array found: {text[:300]}")
            return []
        text = text[start:end]
        analyzed = json.loads(text)
        return analyzed
        
    except Exception as e:
        print(f"GPT analysis error: {e}")
        return []

def run_monitor():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Fetching Federal Register documents...")
    actions = fetch_recent_actions(days_back=365)
    print(f"Found {len(actions)} trade-relevant documents")
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Analyzing with GPT...")
    analyzed = analyze_actions_with_gpt(actions)
    print(f"Identified {len(analyzed)} significant tariff actions")
    
    output = {
        "last_checked": datetime.now().isoformat(),
        "last_checked_display": datetime.now().strftime("%B %d, %Y at %I:%M %p"),
        "significant_actions": analyzed,
        "raw_documents": actions[:10]
    }
    
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Saved to {OUTPUT_FILE}")
    print("\nActions found:")
    for a in analyzed:
        print(f"  - {a['date']}: {a['summary'][:80]}")
    
    return output

if __name__ == "__main__":
    run_monitor()