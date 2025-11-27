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
# 2. اختيار الموديل المستقر (Stable Model Selector)
# ==========================================
def get_stable_model_name():
    """
    هذه الدالة تختار الموديل المستقر فقط (Flash 1.5)
    وتبتعد عن الموديلات التجريبية (Experimental) التي تسبب خطأ Quota
    """
    print("🔍 Searching for STABLE Gemini models...")
    try:
        # نبحث تحديداً عن موديل Flash المستقر
        # نتجاهل أي موديل يحتوي على كلمة 'exp' أو 'preview'
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                name = m.name.lower()
                # الشرط الذهبي: نريد Flash ولا نريد التجريبي
                if 'flash' in name and '1.5' in name and 'exp' not in name and 'preview' not in name:
                    print(f"✅ Found Stable Model: {m.name}")
                    return m.name
        
        # إذا لم نجده، نبحث عن Pro المستقر
        for m in genai.list_models():
            if 'pro' in m.name and '1.5' in m.name and 'exp' not in m.name:
                return m.name

    except Exception as e:
        print(f"⚠️ Error listing models: {e}")
    
    # الخيار الأخير المضمون دائماً
    return 'models/gemini-1.5-flash'

# ==========================================
# 3. جمع البيانات
# ==========================================
def get_market_data():
    tickers = ['NVDA', 'TSLA', 'AAPL', 'AMZN', 'BTC-USD'] 
    full_report_data = []
    
    print("📊 Collecting data...")
    for t in tickers:
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

        news_snippets = []
        try:
            # تقليل عدد النتائج إلى 1 لتسريع العملية وتقليل الضغط
            results = DDGS().text(f"{t} stock news summary", max_results=1)
            if results:
                for res in results:
                    news_snippets.append(f"- {res['title']}")
        except:
            pass

        entry = f"STOCK: {t} | PRICE: {price} | NEWS: {'; '.join(news_snippets)}"
        full_report_data.append(entry)
        time.sleep(1) 
        
    return "\n".join(full_report_data)

# ==========================================
# 4. التحليل والإرسال
# ==========================================
def generate_ai_report(data):
    model_name = get_stable_model_name()
    print(f"🤖 Analyzing using: {model_name}")
    
    model = genai.GenerativeModel(model_name)
    
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }

    prompt = f"""
    You are a financial news bot. Summarize this data for Telegram in Arabic.
    - Be extremely concise.
    - Mention price and the main reason for movement.
    - Use emojis.
    
    Data:
    {data}
    """
    
    try:
        # إضافة تأخير بسيط قبل الطلب لتجنب Rate Limit
        time.sleep(2)
        response = model.generate_content(prompt, safety_settings=safety_settings)
        return response.text
    except Exception as e:
        # إذا حدث خطأ 429 مرة أخرى، ننتظر ونحاول مرة واحدة أخيرة
        if "429" in str(e):
            print("⏳ Quota hit, waiting 10 seconds and retrying...")
            time.sleep(10)
            try:
                response = model.generate_content(prompt, safety_settings=safety_settings)
                return response.text
            except:
                pass
        return f"AI Error: {str(e)}"

def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
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
        else:
            send_telegram_message("❌ No data collected.")
    except Exception as e:
        send_telegram_message(f"❌ Script Error: {str(e)}")
