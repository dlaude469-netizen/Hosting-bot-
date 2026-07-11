"""
HOSTING BOT VERSION 3.1
WITH BUTTON-BASED FILE MANAGEMENT
"""

import os
import sys
import time
import threading
import logging
import tempfile
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread
import telebot
from telebot import types
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

# Create upload directory
UPLOAD_DIR = os.path.join(tempfile.gettempdir(), 'hosting_bot_uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Bot initialization
bot = telebot.TeleBot(BOT_TOKEN)

# Data storage
active_users = set()
user_files = {}  # {user_id: [file_list]}
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
# HELPER FUNCTIONS
# ================================

def get_main_menu():
    """Create main menu keyboard"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    btn1 = types.InlineKeyboardButton("📤 Upload File", callback_data="upload_file")
    btn2 = types.InlineKeyboardButton("📁 My Files", callback_data="my_files")
    btn3 = types.InlineKeyboardButton("📊 Status", callback_data="check_status")
    btn4 = types.InlineKeyboardButton("ℹ️ Info", callback_data="show_info")
    btn5 = types.InlineKeyboardButton("❓ Help", callback_data="show_help")
    btn6 = types.InlineKeyboardButton("🏓 Ping", callback_data="ping_test")
    
    markup.add(btn1, btn2)
    markup.add(btn3, btn4)
    markup.add(btn5, btn6)
    
    return markup

def get_files_menu(user_id):
    """Create files management keyboard with delete buttons"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    files = user_files.get(user_id, [])
    
    if not files:
        markup.add(types.InlineKeyboardButton("📭 No Files", callback_data="no_files"))
    else:
        for i, file_info in enumerate(files):
            # File info button
            file_size = f"{file_info['size']:.2f}MB"
            btn_text = f"📄 {i+1}. {file_info['name']} ({file_size})"
            markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"file_info_{i}"))
            
            # Delete button for this file
            delete_btn = types.InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_file_{i}")
            markup.add(delete_btn)
    
    # Back button
    markup.add(types.InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_menu"))
    
    return markup

def format_file_size(size_bytes):
    """Convert bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f}TB"

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
║  FILE UPLOAD & MANAGEMENT        ║
╚══════════════════════════════════╝

👤 Welcome {message.from_user.first_name}!
🆔 User ID: `{user_id}`
🎫 Tier: FREE
📊 Status: ✅ ONLINE

Click buttons below to manage files!
"""
    bot.send_message(message.chat.id, welcome, 
                    parse_mode='Markdown',
                    reply_markup=get_main_menu())

@bot.message_handler(commands=['help'])
def help_handler(message):
    help_text = """
📋 AVAILABLE COMMANDS:

/start - Open main menu
/help - Show this message

🎮 MAIN MENU FEATURES:

📤 Upload File
   → Send any file directly or click button

📁 My Files
   → View all your uploaded files
   → Delete files with button
   → See file size & upload time

📊 Status
   → Check bot status
   → View your storage usage

ℹ️ Info
   → Bot information
   → Tier details

❓ Help
   → This help message

🗑️ DELETE FILES:
   → Go to "My Files"
   → Click "🗑️ Delete" next to file
   → File will be deleted instantly
"""
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['myfiles'])
def myfiles_handler(message):
    user_id = message.from_user.id
    files = user_files.get(user_id, [])
    
    if not files:
        msg = """
📭 YOU HAVEN'T UPLOADED ANY FILES YET!

Click "📤 Upload File" button or send file directly to bot
"""
    else:
        file_list = ""
        for i, f in enumerate(files, 1):
            file_list += f"📄 {i}. {f['name']} ({f['size']:.2f}MB)\n"
        
        msg = f"""
📁 YOUR UPLOADED FILES:

{file_list}

Total: {len(files)}/3 files used

Click on file to see details or delete
"""
    
    bot.send_message(message.chat.id, msg, 
                    reply_markup=get_files_menu(user_id))

# ================================
# CALLBACK HANDLERS - BUTTONS
# ================================

@bot.callback_query_handler(func=lambda call: call.data == "back_menu")
def back_menu_callback(call):
    bot.edit_message_text(
        """
╔══════════════════════════════════╗
║  🚀 HOSTING BOT v3.1             ║
║  MAIN MENU                       ║
╚══════════════════════════════════╝

Select an option below:
""",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=get_main_menu()
    )

@bot.callback_query_handler(func=lambda call: call.data == "upload_file")
def upload_file_callback(call):
    msg = """
📤 FILE UPLOAD INSTRUCTIONS:

1️⃣ Simply send any file to this bot
2️⃣ Bot will automatically save it
3️⃣ Use "📁 My Files" to manage

📋 SUPPORTED FILES:
• Documents (.pdf, .txt, .doc, .docx)
• Images (.jpg, .png, .gif, .bmp)
• Videos (.mp4, .avi, .mkv)
• Audio (.mp3, .wav, .flac)
• Archives (.zip, .rar, .7z)
• Any other file format

⚠️ LIMITS (FREE TIER):
• Max 3 files
• Max 50MB per file
• Temporary storage

💡 TIP:
Just send the file in chat and bot will upload it!

Click "⬅️ Back to Menu" when done
"""
    bot.send_message(call.message.chat.id, msg,
                    reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_menu")
                    ))

@bot.callback_query_handler(func=lambda call: call.data == "my_files")
def my_files_callback(call):
    user_id = call.from_user.id
    files = user_files.get(user_id, [])
    
    if not files:
        msg = "📭 You haven't uploaded any files yet!"
    else:
        file_list = ""
        for i, f in enumerate(files, 1):
            file_list += f"📄 {i}. {f['name']}\n   📊 Size: {f['size']:.2f}MB\n   ⏰ {f['uploaded_at']}\n\n"
        
        msg = f"""
📁 YOUR UPLOADED FILES ({len(files)}/3):

{file_list}

Click on file name to delete it
"""
    
    bot.send_message(call.message.chat.id, msg,
                    reply_markup=get_files_menu(user_id))

@bot.callback_query_handler(func=lambda call: call.data == "check_status")
def check_status_callback(call):
    user_id = call.from_user.id
    file_count = len(user_files.get(user_id, []))
    
    msg = f"""
✅ BOT STATUS: ONLINE

📊 YOUR STORAGE:
Files: {file_count}/3
Usage: {file_count}/3 slots used
Status: {'⚠️ Full' if file_count >= 3 else '✅ Space available'}

🔧 BOT INFO:
Version: 3.1
Tier: FREE
Owner: {OWNER_ID}

⏰ Uptime: Active & Running
🚀 Features: Upload, Storage, Delete
"""
    bot.send_message(call.message.chat.id, msg,
                    reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_menu")
                    ))

@bot.callback_query_handler(func=lambda call: call.data == "show_info")
def show_info_callback(call):
    msg = """
ℹ️ BOT INFORMATION

📛 Name: HOSTING BOT
📈 Version: 3.1
🎯 Purpose: File hosting & management
🔒 Owner Only: Yes
⚙️ Status: Production

🎫 FREE TIER LIMITS:
• Max uploads: 3 files
• Max file size: 50MB per file
• Storage type: Temporary
• Supported: All file types

📤 FEATURES:
✅ Direct file upload
✅ Button-based management
✅ Delete files instantly
✅ File info tracking
✅ Automatic storage
✅ Size monitoring

🚀 HOW TO USE:
1. Send files directly to bot
2. View files with "📁 My Files"
3. Delete with "🗑️ Delete" button
4. Manage storage easily
"""
    bot.send_message(call.message.chat.id, msg,
                    reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_menu")
                    ))

@bot.callback_query_handler(func=lambda call: call.data == "show_help")
def show_help_callback(call):
    msg = """
❓ HELP & INSTRUCTIONS

🎮 MAIN MENU BUTTONS:

📤 Upload File
   Send any file to upload

📁 My Files
   View & delete your files

📊 Status
   Check storage & bot status

ℹ️ Info
   Bot details & features

❓ Help
   This message

🏓 Ping
   Test bot response

🗑️ DELETE FILES:
   1. Click "📁 My Files"
   2. Click "🗑️ Delete" next to file
   3. File deleted instantly

📤 UPLOAD FILES:
   1. Click "📤 Upload File"
   2. OR send file directly
   3. Bot saves automatically

⚠️ LIMITS:
   • 3 files max
   • 50MB per file
   • Temporary storage

💬 COMMANDS:
/start - Open menu
/help - Show help
/myfiles - Show files
"""
    bot.send_message(call.message.chat.id, msg,
                    reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_menu")
                    ))

@bot.callback_query_handler(func=lambda call: call.data == "ping_test")
def ping_test_callback(call):
    bot.answer_callback_query(call.id, "🏓 Pong! Bot is online!", show_alert=False)

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_file_"))
def delete_file_callback(call):
    user_id = call.from_user.id
    file_index = int(call.data.split("_")[-1])
    
    if user_id not in user_files or file_index >= len(user_files[user_id]):
        bot.answer_callback_query(call.id, "❌ File not found!", show_alert=True)
        return
    
    try:
        file_info = user_files[user_id][file_index]
        file_path = file_info['path']
        
        # Delete file from disk
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Remove from list
        deleted_file = user_files[user_id].pop(file_index)
        
        # Show success message
        msg = f"""
✅ FILE DELETED SUCCESSFULLY!

📄 File: {deleted_file['name']}
📊 Size: {deleted_file['size']:.2f}MB

📁 Your Storage:
{len(user_files[user_id])}/3 files remaining
"""
        
        bot.send_message(call.message.chat.id, msg,
                        reply_markup=get_files_menu(user_id))
        
        logger.info(f"File deleted: {deleted_file['name']} by user {user_id}")
        
    except Exception as e:
        logger.error(f"Delete error: {e}")
        bot.answer_callback_query(call.id, f"❌ Error: {str(e)}", show_alert=True)

# ================================
# FILE UPLOAD HANDLER
# ================================

@bot.message_handler(content_types=['document', 'photo', 'video', 'audio'])
def file_handler(message):
    user_id = message.from_user.id
    
    # Initialize user files list
    if user_id not in user_files:
        user_files[user_id] = []
    
    # Check file count
    file_count = len(user_files[user_id])
    if file_count >= 3:
        markup = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("📁 Manage Files", callback_data="my_files")
        )
        bot.reply_to(message, 
                    "❌ Upload limit reached (3 files max for FREE tier)\n\nUse button below to delete files",
                    reply_markup=markup)
        return
    
    # Get file info
    if message.content_type == 'document':
        file_info = bot.get_file(message.document.file_id)
        file_name = message.document.file_name
        file_size = message.document.file_size
    elif message.content_type == 'photo':
        file_info = bot.get_file(message.photo[-1].file_id)
        file_name = f"photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        file_size = message.photo[-1].file_size
    elif message.content_type == 'video':
        file_info = bot.get_file(message.video.file_id)
        file_name = f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        file_size = message.video.file_size
    elif message.content_type == 'audio':
        file_info = bot.get_file(message.audio.file_id)
        file_name = f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        file_size = message.audio.file_size
    else:
        bot.reply_to(message, "❌ Unsupported file type!")
        return
    
    # Check file size (50MB max for FREE)
    if file_size > 50 * 1024 * 1024:
        bot.reply_to(message, f"❌ File too large! Max 50MB\n\nYour file: {file_size / (1024*1024):.2f}MB")
        return
    
    try:
        # Download file
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Save file
        file_path = os.path.join(UPLOAD_DIR, f"{user_id}_{file_name}")
        with open(file_path, 'wb') as f:
            f.write(downloaded_file)
        
        # Store file info
        file_record = {
            "name": file_name,
            "size": file_size / (1024*1024),  # Convert to MB
            "type": message.content_type,
            "uploaded_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "path": file_path
        }
        user_files[user_id].append(file_record)
        
        # Send success message with buttons
        success_msg = f"""
✅ FILE UPLOADED SUCCESSFULLY!

📄 Name: {file_name}
📊 Size: {file_size / (1024*1024):.2f} MB
⏰ Uploaded: {file_record['uploaded_at']}

📁 Your Storage:
{len(user_files[user_id])}/3 files used

Click button below to manage files
"""
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📁 My Files", callback_data="my_files"),
            types.InlineKeyboardButton("⬅️ Back Menu", callback_data="back_menu")
        )
        
        bot.reply_to(message, success_msg, reply_markup=markup)
        logger.info(f"File uploaded: {file_name} by user {user_id}")
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        bot.reply_to(message, f"❌ Upload failed: {str(e)}")

@bot.message_handler(func=lambda message: True)
def echo_handler(message):
    markup = types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton("📤 Upload File", callback_data="upload_file")
    )
    bot.reply_to(message, 
                "📨 I didn't understand that.\n\nClick button or use /help for commands",
                reply_markup=markup)

# ================================
# STARTUP & MAIN
# ================================

def startup_message():
    logger.info("="*50)
    logger.info("🚀 HOSTING BOT VERSION 3.1")
    logger.info("🎮 BUTTON-BASED FILE MANAGEMENT")
    logger.info(f"👑 Owner ID: {OWNER_ID}")
    logger.info(f"📁 Upload Dir: {UPLOAD_DIR}")
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
