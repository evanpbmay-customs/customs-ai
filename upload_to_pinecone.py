import json
import os
import time
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone

load_dotenv('C:/customs_ai2/.env')

openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
index = pc.Index(os.getenv('PINECONE_INDEX'))

BATCH_SIZE = 100
EMBEDDING_BATCH = 100

def get_embeddings_batch(texts):
    response = openai_client.embeddings.create(
        input=texts,
        model="text-embedding-ada-002"
    )
    return [r.embedding for r in response.data]

def main():
    print("Loading rulings...")
    with open('C:/customs_ai2/rulings.json', 'r') as f:
        rulings = json.load(f)
    
    total = len(rulings)
    print(f"Total rulings to upload: {total:,}")

    # Check progress file
    progress_file = 'C:/customs_ai2/upload_progress.json'
    start_index = 0
    if os.path.exists(progress_file):
        with open(progress_file) as f:
            progress = json.load(f)
            start_index = progress.get('last_index', 0)
        print(f"Resuming from index {start_index:,}")

    for i in range(start_index, total, EMBEDDING_BATCH):
        batch_rulings = rulings[i:i + EMBEDDING_BATCH]
        texts = [r['text'][:8000] for r in batch_rulings]
        
        try:
            embeddings = get_embeddings_batch(texts)
        except Exception as e:
            print(f"Embedding error at {i}: {e}")
            time.sleep(5)
            continue

        vectors = []
        for j, (ruling, embedding) in enumerate(zip(batch_rulings, embeddings)):
            vectors.append({
                "id": ruling['ruling_number'],
                "values": embedding,
                "metadata": {
                    "ruling_number": ruling['ruling_number'],
                    "text": ruling['text'][:2000],
                    "url": ruling.get('url', '')
                }
            })

        # Upload to Pinecone in batches of 100
        for k in range(0, len(vectors), BATCH_SIZE):
            pinecone_batch = vectors[k:k + BATCH_SIZE]
            try:
                index.upsert(vectors=pinecone_batch)
            except Exception as e:
                print(f"Pinecone error at {i+k}: {e}")
                time.sleep(5)

        # Save progress
        with open(progress_file, 'w') as f:
            json.dump({'last_index': i + EMBEDDING_BATCH}, f)

        print(f"Uploaded {min(i + EMBEDDING_BATCH, total):,}/{total:,} rulings")
        time.sleep(0.5)

    print(f"\nDone! All {total:,} rulings uploaded to Pinecone.")

if __name__ == "__main__":
    main()
    