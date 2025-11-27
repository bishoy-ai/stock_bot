import os
import requests
import json
import xml.etree.ElementTree as ET
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import time
import random

# ==========================================
# 1. الإعدادات
# ==========================================
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

genai.configure(api_key=GOOGLE_API_KEY)

# قائمة وكلاء مستخدم (User Agents) للتمويه
USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
]

# ==========================================
# 2. أدوات جلب البيانات (RSS + Direct API)
# ==========================================

def get_price_direct(ticker):
    """
    يجلب السعر مباشرة من واجهة Yahoo الخلفية (JSON)
    هذه الطريقة أخف بكثير وأقل عرضة للحظر من مكتبة yfinance
    """
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d"
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        # استخراج السعر من هيكل JSON المعقد
        meta = data['chart']['result'][0]['meta']
        price = meta.get('regularMarketPrice')
        
        if price:
            return f"{price}"
    except Exception as e:
        print(f"⚠️ Price fetch failed for {ticker}: {e}")
    
    return "N/A"

def get_news_rss(ticker):
    """
    يجلب الأخبار من خدمة RSS الخاصة بجوجل.
    RSS مصمم للروبوتات، لذا هو المصدر الأكثر أماناً ضد الحظر.
    """
    # رابط RSS لأخبار سهم معين
    url = f"https://news.google.com/rss/search?q={ticker}+stock&hl=en-US&gl=US&ceid=US:en"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            # تحليل ملف XML
            root = ET.fromstring(response.content)
            news_items = []
            # نأخذ أول خبرين فقط
            for item in root.findall('./channel/item')[:2]:
                title = item.find('title').text
                # تنظيف العنوان من اسم المصدر الطويل
                clean_title = title.split(' - ')[0]
                news_items.append(f"- {clean_title}")
            
            return " | ".join(news_items)
    except Exception as e:
        print(f"⚠️ RSS fetch failed for {ticker}: {e}")
    
    return "No news available via RSS."

def collect_market_data():
    tickers = ['NVDA', 'TSLA', 'AAPL', 'BTC-USD']
    report_data = []
    
    print("🚀 Starting data collection (Stealth Mode)...")
    
    for t in tickers:
        price = get_price_direct(t)
        news = get_news_rss(t)
        
        print(f"   👉 {t}: {price} USD")
        entry = f"SYMBOL: {t} | PRICE: {price} | NEWS_TITLES: {news}"
        report_data.append(entry)
        time.sleep(1) # استراحة قصيرة
        
    return "\n".join(report_data)

# ==========================================
# 3. التحليل والإرسال
# ==========================================
def generate_report(data):
    # نستخدم الموديل المستقر
    model = genai.GenerativeModel('models/gemini-1.5-flash')
    
    safety = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }

    prompt = f"""
    Acting as a financial bot, verify this data and write a Telegram summary in Arabic.
    
    Input Data:
    {data}
    
    Instructions:
    1. If price is 'N/A', just mention the news.
    2. Use emojis for trends (📈/📉).
    3. Keep it VERY short.
    4. Start with: 🔥 *تقرير الأسواق اليومي*
    """
    
    try:
        response = model.generate_content(prompt, safety_settings=safety)
        return response.text
    except Exception as e:
        return f"AI Error: {e}"

def send_telegram(msg):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID: return
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    )

if __name__ == "__main__":
    try:
        data = collect_market_data()
        final_msg = generate_report(data)
        send_telegram(final_msg)
        print("✅ Finished.")
    except Exception as e:
        send_telegram(f"❌ Script Crash: {e}")
