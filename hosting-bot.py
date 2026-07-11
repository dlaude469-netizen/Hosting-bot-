"""
HOSTING BOT VERSION 3.1
AUTO-RECOVERY SYSTEM & TIER MANAGEMENT
FONT STYLE: MATHEMATICAL BOLD SANS-SERIF
"""

import subprocess
import sys
import os

# Direct imports (NO auto-install)
import telebot
import zipfile
import tempfile
import shutil
from telebot import types
import time
from datetime import datetime, timedelta
import psutil
import sqlite3
import json
import logging
import signal
import threading
import re
import atexit
import requests
from flask import Flask
from threading import Thread
import qrcode
from io import BytesIO
import hashlib
import random
import string
from cryptography.fernet import Fernet
import base64

app = Flask('')

@app.route('/')
def home():
    return "I'm HOSTING BOT"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    print("✅ Flask Keep-Alive server started.")

# ================================
# CONFIGURATION
# ================================
TOKEN = os.environ.get('BOT_TOKEN', '8867822022:AAFrrFr3KnZRDNI__eQnd_TD7sQyXRDSJcg')
OWNER_ID = int(os.environ.get('OWNER_ID', '0'))
ADMIN_ID = 8739344756

if TOKEN == 'PUT_YOUR_BOT_TOKEN_HERE' or not TOKEN:
    raise SystemExit("❌ BOT_TOKEN environment variable not set. Set it before running the bot.")
if OWNER_ID == 0:
    raise SystemExit("❌ OWNER_ID environment variable not set. Set it to your Telegram user ID before running the bot.")

# Folder setup
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_BOTS_DIR = os.path.join(tempfile.gettempdir(), 'hosting_uploads')
HOSTING_DATA_DIR = os.path.join(tempfile.gettempdir(), 'hosting_data')
DATABASE_PATH = os.path.join(HOSTING_DATA_DIR, 'hosting_bot.db')
RUNNING_SCRIPTS_DB = os.path.join(HOSTING_DATA_DIR, 'running_scripts.json')

# TIER SYSTEM
TIER_SYSTEM = {
    "free": {
        "name": "FREE",
        "upload_limit": 3,
        "max_file_size": 50 * 1024 * 1024,
        "icon": "🎫",
        "color": "#2ecc71",
        "auto_restart": False
    },
    "premium": {
        "name": "PREMIUM",
        "upload_limit": 10,
        "max_file_size": 200 * 1024 * 1024,
        "icon": "⭐",
        "color": "#f39c12",
        "auto_restart": True
    },
    "owner": {
        "name": "OWNER",
        "upload_limit": float('inf'),
        "max_file_size": float('inf'),
        "icon": "👑",
        "color": "#e74c3c",
        "auto_restart": True
    }
}

# Create necessary directories
os.makedirs(UPLOAD_BOTS_DIR, exist_ok=True)
os.makedirs(HOSTING_DATA_DIR, exist_ok=True)

# Initialize bot
bot = telebot.TeleBot(TOKEN, use_class_middlewares=True)

# Data structures
bot_scripts = {}
user_subscriptions = {}
user_files = {}
active_users = set()
admin_ids = {ADMIN_ID, OWNER_ID}
bot_locked = False

# Logging Setup
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ================================
# MIDDLEWARE - PERSONAL-USE LOCK
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
                if hasattr(update, 'text') or hasattr(update, 'document'):
                    bot.reply_to(update, "🔒 This bot is private and locked to its owner only.")
                else:
                    bot.answer_callback_query(update.id, "🔒 Not authorized.", show_alert=True)
            except Exception:
                pass
            return CancelUpdate()
        return None

    def post_process(self, update, data, exception=None):
        pass

bot.setup_middleware(OwnerOnlyMiddleware())

# ================================
# START COMMAND
# ================================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    active_users.add(user_id)
    
    welcome_msg = f"""
🚀 HOSTING BOT v3.1
Welcome {message.from_user.first_name}!

👤 User ID: `{user_id}`
🎫 Tier: FREE
📊 Status: Ready

Use /help for commands
"""
    
    bot.reply_to(message, welcome_msg, parse_mode='Markdown')

@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = """
📋 Available Commands:

/start - Start the bot
/help - Show this message
/status - Check bot status
/ping - Ping test
"""
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['status'])
def send_status(message):
    status_msg = f"""
✅ Bot Status: ONLINE
📊 Memory Usage: {psutil.virtual_memory().percent}%
⏱️ CPU Usage: {psutil.cpu_percent()}%
👥 Active Users: {len(active_users)}
"""
    bot.reply_to(message, status_msg)

@bot.message_handler(commands=['ping'])
def ping(message):
    bot.reply_to(message, "🏓 Pong!")

# ================================
# CLEANUP AND SHUTDOWN
# ================================
def cleanup():
    logger.warning("🔴 Shutting down... Cleaning up processes")
    logger.info("✅ Cleanup complete")

atexit.register(cleanup)

# ================================
# MAIN EXECUTION
# ================================
if __name__ == '__main__':
    logger.info("="*50)
    logger.info("🚀 HOSTING BOT VERSION 3.1")
    logger.info("📊 Auto-Recovery System Enabled")
    logger.info(f"👑 Owner ID: {OWNER_ID}")
    logger.info(f"🛡️ Admins: {len(admin_ids)}")
    logger.info("="*50)
    
    # Get bot username
    try:
        bot_username = bot.get_me().username
        logger.info(f"🤖 Bot Username: @{bot_username}")
    except Exception as e:
        logger.error(f"❌ Error getting bot username: {e}")
    
    logger.info("="*50)
    
    # Start Flask keep-alive
    keep_alive()
    
    # Start bot polling
    logger.info("🤖 Starting bot polling...")
    
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=30)
        except requests.exceptions.ReadTimeout:
            logger.warning("⚠️ Read Timeout. Restarting in 5s...")
            time.sleep(5)
        except requests.exceptions.ConnectionError as ce:
            logger.error(f"⚠️ Connection Error: {ce}. Retrying in 15s...")
            time.sleep(15)
        except Exception as e:
            logger.critical(f"💥 Unrecoverable error: {e}", exc_info=True)
            logger.info("🔄 Restarting in 30s due to critical error...")
            time.sleep(30)
        finally:
            logger.warning("🔴 Polling stopped. Will restart if in loop...")
            time.sleep(1)
