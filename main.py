import os
import requests
import sys

# 1. قراءة المفاتيح
TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
API_KEY = os.environ.get("GOOGLE_API_KEY")

print("--- DIAGNOSTIC START ---")

# 2. فحص وجود المفاتيح
if not TOKEN:
    print("❌ FAIL: TELEGRAM_TOKEN is missing from environment variables.")
    sys.exit(1)
else:
    print(f"✅ TELEGRAM_TOKEN found (Length: {len(TOKEN)})")

if not CHAT_ID:
    print("❌ FAIL: TELEGRAM_CHAT_ID is missing.")
    sys.exit(1)
else:
    print(f"✅ TELEGRAM_CHAT_ID found: {CHAT_ID}")

# 3. تجربة إرسال رسالة "TEST" مباشرة
print("🔄 Attempting to send test message to Telegram...")

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
payload = {
    "chat_id": CHAT_ID,
    "text": "🚨 Test Message: If you see this, the Bot is connected!",
    "parse_mode": "Markdown"
}

try:
    response = requests.post(url, json=payload)
    print(f"Server Response Code: {response.status_code}")
    print(f"Server Response Body: {response.text}")
    
    if response.status_code == 200:
        print("✅ SUCCESS! Message sent to Telegram.")
    else:
        print("❌ TELEGRAM API ERROR: The token is correct, but Telegram rejected the message.")
        print("Possibilities: Wrong Chat ID, or you didn't click /start on the bot.")
except Exception as e:
    print(f"❌ CONNECTION ERROR: {e}")

print("--- DIAGNOSTIC END ---")
