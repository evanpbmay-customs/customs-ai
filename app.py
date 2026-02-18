import streamlit as st
import os
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

TARIFF_LAST_UPDATED = "February 18, 2026"

TARIFF_ALERT_COUNTRIES = {
    "Vietnam": "⚠️ Vietnam is subject to 2025 reciprocal tariffs (currently ~20%, subject to change). Verify current rates at hts.usitc.gov before making import decisions.",
    "China (Section 301 tariffs apply)": "⚠️ China faces Section 301 tariffs (7.5%-25%) PLUS 2025 executive tariffs. Total additional duties may exceed 145% on some products. Verify before importing.",
    "Hong Kong (Section 301 tariffs apply)": "⚠️ Hong Kong goods are treated as Chinese-origin and subject to the same Section 301 and 2025 executive tariffs as China.",
    "Cambodia": "⚠️ Cambodia is subject to 2025 reciprocal tariffs. Rates are under active review.",
    "Bangladesh": "⚠️ Bangladesh is subject to 2025 reciprocal tariffs. Rates are under active review.",
    "India": "⚠️ India is subject to 2025 reciprocal tariffs. Rates are under active review.",
    "Thailand": "⚠️ Thailand is subject to 2025 reciprocal tariffs. Rates are under active review.",
    "Indonesia": "⚠️ Indonesia is subject to 2025 reciprocal tariffs. Rates are under active review.",
    "Taiwan": "⚠️ Taiwan is subject to 2025 reciprocal tariffs. Rates are under active review.",
    "Japan": "⚠️ Japan is subject to 2025 reciprocal tariffs. Rates are under active review.",
    "South Korea (KORUS FTA - may qualify for free)": "⚠️ South Korea is subject to 2025 reciprocal tariffs which may override KORUS FTA benefits on some products.",
    "European Union (EU)": "⚠️ EU goods are subject to 2025 reciprocal tariffs. Rates are under active review — verify current rates before making import decisions.",
    "United Kingdom": "⚠️ UK goods may be subject to 2025 reciprocal tariffs. Rates are under active review.",
    "Turkey": "⚠️ Turkey may be subject to 2025 reciprocal tariffs. Rates are under active review.",
}

def password_entered():
    if st.session_state["password"] == os.getenv("APP_PASSWORD", "customs2026"):
        st.session_state["password_correct"] = True
        del st.session_state["password"]
    else:
        st.session_state["password_correct"] = False

def check_password():
    if "password_correct" not in st.session_state:
        render_landing()
        return False
    elif not st.session_state["password_correct"]:
        render_landing()
        st.error("Incorrect password. Contact us for access.")
        return False
    return True

def render_landing():
    st.markdown("""
    <div style='text-align:center; padding:32px 0 16px 0; border-bottom:3px solid #002B5C; margin-bottom:28px;'>
        <div style='font-size:44px;'>🛃</div>
        <h1 style='font-family:Georgia,serif; font-size:2.3em; color:#002B5C; margin:8px 0 0 0;'>Customs Classifier</h1>
        <p style='color:#555; font-size:1em; margin-top:6px; font-weight:300;'>AI-powered HTS classification backed by real CBP rulings</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div style='background:#f9f9f9; border-top:3px solid #002B5C; padding:18px; border-radius:2px; height:150px;'>
            <div style='font-size:1.4em;'>📋</div>
            <div style='font-family:Georgia,serif; font-weight:700; color:#002B5C; margin:6px 0 4px; font-size:0.95em;'>HTS Classification</div>
            <div style='font-size:0.82em; color:#666;'>10-digit codes with confidence levels, backed by real CBP rulings.</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div style='background:#f9f9f9; border-top:3px solid #C9A84C; padding:18px; border-radius:2px; height:150px;'>
            <div style='font-size:1.4em;'>💰</div>
            <div style='font-family:Georgia,serif; font-weight:700; color:#002B5C; margin:6px 0 4px; font-size:0.95em;'>Duty Rate Lookup</div>
            <div style='font-size:0.82em; color:#666;'>General rates plus Section 301, 2025 tariffs, and FTA benefits.</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div style='background:#f9f9f9; border-top:3px solid #002B5C; padding:18px; border-radius:2px; height:150px;'>
            <div style='font-size:1.4em;'>💬</div>
            <div style='font-family:Georgia,serif; font-weight:700; color:#002B5C; margin:6px 0 4px; font-size:0.95em;'>Ask Follow-ups</div>
            <div style='font-size:0.82em; color:#666;'>Ask about documentation, ADD/CVD, bonding and more after each classification.</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div style='background:#002B5C; color:white; padding:24px; border-radius:2px; margin:28px 0 20px 0; text-align:center;'>
        <div style='font-family:Georgia,serif; font-size:1.5em; margin-bottom:4px;'>$49 <span style='font-size:0.55em; font-weight:300;'>/ month</span></div>
        <div style='font-size:0.8em; color:#C9A84C; letter-spacing:1px; text-transform:uppercase; font-weight:600;'>Unlimited Classifications</div>
        <div style='font-size:0.8em; color:#aac; margin-top:8px;'>Email <a href='mailto:customsclassifier@gmail.com' style='color:#C9A84C;'>customsclassifier@gmail.com</a> to get access</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='font-family:sans-serif; font-size:0.72em; font-weight:600; letter-spacing:1.8px; text-transform:uppercase; color:#002B5C; margin-bottom:6px;'>Subscriber Login</div>", unsafe_allow_html=True)
    st.text_input("Access Password", type="password", on_change=password_entered, key="password",
                  placeholder="Enter your access password", label_visibility="collapsed")

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
   - 2025 reciprocal/executive tariffs if applicable (note if paused or in flux)
   - Any trade agreement benefits (USMCA free, KORUS FTA, CAFTA, etc.)
   - Total estimated duty rate combining all applicable tariffs
5. Reasoning based on the similar CBP rulings provided
6. Most relevant ruling numbers that support this classification

Be transparent about uncertainty on 2025 tariff rates."""

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
        messages.append({"role": "user", "content": prompt})
    
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=800
    )
    
    return response.choices[0].message.content, similar_rulings

def ask_followup(question, classification, description, country):
    prompt = f"""You are an expert US customs and trade compliance specialist.

A product was just classified with the following result:

PRODUCT: {description}
COUNTRY OF ORIGIN: {country}
CLASSIFICATION RESULT:
{classification}

The user has a follow-up question: {question}

You may ONLY answer questions in these categories:
- Required import documentation (CBP Form 3461, commercial invoice, packing list, bill of lading, etc.)
- Whether the product is likely subject to antidumping (ADD) or countervailing duties (CVD)
- Whether a customs bond is required
- ISF (Importer Security Filing) requirements
- FDA, USDA, or other agency filing requirements for this product type
- What information must appear on the commercial invoice
- Country of origin marking requirements (19 CFR Part 134)
- HTS classification methodology questions

If the question is outside these categories, or involves specific dollar thresholds, rates, or rules that change frequently, respond with:
This question involves information that changes frequently and is outside the scope of what I can reliably answer. Please verify with a licensed customs broker or at cbp.gov.

Do NOT include quotation marks in your response. Do NOT guess or provide outdated information. It is better to decline than to answer incorrectly.
Answer concisely and practically. Name specific regulations where relevant."""

    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=600
    )
    return response.choices[0].message.content

# Page config
st.set_page_config(page_title="Customs Classifier AI", page_icon="🛃", layout="centered")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Merriweather:wght@400;700&family=Source+Sans+3:wght@300;400;500;600&display=swap');
    .stApp { background-color:#ffffff; }
    .block-container { padding-left:1rem !important; padding-right:1rem !important; max-width:860px !important; }
    .main-header { text-align:center; padding:32px 0 16px 0; border-bottom:3px solid #002B5C; margin-bottom:28px; }
    .main-header h1 { font-family:'Merriweather',Georgia,serif; font-size:clamp(1.6em,5vw,2.4em); color:#002B5C; margin:0; }
    .main-header p { font-family:'Source Sans 3',sans-serif; color:#555; font-size:clamp(0.9em,3vw,1.05em); margin-top:8px; font-weight:300; }
    .badge-row { display:flex; justify-content:center; gap:8px; margin:14px 0 4px 0; flex-wrap:wrap; }
    .badge { background:#002B5C; color:#C9A84C; font-family:'Source Sans 3',sans-serif; font-size:clamp(0.62em,2vw,0.72em); font-weight:600; padding:4px 10px; border-radius:2px; letter-spacing:1px; text-transform:uppercase; }
    .result-box { background:#f9f9f9; border-left:4px solid #C9A84C; border-top:1px solid #e0e0e0; border-right:1px solid #e0e0e0; border-bottom:1px solid #e0e0e0; border-radius:2px; padding:20px; margin:12px 0; box-shadow:0 1px 4px rgba(0,0,0,0.05); font-family:'Source Sans 3',sans-serif; color:#222; line-height:1.7; font-size:clamp(0.88em,2.5vw,1em); word-wrap:break-word; }
    .followup-box { background:#f0f4f9; border-left:4px solid #002B5C; border-top:1px solid #d0dce8; border-right:1px solid #d0dce8; border-bottom:1px solid #d0dce8; border-radius:2px; padding:20px; margin:12px 0; font-family:'Source Sans 3',sans-serif; color:#222; line-height:1.7; font-size:clamp(0.88em,2.5vw,1em); }
    .ruling-item { font-family:'Source Sans 3',sans-serif; font-size:clamp(0.82em,2.5vw,0.9em); color:#333; padding:7px 0; border-bottom:1px solid #f0f0f0; word-wrap:break-word; }
    .section-label { font-family:'Source Sans 3',sans-serif; font-size:0.72em; font-weight:600; letter-spacing:1.8px; text-transform:uppercase; color:#002B5C; margin-bottom:6px; margin-top:20px; }
    .stButton > button { background-color:#002B5C !important; color:#C9A84C !important; border:none !important; font-family:'Source Sans 3',sans-serif !important; font-weight:600 !important; letter-spacing:1.2px !important; text-transform:uppercase !important; padding:12px 24px !important; border-radius:2px !important; font-size:0.85em !important; transition:all 0.2s ease !important; width:100% !important; }
    .stButton > button:hover { background-color:#C9A84C !important; color:#002B5C !important; }
    a { color:#002B5C !important; }
    a:hover { color:#C9A84C !important; }
    .footer-note { text-align:center; padding:24px 0 8px 0; font-family:'Source Sans 3',sans-serif; font-size:0.78em; color:#aaa; border-top:1px solid #e0e0e0; margin-top:32px; line-height:1.6; }
    @media (max-width:640px) { [data-testid="column"] { width:100% !important; flex:1 1 100% !important; min-width:100% !important; } }
</style>
""", unsafe_allow_html=True)

if not check_password():
    st.stop()

st.markdown("""
<div class='main-header'>
    <h1>🛃 Customs Classifier</h1>
    <p>AI-powered HTS classification backed by real CBP rulings</p>
    <div class='badge-row'>
        <span class='badge'>CBP Rulings Database</span>
        <span class='badge'>GPT-4o Powered</span>
        <span class='badge'>2025 Tariffs Included</span>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<div class='section-label'>Product Description</div>", unsafe_allow_html=True)
description = st.text_area("",
    placeholder="Describe the product in detail — material, function, use case. Example: Bluetooth wireless earbuds with charging case, made of plastic and silicone, used for listening to music.",
    height=120, label_visibility="collapsed")

st.markdown("<div class='section-label'>Country of Origin</div>", unsafe_allow_html=True)
country = st.selectbox("", [
    "Not specified",
    "China (Section 301 tariffs apply)",
    "Hong Kong (Section 301 tariffs apply)",
    "Mexico (USMCA - may qualify for free)",
    "Canada (USMCA - may qualify for free)",
    "European Union (EU)",
    "United Kingdom",
    "Turkey",
    "Vietnam", "Bangladesh", "Indonesia", "Cambodia", "Thailand",
    "Myanmar", "Malaysia", "Philippines", "Sri Lanka", "Pakistan",
    "South Korea (KORUS FTA - may qualify for free)",
    "Japan", "Taiwan", "India",
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
], label_visibility="collapsed")

if country in TARIFF_ALERT_COUNTRIES:
    st.warning(TARIFF_ALERT_COUNTRIES[country])

st.markdown("<div class='section-label'>Product Image (Optional)</div>", unsafe_allow_html=True)
image_file = st.file_uploader("", type=["jpg", "jpeg", "png"], label_visibility="collapsed")

st.markdown("<br>", unsafe_allow_html=True)
classify_btn = st.button("Classify Product →", type="primary", use_container_width=True)

if classify_btn:
    if not description:
        st.error("Please enter a product description.")
    else:
        with st.spinner("Searching CBP rulings database and classifying..."):
            image_data = None
            if image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            full_description = description
            if country != "Not specified":
                full_description = f"{description}\n\nCountry of Origin: {country}"
            classification, similar_rulings = classify_product(full_description, image_data)

        st.session_state["last_classification"] = classification
        st.session_state["last_description"] = description
        st.session_state["last_country"] = country

        st.markdown("<div class='section-label'>Classification Result</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='result-box'>{classification}</div>", unsafe_allow_html=True)

        st.markdown("<div class='section-label'>Supporting CBP Rulings</div>", unsafe_allow_html=True)
        for r in similar_rulings:
            st.markdown(f"<div class='ruling-item'>📄 <a href='{r['url']}' target='_blank'>{r['ruling_number']}</a> — similarity score: {r['similarity']}</div>", unsafe_allow_html=True)

        st.markdown("<div class='section-label'>Was This Correct?</div>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Yes, correct", use_container_width=True):
                save_feedback(description, country, classification, True)
                st.success("Thanks for the feedback!")
        with col2:
            if st.button("❌ No, incorrect", use_container_width=True):
                save_feedback(description, country, classification, False)
                st.warning("Thanks — we'll use this to improve.")

        st.markdown(f"""
        <div class='footer-note'>
            For informational purposes only — not legal advice.<br>
            Tariff data last updated: {TARIFF_LAST_UPDATED} · Always verify with a licensed customs broker before making import decisions.
        </div>
        """, unsafe_allow_html=True)

if "last_classification" in st.session_state:
    st.markdown("<div class='section-label'>Ask a Follow-up Question</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-family:sans-serif; font-size:0.85em; color:#666; margin-bottom:8px;'>Examples: \"What import documents do I need?\" · \"Is this subject to ADD/CVD?\" · \"Do I need a customs bond?\" · \"What are the country of origin marking requirements?\"</div>", unsafe_allow_html=True)
    with st.form(key="followup_form"):
        followup = st.text_input("", placeholder="Ask anything about this classification...", label_visibility="collapsed")
        submitted = st.form_submit_button("Ask →", use_container_width=True)
    if submitted and followup:
        with st.spinner("Researching your question..."):
            answer = ask_followup(followup, st.session_state["last_classification"], st.session_state["last_description"], st.session_state["last_country"])
        st.markdown(f"<div class='followup-box'>{answer}</div>", unsafe_allow_html=True)