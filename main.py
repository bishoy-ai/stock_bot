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

# تمويه المتصفح
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})

# ==========================================
# 2. المستكشف الذكي للموديلات (Smart Model Selector)
# ==========================================
def get_best_available_model():
    """
    هذه الدالة تسأل جوجل عن الموديلات المتاحة وتختار أفضل واحد تلقائياً
    لحل مشكلة 404 Model Not Found
    """
    print("🔍 Searching for available Gemini models...")
    try:
        # نطلب قائمة الموديلات التي تدعم توليد النصوص
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                # نبحث عن موديلات Pro أو Flash
                if 'gemini' in m.name and ('pro' in m.name or 'flash' in m.name):
                    print(f"✅ Found working model: {m.name}")
                    return m.name
    except Exception as e:
        print(f"⚠️ Error listing models: {e}")
    
    # إذا فشل البحث، نعود للموديل القياسي كاحتياطي
    print("⚠️ Could not list models, falling back to 'gemini-pro'")
    return 'gemini-pro'

# ==========================================
# 3. جمع البيانات
# ==========================================
def get_market_data():
    tickers = ['NVDA', 'TSLA', 'AAPL', 'AMZN', 'GOOGL'] 
    full_report_data = []
    
    print("📊 Collecting data from Web & Yahoo...")
    for t in tickers:
        # جلب السعر
        price = "N/A"
        try:
            stock = yf.Ticker(t, session=session)
            if stock.fast_info and stock.fast_info.last_price:
                price = f"{stock.fast_info.last_price:.2f}"
            else:
                hist = stock.history(period='1d')
                if not hist.empty:
                    price = f"{hist['Close'].iloc[-1]:.2f}"
        except:
            pass

        # جلب الأخبار (Web Search)
        news_snippets = []
        try:
            results = DDGS().text(f"{t} stock news analyst rating today", max_results=2)
            if results:
                for res in results:
                    news_snippets.append(f"- {res['title']}")
        except:
            news_snippets.append("No news found.")

        entry = f"STOCK: {t} | PRICE: {price} | NEWS: {'; '.join(news_snippets)}"
        full_report_data.append(entry)
        time.sleep(1) 
        
    return "\n".join(full_report_data)

# ==========================================
# 4. التحليل والإرسال
# ==========================================
def generate_ai_report(data):
    # 1. نحصل على اسم الموديل الصحيح ديناميكياً
    model_name = get_best_available_model()
    
    print(f"🤖 Analyzing using: {model_name}")
    model = genai.GenerativeModel(model_name)
    
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }

    prompt = f"""
    Acting as a financial analyst, summarize these stocks for a Telegram message in Arabic.
    - Be concise.
    - Use emojis (📈, 📉).
    - Focus on the *WHY* (News).
    
    Data:
    {data}
    """
    
    try:
        response = model.generate_content(prompt, safety_settings=safety_settings)
        return response.text
    except Exception as e:
        return f"AI Generation Error ({model_name}): {str(e)}"

def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Missing Telegram Tokens")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

if __name__ == "__main__":
    try:
        data = get_market_data()
        if len(data) > 10:
            report = generate_ai_report(data)
            send_telegram_message(report)
            print("✅ Process Completed Successfully")
        else:
            send_telegram_message("❌ No data collected.")
    except Exception as e:
        err_msg = f"❌ Critical Script Error: {str(e)}"
        print(err_msg)
        send_telegram_message(err_msg)
