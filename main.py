import os
import requests
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

# ==========================================
# 2. وظيفة "المطرقة" لاختيار الموديل (Brute Force)
# ==========================================
def get_working_model():
    """
    يجرب قائمة من الموديلات المعروفة واحداً تلو الآخر.
    أول موديل يعمل بنجاح سيتم اعتماده.
    """
    # قائمة الموديلات مرتبة من الأسرع والأحدث
    candidates = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-001",  # الاسم الرسمي الدقيق
        "gemini-1.5-flash-002",  # تحديث جديد
        "gemini-1.5-pro",
        "gemini-1.5-pro-001",
        "gemini-pro"             # الخيار القديم كاحتياطي أخير
    ]
    
    print("🤖 Searching for a working AI model...")
    
    for model_name in candidates:
        try:
            print(f"   👉 Testing: {model_name} ...", end=" ")
            model = genai.GenerativeModel(model_name)
            # تجربة توليد كلمة واحدة للتأكد من الاتصال
            model.generate_content("Hi")
            print("✅ WORKS!")
            return model_name
        except Exception as e:
            # نتجاهل الخطأ وننتقل للتالي
            print(f"❌ Failed ({e})")
            continue
            
    raise Exception("All Gemini models failed. Check API Key or Region.")

# ==========================================
# 3. جمع البيانات (Stealth Mode)
# ==========================================
def get_price_direct(ticker):
    # خدعة لجلب السعر بدون مكتبة yfinance الثقيلة
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        data = requests.get(url, headers=headers, timeout=5).json()
        price = data['chart']['result'][0]['meta']['regularMarketPrice']
        return f"{price}"
    except:
        return "N/A"

def get_news_rss(ticker):
    # جلب الأخبار عبر RSS (لا يُحظر أبداً)
    url = f"https://news.google.com/rss/search?q={ticker}+stock&hl=en-US&gl=US&ceid=US:en"
    try:
        resp = requests.get(url, timeout=5)
        root = ET.fromstring(resp.content)
        items = root.findall('./channel/item')[:2]
        titles = [i.find('title').text.split(' - ')[0] for i in items]
        return " | ".join(titles) if titles else "No news"
    except:
        return "No news"

def collect_data():
    tickers = ['NVDA', 'TSLA', 'AAPL', 'BTC-USD']
    report = []
    print("📊 Collecting Market Data...")
    
    for t in tickers:
        p = get_price_direct(t)
        n = get_news_rss(t)
        report.append(f"SYMBOL: {t} | PRICE: {p} | NEWS: {n}")
        time.sleep(1)
        
    return "\n".join(report)

# ==========================================
# 4. التقرير والإرسال
# ==========================================
def main():
    # 1. جمع البيانات
    data = collect_data()
    
    # 2. اختيار الموديل (تلقائياً)
    try:
        best_model = get_working_model()
    except Exception as e:
        send_telegram(f"❌ AI Error: {e}")
        return

    # 3. التحليل
    model = genai.GenerativeModel(best_model)
    safety = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }

    prompt = f"""
    Acting as a financial analyst, summarize this data for a Telegram post in Arabic.
    - Be concise.
    - Use emojis (📈, 📉).
    - Format: 
      🔸 *Symbol* (Price)
      👉 One line analysis.
    
    Data:
    {data}
    """
    
    print("📝 Generating Report...")
    try:
        response = model.generate_content(prompt, safety_settings=safety)
        send_telegram(response.text)
        print("✅ Message Sent!")
    except Exception as e:
        send_telegram(f"❌ Generation Error: {e}")

def send_telegram(msg):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID: return
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    )

if __name__ == "__main__":
    main()
