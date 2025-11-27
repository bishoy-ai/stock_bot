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

# تمويه المتصفح (ضروري لـ Yahoo)
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})

# ==========================================
# 2. اختيار الموديل (الآمن والمجاني فقط)
# ==========================================
def get_safe_model():
    """
    يبحث عن موديل Flash 1.5 المستقر حصراً.
    يتجنب الموديلات التجريبية (exp/preview) لتفادي مشاكل الدفع.
    """
    print("🔍 Selecting best AI model...")
    try:
        # البحث عن الاسم الرسمي الدقيق في قائمة جوجل
        for m in genai.list_models():
            name = m.name.lower()
            # الشرط: يجب أن يكون flash و 1.5، وممنوع أن يكون experimental
            if 'flash' in name and '1.5' in name and 'exp' not in name:
                print(f"✅ Found Stable Model: {m.name}")
                return m.name
    except:
        pass
    
    # إذا فشل البحث، نستخدم الاسم القياسي الأكثر أماناً
    print("⚠️ Using default fallback model")
    return 'models/gemini-1.5-flash'

# ==========================================
# 3. جلب البيانات (سعر + أخبار)
# ==========================================
def get_data():
    # يمكنك تعديل القائمة هنا
    tickers = ['NVDA', 'TSLA', 'AAPL', 'BTC-USD']
    report_lines = []
    
    print("📊 Fetching market data...")
    
    for t in tickers:
        try:
            # 1. السعر (من Yahoo)
            price = "N/A"
            stock = yf.Ticker(t, session=session)
            
            # محاولة سريعة
            if hasattr(stock, 'fast_info') and stock.fast_info.last_price:
                price = f"{stock.fast_info.last_price:.2f}"
            else:
                # محاولة بطيئة (تاريخ)
                hist = stock.history(period='1d')
                if not hist.empty:
                    price = f"{hist['Close'].iloc[-1]:.2f}"

            # 2. الأخبار (بحث سريع في DuckDuckGo)
            news_txt = "No breaking news"
            try:
                # نبحث عن خبر واحد فقط لتخفيف الحمل
                res = DDGS().text(f"{t} stock news reason today", max_results=1)
                if res:
                    news_txt = res[0]['title']
            except:
                pass

            report_lines.append(f"📌 {t} | Price: {price} | News: {news_txt}")
            time.sleep(1) # استراحة ثانية لتجنب الحظر
            
        except Exception as e:
            print(f"Error fetching {t}: {e}")

    return "\n".join(report_lines)

# ==========================================
# 4. الذكاء الاصطناعي والإرسال
# ==========================================
def main():
    # 1. جمع البيانات
    data = get_data()
    if not data:
        send_telegram("❌ فشل جمع البيانات من المصادر.")
        return

    # 2. التجهيز للذكاء الاصطناعي
    model_name = get_safe_model()
    model = genai.GenerativeModel(model_name)
    
    # إيقاف فلاتر الأمان (للسماح بالمصطلحات المالية)
    safety = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }

    prompt = f"""
    Acting as a senior financial analyst, summarize this daily update for Telegram in Arabic.
    
    Guidelines:
    - Use emojis (📈, 📉, 💰).
    - Be concise (Short bullet points).
    - Explain *WHY* the price moved based on the news provided.
    - Format:
      🔸 *Symbol* (Price)
      👉 Analysis
    
    Data:
    {data}
    """

    print("🤖 Generating report...")
    try:
        response = model.generate_content(prompt, safety_settings=safety)
        final_msg = response.text
        
        # 3. الإرسال لتليجرام
        send_telegram(final_msg)
        print("✅ Report sent successfully!")
        
    except Exception as e:
        error_msg = f"❌ AI Error: {str(e)}"
        print(error_msg)
        send_telegram(error_msg)

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID, 
        "text": msg, 
        "parse_mode": "Markdown"
    }
    requests.post(url, json=payload)

if __name__ == "__main__":
    main()
