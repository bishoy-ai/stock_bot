import os
import time
import requests
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import yfinance as yf
from duckduckgo_search import DDGS

# ==========================================
# 1. الإعدادات
# ==========================================
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

genai.configure(api_key=GOOGLE_API_KEY)

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})

# ==========================================
# 2. اختيار الموديل الصحيح (بدون تخمين)
# ==========================================
def get_working_model_name():
    print("🔍 Listing available models for your API Key...")
    valid_models = []
    try:
        for m in genai.list_models():
            # نتأكد أن الموديل يدعم توليد النصوص
            if 'generateContent' in m.supported_generation_methods:
                print(f"   - Found: {m.name}")
                valid_models.append(m.name)
        
        # الآن نختار الأفضل بناء على القائمة الفعلية
        # الأولوية 1: Flash المستقر
        for m in valid_models:
            if 'flash' in m and 'exp' not in m and '001' in m: # models/gemini-1.5-flash-001
                print(f"✅ Selected Stable Flash: {m}")
                return m

        # الأولوية 2: Flash العام
        for m in valid_models:
            if 'flash' in m and 'exp' not in m:
                print(f"✅ Selected Flash: {m}")
                return m
        
        # الأولوية 3: Pro المستقر
        for m in valid_models:
            if 'pro' in m and 'exp' not in m:
                print(f"✅ Selected Pro: {m}")
                return m

    except Exception as e:
        print(f"⚠️ Error listing models: {e}")
    
    # إذا فشل كل شيء، نستخدم الاسم القديم جداً الذي يعمل دائماً
    print("⚠️ Fallback to 'gemini-pro'")
    return 'gemini-pro'

# ==========================================
# 3. جمع البيانات
# ==========================================
def get_market_data():
    tickers = ['NVDA', 'TSLA', 'AAPL', 'BTC-USD']
    data = []
    print("📊 Fetching Data...")
    
    for t in tickers:
        try:
            # Price
            price = "N/A"
            stock = yf.Ticker(t, session=session)
            if stock.fast_info and stock.fast_info.last_price:
                price = f"{stock.fast_info.last_price:.2f}"
            
            # News (Simple Search)
            news_txt = ""
            try:
                res = DDGS().text(f"{t} stock news today", max_results=1)
                if res: news_txt = res[0]['title']
            except: pass
            
            data.append(f"{t}: {price} | News: {news_txt}")
            time.sleep(1)
        except:
            pass
            
    return "\n".join(data)

# ==========================================
# 4. التحليل والإرسال
# ==========================================
def generate_and_send():
    data = get_market_data()
    if not data:
        print("No data collected")
        return

    # الحصول على الموديل
    model_name = get_working_model_name()
    model = genai.GenerativeModel(model_name)
    
    # إعدادات الأمان
    safety = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }

    prompt = f"""
    Summarize stock status for Telegram in Arabic. Use emojis.
    Data: {data}
    """

    try:
        response = model.generate_content(prompt, safety_settings=safety)
        msg = response.text
        
        # إرسال لتليجرام
        if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
            )
            print("✅ Message Sent!")
        else:
            print("❌ Telegram tokens missing")
            
    except Exception as e:
        print(f"❌ AI Error: {e}")
        # إرسال رسالة الخطأ لتليجرام لنعرف السبب
        if TELEGRAM_TOKEN:
             requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
             json={"chat_id": TELEGRAM_CHAT_ID, "text": f"Error: {e}"})

if __name__ == "__main__":
    generate_and_send()
