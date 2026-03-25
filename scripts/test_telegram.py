import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import requests
from django.conf import settings

def test_telegram_bot():
    print("=" * 50)
    print("Testing Telegram Bot Connection")
    print("=" * 50)
    
    # Test if bot is working
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getMe"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data.get('ok'):
            bot = data['result']
            print(f"✅ Bot connected successfully!")
            print(f"   Bot Name: {bot.get('first_name')}")
            print(f"   Bot Username: @{bot.get('username')}")
            print(f"   Bot ID: {bot.get('id')}")
        else:
            print(f"❌ Bot connection failed: {data}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nMake sure you have added TELEGRAM_BOT_TOKEN to .env")

if __name__ == '__main__':
    test_telegram_bot()