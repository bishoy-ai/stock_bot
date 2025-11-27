import os
import requests
import google.generativeai as genai
import yfinance as yf

# ==========================================
# 1. إعداد وفحص المفاتيح
# ==========================================
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

print("--- Diagnostics ---")
if not GOOGLE_API_KEY:
    print("❌ Error: GOOGLE_API_KEY is missing! Check GitHub Secrets.")
    exit(1) # إيقاف الكود إذا لم يوجد مفتاح
else:
    print(f"✅ GOOGLE_API_KEY found (Length: {len(GOOGLE_API_KEY)})")

if not TELEGRAM_TOKEN:
    print("⚠️ Warning: TELEGRAM_TOKEN is missing. Message won't be sent.")

genai.configure(api_key=GOOGLE_API_KEY)

# ==========================================
# 2. الدوال
# ==========================================

def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Skipping Telegram: Missing token or chat_id.")
        print("Message content:", message)
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        r = requests.post(url, json=payload)
        if r.status_code == 200:
            print("✅ Telegram message sent successfully!")
        else:
            print(f"❌ Telegram failed: {r.text}")
    except Exception as e:
        print(f"❌ Telegram Error: {e}")

def get_market_data():
    print("📊 Fetching market data...")
    # قائمة أسهم ثابتة لتجنب مشاكل البحث
    tickers = ['NVDA', 'TSLA', 'AAPL', 'MSFT']
    data_summary = []
    
    for t in tickers:
        try:
            stock = yf.Ticker(t)
            # محاولة جلب السعر
            price = stock.fast_info.last_price if hasattr(stock, 'fast_info') else "N/A"
            if price == "N/A": 
                # محاولة بديلة
                hist = stock.history(period='1d')
                if not hist.empty:
                    price = hist['Close'].iloc[-1]
            
            # محاولة جلب الأخبار
            news_txt = ""
            try:
                news = stock.news
                if news:
                    news_txt = news[0]['title']
            except:
                news_txt = "No news found"
                
            data_summary.append(f"{t}: Price {price:.2f} | News: {news_txt}")
        except Exception as e:
            print(f"⚠️ Error fetching {t}: {e}")
    
    return "\n".join(data_summary)

def generate_ai_report(data):
    print("🤖 Connecting to AI...")
    
    # محاولة استخدام عدة موديلات بالترتيب في حال فشل أحدها
    models_to_try = ['gemini-1.5-flash', 'gemini-pro', 'gemini-1.5-pro-latest']
    
    model = None
    active_model_name = ""

    for m_name in models_to_try:
        try:
            print(f"Trying model: {m_name}...")
            model = genai.GenerativeModel(m_name)
            # تجربة بسيطة للتأكد أن الموديل يعمل
            response = model.generate_content("Hello")
            active_model_name = m_name
            print(f"✅ Success! Connected to {m_name}")
            break
        except Exception as e:
            print(f"❌ Failed to connect to {m_name}: {e}")
    
    if not model:
        print("❌ FATAL: Could not connect to any Gemini model.")
        # طباعة الموديلات المتاحة للمساعدة في التشخيص
        try:
            print("Available models for your key:")
            for m in genai.list_models():
                print(f"- {m.name}")
        except:
            pass
        exit(1)

    # التحليل الفعلي
    prompt = f"""
    Acting as a financial analyst, summarize these stocks for a Telegram message in Arabic.
    Keep it very short. Use emojis.
    Data:
    {data}
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"❌ Error during generation: {e}")
        return "Error generating report."

# ==========================================
# 3. التشغيل الرئيسي
# ==========================================
if __name__ == "__main__":
    data = get_market_data()
    print("Data collected:", data)
    
    if data:
        report = generate_ai_report(data)
        print("Report generated. Sending...")
        send_telegram_message(report)
    else:
        print("❌ No data collected.")
