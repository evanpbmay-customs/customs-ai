import streamlit as st
import os
import re
import base64
import csv
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone
import requests

load_dotenv('C:/customs_ai2/.env')

openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
index = pc.Index(os.getenv('PINECONE_INDEX'))

# Countries with active 2025 tariff actions
TARIFF_ALERT_COUNTRIES = {
    "Vietnam": "⚠️ Vietnam is subject to 2025 reciprocal tariffs (currently ~20%, subject to change). Rates are under active review — verify current rates at hts.usitc.gov before making import decisions.",
    "China (Section 301 tariffs apply)": "⚠️ China faces Section 301 tariffs (7.5%-25% depending on product list) PLUS 2025 executive tariffs. Total additional duties may exceed 145% on some products. Verify current rates before importing.",
    "Hong Kong (Section 301 tariffs apply)": "⚠️ Hong Kong goods are treated as Chinese-origin for tariff purposes and subject to the same Section 301 and 2025 executive tariffs as China.",
    "Cambodia": "⚠️ Cambodia is subject to 2025 reciprocal tariffs. Rates are under active review — verify current rates before making import decisions.",
    "Bangladesh": "⚠️ Bangladesh is subject to 2025 reciprocal tariffs. Rates are under active review — verify current rates before making import decisions.",
    "India": "⚠️ India is subject to 2025 reciprocal tariffs. Rates are under active review — verify current rates before making import decisions.",
    "Thailand": "⚠️ Thailand is subject to 2025 reciprocal tariffs. Rates are under active review — verify current rates before making import decisions.",
    "Indonesia": "⚠️ Indonesia is subject to 2025 reciprocal tariffs. Rates are under active review — verify current rates before making import decisions.",
    "Taiwan": "⚠️ Taiwan is subject to 2025 reciprocal tariffs. Rates are under active review — verify current rates before making import decisions.",
    "Japan": "⚠️ Japan is subject to 2025 reciprocal tariffs. Rates are under active review — verify current rates before making import decisions.",
    "South Korea (KORUS FTA - may qualify for free)": "⚠️ South Korea is subject to 2025 reciprocal tariffs which may override KORUS FTA benefits on some products. Verify current rates before making import decisions.",
    "Germany": "⚠️ Germany (EU) is subject to 2025 reciprocal tariffs. Rates are under active review — verify current rates before making import decisions.",
    "Italy": "⚠️ Italy (EU) is subject to 2025 reciprocal tariffs. Rates are under active review — verify current rates before making import decisions.",
    "France": "⚠️ France (EU) is subject to 2025 reciprocal tariffs. Rates are under active review — verify current rates before making import decisions.",
    "Spain": "⚠️ Spain (EU) is subject to 2025 reciprocal tariffs. Rates are under active review — verify current rates before making import decisions.",
    "Netherlands": "⚠️ Netherlands (EU) is subject to 2025 reciprocal tariffs. Rates are under active review — verify current rates before making import decisions.",
}

def get_embedding(text):
    response = openai_client.embeddings.create(
        input=text[:8000],
        model="text-embedding-ada-002"
    )
    return response.data[0].embedding

def save_feedback(description, country, classification, was_correct):
    feedback = {
        "timestamp": datetime.now().isoformat(),
        "description": description,
        "country": country,
        "classification": classification[:200],
        "was_correct": was_correct
    }
    file_exists = os.path.exists("feedback.csv")
    with open("feedback.csv", "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=feedback.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(feedback)

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

    prompt = f"""You are an expert US customs classification specialist with knowledge of current tariff rates.
Based on the following similar CBP rulings, classify this product.

SIMILAR CBP RULINGS:
{context}

PRODUCT DESCRIPTION:
{description}

Provide:
1. HTS Code (10 digits)
2. Confidence Level (High/Medium/Low)
3. General duty rate from the HTS schedule (e.g. "Free", "3.5%", "6.7¢/kg")
4. Country-specific tariffs based on country of origin if provided:
   - Section 301 China tariffs if applicable (List 1/2/3/4A - specify rate)
   - 2025 reciprocal/executive tariffs if applicable (note these are subject to change and some are paused)
   - Any trade agreement benefits (USMCA free, KORUS FTA, CAFTA, etc.)
   - Total estimated duty rate combining all applicable tariffs
   - Note clearly if rates are currently in flux or subject to executive action
5. Reasoning based on the similar CBP rulings provided
6. Most relevant ruling numbers that support this classification

Important: Be transparent about uncertainty on 2025 tariff rates as these have been subject to frequent executive action."""

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
        max_tokens=800
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

country = st.selectbox("Country of Origin (optional)", [
    "Not specified",
    "China (Section 301 tariffs apply)",
    "Hong Kong (Section 301 tariffs apply)",
    "Mexico (USMCA - may qualify for free)",
    "Canada (USMCA - may qualify for free)",
    "Vietnam", "Bangladesh", "Indonesia", "Cambodia", "Thailand",
    "Myanmar", "Malaysia", "Philippines", "Sri Lanka", "Pakistan",
    "South Korea (KORUS FTA - may qualify for free)",
    "Japan", "Taiwan", "India",
    "Germany", "Italy", "France", "Spain", "Netherlands",
    "United Kingdom", "Turkey",
    "Brazil", "Colombia",
    "Peru (FTA - may qualify for free)",
    "Chile (FTA - may qualify for free)",
    "Costa Rica (CAFTA - may qualify for free)",
    "El Salvador (CAFTA - may qualify for free)",
    "Guatemala (CAFTA - may qualify for free)",
    "Honduras (CAFTA - may qualify for free)",
    "Dominican Republic (CAFTA - may qualify for free)",
    "Israel (FTA - may qualify for free)",
    "Jordan (FTA - may qualify for free)",
    "Morocco (FTA - may qualify for free)",
    "South Africa", "Ethiopia",
    "Australia (FTA - may qualify for free)",
    "Singapore (FTA - may qualify for free)",
    "Other"
])

# Show tariff alert if applicable
if country in TARIFF_ALERT_COUNTRIES:
    st.warning(TARIFF_ALERT_COUNTRIES[country])

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
        st.markdown("### Was this classification correct?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Yes, correct"):
                save_feedback(description, country, classification, True)
                st.success("Thanks for the feedback!")
        with col2:
            if st.button("❌ No, incorrect"):
                save_feedback(description, country, classification, False)
                st.warning("Thanks — we'll use this to improve.")

        st.divider()
        st.caption("⚠️ This tool provides informational classifications only and does not constitute legal advice. Tariff rates — particularly 2025 executive tariffs — are subject to frequent change. Always verify current rates with a licensed customs broker before making import decisions.")