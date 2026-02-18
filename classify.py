import os
import json
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

def classify_product(description):
    print(f"\nClassifying: {description}")
    print("Searching similar rulings...")
    
    embedding = get_embedding(description)
    
    results = index.query(vector=embedding, top_k=5, include_metadata=True)
    
    similar_rulings = []
    for match in results.matches:
        similar_rulings.append({
            "ruling_number": match.metadata.get("ruling_number"),
            "text": match.metadata.get("text"),
            "url": match.metadata.get("url"),
            "similarity": round(match.score, 3)
        })
    
    context = "\n\n".join([
        f"Ruling {r['ruling_number']} (similarity: {r['similarity']}):\n{r['text']}"
        for r in similar_rulings
    ])
    
    prompt = f"""You are an expert US customs classification specialist. 
Based on the following similar CBP rulings, classify the product described below.

SIMILAR CBP RULINGS:
{context}

PRODUCT TO CLASSIFY:
{description}

Provide:
1. The most likely HTS code (10 digits if possible)
2. Confidence level (High/Medium/Low)
3. Brief reasoning based on the similar rulings
4. The 2-3 most relevant ruling numbers that support this classification

Be concise and specific."""

    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500
    )
    
    return {
        "classification": response.choices[0].message.content,
        "similar_rulings": similar_rulings
    }

if __name__ == "__main__":
    test_product = "Bluetooth wireless earbuds with charging case, used for listening to music"
    result = classify_product(test_product)
    print("\n=== CLASSIFICATION RESULT ===")
    print(result["classification"])
    print("\n=== SIMILAR RULINGS USED ===")
    for r in result["similar_rulings"]:
        print(f"- {r['ruling_number']} (similarity: {r['similarity']}) {r['url']}")