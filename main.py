import os
import time
import requests
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import yfinance as yf
from duckduckgo_search import DDGS

# ==========================================
# إعدادات
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
# أدوات جلب البيانات (Multi-Source)
# ==========================================

def get_price(ticker):
    """
    محاولة جلب السعر فقط من Yahoo.
    إذا فشل، يمكننا مستقبلاً إضافة مصدر آخر هنا.
    """
    try:
        stock = yf.Ticker(ticker, session=session)
        # نحاول جلب السعر اللحظي أو سعر الإغلاق السابق
        if stock.fast_info and stock.fast_info.last_price:
            return f"{stock.fast_info.last_price:.2f}"
        
        hist = stock.history(period='1d')
        if not hist.empty:
            return f"{hist['Close'].iloc[-1]:.2f}"
    except:
        pass
    return "N/A"

def get_diverse_news(ticker):
    """
    هنا السحر: نبحث في الويب بالكامل عن أخبار السهم
    هذا يجلب عناوين من CNBC, Reuters, Motley Fool وغيرها
    """
    print(f"🌍 Searching web for {ticker} news...")
    news_summary = []
    try:
        # نبحث عن آخر الأخبار المالية لهذا السهم
        # نستخدم backend='api' أو 'html' لنتائج أسرع
        results = DDGS().text(f"{ticker} stock analyst rating news today", max_results=3)
        
        if results:
            for res in results:
                # نأخذ العنوان واسم الموقع (إن وجد في الرابط) ومقتطف الخبر
                title = res.get('title', '')
                body = res.get('body', '')
                source = res.get('href', '')
                news_summary.append(f"- {title}: {body} (Source: {source})")
        else:
            news_summary.append("No recent news found via search.")
            
    except Exception as e:
        print(f"Search error for {ticker}: {e}")
        news_summary.append("Error fetching news.")
        
    return "\n".join(news_summary)

def get_market_data():
    tickers = ['NVDA', 'TSLA', 'AAPL', 'AMZN', 'GOOGL'] # قائمة الأسهم
    full_report_data = []
    
    for t in tickers:
        # 1. المصدر الأول: السعر من Yahoo
        price = get_price(t)
        
        # 2. المصدر الثاني: الأخبار من محرك البحث (مصادر متنوعة)
        news = get_diverse_news(t)
        
        entry = f"""
        TICKER: {t}
        PRICE: {price}USD
        WEB NEWS & ANALYSIS:
        {news}
        -----------------------
        """
        full_report_data.append(entry)
        time.sleep(1) # راحة قصيرة
        
    return "\n".join(full_report_data)

def generate_ai_report(data):
    print("🤖 Analyzing with Gemini Pro...")
    model = genai.GenerativeModel('gemini-pro')
    
    # إعدادات الأمان (مهمة جداً)
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }

    prompt = f"""
    بصفتك محللاً مالياً، قم بقراءة البيانات المجمعة من مصادر الويب المختلفة (Yahoo, News Sites).
    
    المهمة: اكتب تقريراً لتليجرام باللغة العربية.
    
    الشروط:
    1. ركز على "لماذا" السعر يتحرك (بناء على الأخبار التي وجدتها).
    2. اذكر المصدر إذا كان الخبر قوياً (مثلاً: حسب رويترز..).
    3. التنسيق:
    
    💎 *[اسم السهم]*: [السعر]
    📰 *الملخص:* [شرح السبب في سطرين]
    📊 *الاتجاه:* [صاعد/هابط/محايد]
    
    البيانات:
    {data}
    """
    
    try:
        response = model.generate_content(prompt, safety_settings=safety_settings)
        return response.text
    except Exception as e:
        return f"Gemini Analysis Error: {str(e)}"

# ==========================================
# التشغيل
# ==========================================
def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

if __name__ == "__main__":
    try:
        data = get_market_data()
        report = generate_ai_report(data)
        send_telegram_message(report)
    except Exception as e:
        send_telegram_message(f"❌ Error: {str(e)}")
