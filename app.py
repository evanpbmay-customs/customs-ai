import streamlit as st
import os
import re
import base64
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone
import requests

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

def classify_product(description, image_data=None):
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
Based on the following similar CBP rulings, classify this product.

SIMILAR CBP RULINGS:
{context}

PRODUCT DESCRIPTION:
{description}

Provide:
1. HTS Code (10 digits)
2. Confidence Level (High/Medium/Low)
3. General duty rate (e.g. "Free", "3.5%", "6.7¢/kg") from the HTS
4. Country-specific tariffs if country of origin is provided:
   - Section 301 China tariff if applicable (e.g. "25% additional")
   - Any other relevant trade program (USMCA free, GSP free, etc.)
   - Total estimated duty rate combining general + additional tariffs
5. Reasoning based on similar rulings
6. Most relevant ruling numbers"""

    messages = []
    
    if image_data:
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
            ]
        })
    else:
        messages.append({
            "role": "user",
            "content": prompt
        })
    
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=700
    )
    
    return response.choices[0].message.content, similar_rulings

# App UI
st.set_page_config(page_title="customs.ai", page_icon="🛃", layout="centered")

st.title("🛃 Customs Classifier AI")
st.markdown("**Enter a product description to get an HTS classification based on real CBP rulings.**")
st.markdown("*For informational purposes only. Not legal advice.*")
st.divider()

description = st.text_area("Product Description", 
    placeholder="Example: Bluetooth wireless earbuds with charging case, used for listening to music",
    height=120)

country = st.selectbox("Country of Origin (optional)", 
    ["Not specified", "China", "Mexico", "Canada", "Vietnam", "India", 
     "Bangladesh", "Indonesia", "South Korea", "Japan", "Germany", 
     "Taiwan", "Thailand", "Brazil", "Other"])

image_file = st.file_uploader("Product Image (optional)", type=["jpg", "jpeg", "png"])

if st.button("Classify Product", type="primary"):
    if not description:
        st.error("Please enter a product description.")
    else:
        with st.spinner("Searching CBP rulings and classifying..."):
            image_data = None
            if image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            full_description = description
            if country != "Not specified":
                full_description = f"{description}\n\nCountry of Origin: {country}"
            
            classification, similar_rulings = classify_product(full_description, image_data)
        
        st.success("Classification Complete")
        st.markdown("### Result")
        st.markdown(classification)
        
        st.divider()
        st.markdown("### Similar CBP Rulings Used")
        for r in similar_rulings:
            st.markdown(f"- [{r['ruling_number']}]({r['url']}) — similarity: {r['similarity']}")
        
        st.divider()
        st.caption("⚠️ This tool provides informational classifications only and does not constitute legal advice. Verify with a licensed customs broker for binding purposes.")