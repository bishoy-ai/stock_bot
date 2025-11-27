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

# تمويه المتصفح لتجنب الحظر
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})

# ==========================================
# 2. الدوال
# ==========================================

def get_price(ticker):
    """جلب السعر من Yahoo مع معالجة الأخطاء"""
    try:
        stock = yf.Ticker(ticker, session=session)
        if stock.fast_info and stock.fast_info.last_price:
            return f"{stock.fast_info.last_price:.2f}"
        hist = stock.history(period='1d')
        if not hist.empty:
            return f"{hist['Close'].iloc[-1]:.2f}"
    except:
        pass
    return "N/A"

def get_diverse_news(ticker):
    """البحث في الويب عن أخبار وتحليلات"""
    print(f"🌍 Searching web for {ticker}...")
    news_summary = []
    try:
        # البحث عن الأخبار الحديثة
        results = DDGS().text(f"{ticker} stock news analysis today", max_results=3)
        if results:
            for res in results:
                title = res.get('title', '')
                body = res.get('body', '')
                source = res.get('href', '')
                news_summary.append(f"- {title}: {body} (Source: {source})")
        else:
            news_summary.append("No specific news found via search.")
    except Exception as e:
        print(f"Search error: {e}")
        news_summary.append("Could not fetch news.")
    return "\n".join(news_summary)

def get_market_data():
    # قائمة الأسهم (يمكنك زيادتها)
    tickers = ['NVDA', 'TSLA', 'AAPL', 'AMZN', 'GOOGL'] 
    full_report_data = []
    
    for t in tickers:
        price = get_price(t)
        news = get_diverse_news(t)
        
        entry = f"""
        SYMBOL: {t}
        CURRENT PRICE: {price} USD
        NEWS SNIPPETS:
        {news}
        -----------------------
        """
        full_report_data.append(entry)
        time.sleep(1) # تفادي الضغط على السيرفرات
        
    return "\n".join(full_report_data)

def generate_ai_report(data):
    print("🤖 Analyzing with Gemini 1.5 Flash...")
    
    # === التعديل هنا: استخدام الموديل الجديد ===
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }

    prompt = f"""
    أنت خبير اقتصادي. لديك بيانات من الويب عن عدة أسهم.
    المطلوب: تقرير تليجرام مختصر باللغة العربية.
    
    لكل سهم اكتب:
    - السعر.
    - جملة واحدة تشرح سبب التحرك (بناء على الأخبار المرفقة).
    - استخدم الإيموجي المناسب (🚀 لخبر جيد، 🔻 لخبر سيء).
    
    البيانات الخام:
    {data}
    """
    
    try:
        response = model.generate_content(prompt, safety_settings=safety_settings)
        return response.text
    except Exception as e:
        return f"AI Error: {str(e)}"

def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

# ==========================================
# 3. التشغيل
# ==========================================
if __name__ == "__main__":
    try:
        data = get_market_data()
        if not data.strip():
            send_telegram_message("❌ لم يتم جمع بيانات.")
        else:
            report = generate_ai_report(data)
            send_telegram_message(report)
    except Exception as e:
        send_telegram_message(f"❌ Critical Script Error: {str(e)}")
