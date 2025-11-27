import os
import requests
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold # استدعاء مكتبة الأمان
import yfinance as yf

# ==========================================
# 1. الإعدادات
# ==========================================
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

genai.configure(api_key=GOOGLE_API_KEY)

# ==========================================
# 2. الدوال
# ==========================================

def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    requests.post(url, json=payload)

def get_market_data():
    print("📊 Fetching market data...")
    # سنركز على 3 أسهم فقط لضمان سرعة الاستجابة وعدم تجاوز الحدود
    tickers = ['NVDA', 'TSLA', 'AAPL']
    data_summary = []
    
    for t in tickers:
        try:
            stock = yf.Ticker(t)
            hist = stock.history(period='1d')
            price = hist['Close'].iloc[-1] if not hist.empty else "N/A"
            
            # جلب آخر خبر واحد فقط
            news_txt = "No specific news."
            if stock.news:
                news_txt = stock.news[0]['title']
                
            data_summary.append(f"Stock: {t} | Price: {price:.2f} | News: {news_txt}")
        except:
            continue
    
    return "\n".join(data_summary)

def generate_ai_report(data):
    print("🤖 Analyzing with Gemini...")
    
    # استخدام الموديل Pro لأنه أكثر استقراراً
    model = genai.GenerativeModel('gemini-pro')
    
    # ======================================================
    # 🔥 الحل السحري: إيقاف فلاتر الأمان تماماً 🔥
    # ======================================================
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }

    prompt = f"""
    لخص وضع هذه الأسهم اليوم في رسالة قصيرة جداً لتليجرام باللغة العربية.
    استخدم الإيموجي. لا تقدم نصيحة مالية، فقط لخص الأخبار والسعر.
    
    البيانات:
    {data}
    """
    
    try:
        # إرسال الإعدادات مع الطلب
        response = model.generate_content(prompt, safety_settings=safety_settings)
        return response.text
    except Exception as e:
        # إذا حدث خطأ، أرسل لنا الخطأ نفسه لنعرف السبب
        return f"Error details: {str(e)}"

# ==========================================
# 3. التشغيل
# ==========================================
if __name__ == "__main__":
    data = get_market_data()
    if data:
        report = generate_ai_report(data)
        send_telegram_message(report)
    else:
        send_telegram_message("❌ لم أستطع جلب بيانات من Yahoo Finance.")
