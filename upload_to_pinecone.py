import json
import os
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone

load_dotenv('C:/customs_ai2/.env')

openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
index = pc.Index(os.getenv('PINECONE_INDEX'))

def get_embedding(text):
    response = openai_client.embeddings.create(
        input=text[:8000],
        model="text-embedding-ada-002"
    )
    return response.data[0].embedding

def upload_rulings():
    with open('C:/customs_ai2/rulings.json', 'r') as f:
        rulings = json.load(f)
    
    print(f"Uploading {len(rulings)} rulings to Pinecone...")
    
    for i, ruling in enumerate(rulings):
        text = ruling.get('text', '')
        if not text:
            continue
        
        embedding = get_embedding(text)
        
        index.upsert(vectors=[{
            'id': ruling.get('ruling_number', str(i)),
            'values': embedding,
            'metadata': {
                'ruling_number': ruling.get('ruling_number', ''),
                'text': text[:1000],
                'url': ruling.get('url', '')
            }
        }])
        
        print(f"Uploaded {i+1}/{len(rulings)}: {ruling.get('ruling_number')}")
    
    print("Done! All rulings uploaded to Pinecone.")

if __name__ == "__main__":
    upload_rulings()