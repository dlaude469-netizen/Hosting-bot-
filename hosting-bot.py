"""
HOSTING BOT VERSION 3.1
RAILWAY COMPATIBLE VERSION
"""

import os
import sys
import time
import threading
import logging
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread
import telebot
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Get environment variables
BOT_TOKEN = os.environ.get('BOT_TOKEN')
OWNER_ID = os.environ.get('OWNER_ID')
PORT = int(os.environ.get('PORT', 8080))

# Validate configuration
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN not set")
    sys.exit(1)

if not OWNER_ID:
    logger.error("❌ OWNER_ID not set")
    sys.exit(1)

try:
    OWNER_ID = int(OWNER_ID)
except ValueError:
    logger.error("❌ OWNER_ID must be numeric")
    sys.exit(1)

# Flask app for keep-alive
app = Flask(__name__)

@app.route('/')
def home():
    return "🚀 I'm HOSTING BOT v3.1"

def run_flask():
    try:
        app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"Flask error: {e}")

def keep_alive():
    t = Thread(target=run_flask, daemon=True)
    t.start()
    logger.info("✅ Flask Keep-Alive server started")

# ================================
# CONFIGURATION
# ================================

TIER_SYSTEM = {
    "free": {
        "name": "🎫 FREE",
        "upload_limit": 3,
        "max_file_size": 50 * 1024 * 1024,
    },
    "premium": {
        "name": "⭐ PREMIUM",
        "upload_limit": 10,
        "max_file_size": 200 * 1024 * 1024,
    },
    "owner": {
        "name": "👑 OWNER",
        "upload_limit": float('inf'),
        "max_file_size": float('inf'),
    }
}

# Bot initialization
bot = telebot.TeleBot(BOT_TOKEN)

# Data storage
active_users = set()
bot_data = {}

# ================================
# MIDDLEWARE - OWNER ONLY
# ================================

from telebot.handler_backends import BaseMiddleware, CancelUpdate

class OwnerOnlyMiddleware(BaseMiddleware):
    def __init__(self):
        super().__init__()
        self.update_types = ['message', 'callback_query']

    def pre_process(self, update, data):
        user = getattr(update, 'from_user', None)
        if user is None or user.id != OWNER_ID:
            try:
                if hasattr(update, 'text'):
                    bot.reply_to(update, "🔒 This bot is private and locked to owner only.")
            except:
                pass
            return CancelUpdate()
        return None

    def post_process(self, update, data, exception=None):
        pass

bot.setup_middleware(OwnerOnlyMiddleware())

# ================================
# BOT HANDLERS
# ================================

@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = message.from_user.id
    active_users.add(user_id)
    
    welcome = f"""
╔══════════════════════════════════╗
║  🚀 HOSTING BOT v3.1             ║
║  AUTO-RECOVERY & TIER SYSTEM     ║
╚══════════════════════════════════╝

👤 Welcome {message.from_user.first_name}!
🆔 User ID: `{user_id}`
🎫 Tier: FREE
📊 Status: ✅ ONLINE

Use /help for available commands
"""
    bot.reply_to(message, welcome, parse_mode='Markdown')

@bot.message_handler(commands=['help'])
def help_handler(message):
    help_text = """
📋 AVAILABLE COMMANDS:

/start - Welcome message
/help - This help message
/status - Check bot status
/ping - Ping test
/info - Bot information
/users - Active users count
"""
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['status'])
def status_handler(message):
    try:
        import psutil
        cpu = psutil.cpu_percent()
        memory = psutil.virtual_memory().percent
        status_msg = f"""
✅ BOT STATUS: ONLINE

📊 System Info:
CPU: {cpu}%
Memory: {memory}%
Users: {len(active_users)}

⏰ Uptime: Active
🔧 Version: 3.1
"""
    except:
        status_msg = """
✅ BOT STATUS: ONLINE
🔧 Version: 3.1
👥 Users: """ + str(len(active_users))
    
    bot.reply_to(message, status_msg)

@bot.message_handler(commands=['ping'])
def ping_handler(message):
    bot.reply_to(message, "🏓 Pong!")

@bot.message_handler(commands=['info'])
def info_handler(message):
    info = f"""
ℹ️ BOT INFORMATION

📛 Name: HOSTING BOT
📈 Version: 3.1
🎯 Purpose: Multi-tier hosting management
🔒 Owner ID: {OWNER_ID}
⚙️ Status: Production

🎫 Tier System:
• FREE - 3 uploads, 50MB max
• PREMIUM - 10 uploads, 200MB max
• OWNER - Unlimited

🚀 Features:
• Auto-recovery system
• Tier management
• Process monitoring
• File hosting
"""
    bot.reply_to(message, info)

@bot.message_handler(commands=['users'])
def users_handler(message):
    bot.reply_to(message, f"👥 Active users: {len(active_users)}")

@bot.message_handler(func=lambda message: True)
def echo_handler(message):
    bot.reply_to(message, f"📨 Echo: {message.text}")

# ================================
# STARTUP & MAIN
# ================================

def startup_message():
    logger.info("="*50)
    logger.info("🚀 HOSTING BOT VERSION 3.1")
    logger.info("📊 Auto-Recovery System Enabled")
    logger.info("🎫 Tier-Based Hosting Active")
    logger.info(f"👑 Owner ID: {OWNER_ID}")
    logger.info(f"🔧 Python: {sys.version.split()[0]}")
    logger.info("="*50)
    
    try:
        me = bot.get_me()
        logger.info(f"🤖 Bot: @{me.username}")
    except Exception as e:
        logger.error(f"Error getting bot info: {e}")

if __name__ == '__main__':
    startup_message()
    
    # Start Flask keep-alive
    keep_alive()
    time.sleep(1)
    
    # Start bot polling
    logger.info("🤖 Starting bot polling...")
    
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=30)
        except requests.exceptions.ReadTimeout:
            logger.warning("⚠️ Read timeout. Restarting...")
            time.sleep(5)
        except requests.exceptions.ConnectionError:
            logger.warning("⚠️ Connection error. Retrying...")
            time.sleep(15)
        except Exception as e:
            logger.error(f"💥 Error: {e}")
            time.sleep(30)
