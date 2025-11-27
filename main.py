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
# 2. دوال جلب البيانات (استراتيجية النجاة)
# ==========================================

def get_data_for_ticker(ticker):
    """
    يحاول جلب البيانات بأي طريقة ممكنة.
    إذا فشل Yahoo، يستخدم البحث النصي.
    """
    print(f"🔍 Fetching info for {ticker}...")
    
    # --- المحاولة 1: Yahoo Finance ---
    try:
        stock = yf.Ticker(ticker, session=session)
        price = stock.fast_info.last_price
        if price:
            print(f"   ✅ Yahoo worked for {ticker}")
            # نجلب الأخبار من البحث لضمان حداثتها
            news_snippet = ""
            try:
                res = DDGS().text(f"{ticker} stock news reason today", max_results=1)
                if res: news_snippet = res[0]['title']
            except: pass
            
            return f"STOCK: {ticker} | SOURCE: YAHOO | PRICE: {price:.2f} | NEWS: {news_snippet}"
    except Exception as e:
        print(f"   ⚠️ Yahoo failed for {ticker} ({e}). Switching to Search...")

    # --- المحاولة 2: البحث العام (المنقذ) ---
    try:
        # نبحث عن السعر والخبر في نص واحد
        # Gemini سيستخرج الرقم من هذا النص
        query = f"{ticker} stock price and latest news today"
        results = DDGS().text(query, max_results=2)
        
        if results:
            print(f"   ✅ Search worked for {ticker}")
            combined_text = " | ".join([r['body'] for r in results])
            return f"STOCK: {ticker} | SOURCE: WEB_SEARCH | DATA_SNIPPET: {combined_text}"
            
    except Exception as e:
        print(f"   ❌ Search also failed for {ticker}: {e}")
        
    return None

def get_all_market_data():
    tickers = ['NVDA', 'TSLA', 'AAPL', 'BTC-USD']
    collected_data = []
    
    for t in tickers:
        info = get_data_for_ticker(t)
        if info:
            collected_data.append(info)
        time.sleep(2) # تأخير مهم جداً لتجنب الحظر
        
    return "\n".join(collected_data)

# ==========================================
# 3. الذكاء الاصطناعي
# ==========================================
def get_safe_model():
    # نستخدم الفلاش المستقر لتجنب مشاكل النسخ التجريبية
    return 'models/gemini-1.5-flash'

def generate_report(data):
    model_name = get_safe_model()
    model = genai.GenerativeModel(model_name)
    
    safety = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }

    prompt = f"""
    You are a smart financial assistant.
    I have collected raw data about stocks from the web. Some contains explicit prices, some contains text snippets describing the price.
    
    YOUR TASK:
    1. Read the data snippet for each stock.
    2. Extract the likely CURRENT PRICE from the text.
    3. Summarize the sentiment (Why is it moving?).
    4. Output a clean Telegram message in Arabic.
    
    Format:
    📈 *Symbol* (Price)
    💬 Cause of movement
    
    Raw Data:
    {data}
    """
    
    return model.generate_content(prompt, safety_settings=safety).text

# ==========================================
# 4. التشغيل الرئيسي
# ==========================================
def send_telegram(msg):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID: return
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    )

if __name__ == "__main__":
    print("🚀 Starting Bot...")
    data = get_all_market_data()
    
    if data:
        print("✅ Data collected. Analyzing...")
        try:
            report = generate_report(data)
            send_telegram(report)
            print("✅ Report sent!")
        except Exception as e:
            send_telegram(f"❌ AI Error: {e}")
    else:
        # إذا وصلنا هنا، فهذا يعني أن Yahoo والبحث كلاهما محظوران تماماً
        send_telegram("❌ فشل تام: لم أستطع الوصول للإنترنت (IP Blocked).")
