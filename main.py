import os
import requests
import google.generativeai as genai
import yfinance as yf
from duckduckgo_search import DDGS


GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

genai.configure(api_key=GOOGLE_API_KEY)



def send_telegram_message(message):
    """دالة لإرسال الرسالة إلى تليجرام"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown" # لتنسيق الخط
    }
    requests.post(url, json=payload)

def search_trending_stocks():
    # هنا سنستخدم قائمة أسهم نشطة جداً لضمان وجود أخبار
    # يمكنك تعديلها لتشمل الأسهم التي تفضلها
    return ['NVDA', 'TSLA', 'AAPL', 'AMD', 'AMZN', 'MSFT', 'GOOGL', 'META']

def get_data_and_analyze(tickers):
    stock_data = []
    for ticker in tickers[:5]:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1d")
            price = hist['Close'].iloc[-1] if not hist.empty else "N/A"
            
            # جلب الأخبار
            news_summary = ""
            if stock.news:
                for n in stock.news[:2]:
                    news_summary += f"- {n['title']} ({n['publisher']})\n"
            
            stock_data.append(f"Stock: {ticker}, Price: {price}, News: {news_summary}")
        except:
            continue
            
    # إرسال لـ Gemini
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""
    لخّص تحليل هذه الأسهم في رسالة قصيرة مناسبة لتطبيق تليجرام.
    البيانات: {stock_data}
    
    التنسيق المطلوب:
    🔥 *تقرير الأسهم اليومي* 🔥
    
    *رمز السهم:* [السعر]
    📉 *التحليل:* [جملة واحدة عن الاتجاه هل هو صاعد أم هابط بناء على الأخبار]
    
    (كرر للأسهم)
    
    ⚠️ تنبيه: تحليل ذكاء اصطناعي.
    """
    response = model.generate_content(prompt)
    return response.text


if __name__ == "__main__":
    print("Starting process...")
    tickers = search_trending_stocks()
    report = get_data_and_analyze(tickers)
    send_telegram_message(report)
    print("Message sent!")
