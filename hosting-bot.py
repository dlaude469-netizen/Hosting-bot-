"""
HOSTING BOT VERSION 3.1
WITH SCRIPT EXECUTION FEATURE
"""

import os
import sys
import time
import threading
import logging
import tempfile
import subprocess
from datetime import datetime
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

# Validate
if not BOT_TOKEN or not OWNER_ID:
    logger.error("❌ Missing BOT_TOKEN or OWNER_ID")
    sys.exit(1)

try:
    OWNER_ID = int(OWNER_ID)
except:
    sys.exit(1)

# Flask app
app = Flask(__name__)

@app.route('/')
def home():
    return "🚀AXXU HOSTING BOT v3.1 - Script Execution"

def run_flask():
    try:
        app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"Flask error: {e}")

def keep_alive():
    t = Thread(target=run_flask, daemon=True)
    t.start()
    logger.info("✅ Flask Keep-Alive started")

# Directories
UPLOAD_DIR = os.path.join(tempfile.gettempdir(), 'hosting_bot_scripts')
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Bot initialization
bot = telebot.TeleBot(BOT_TOKEN)

# Data storage
active_users = set()
user_scripts = {}  # {user_id: [script_list]}
running_processes = {}  # {user_id: process}

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
                    bot.reply_to(update, "🔒 Private bot - Owner only!")
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
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📤 Upload Script", callback_data="upload_script"),
        types.InlineKeyboardButton("▶️ Run Script", callback_data="run_script")
    )
    markup.add(
        types.InlineKeyboardButton("📁 My Scripts", callback_data="my_scripts"),
        types.InlineKeyboardButton("🛑 Stop Running", callback_data="stop_script")
    )
    markup.add(
        types.InlineKeyboardButton("📊 Status", callback_data="check_status"),
        types.InlineKeyboardButton("❓ Help", callback_data="show_help")
    )
    return markup

def get_scripts_menu(user_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    scripts = user_scripts.get(user_id, [])
    
    if not scripts:
        markup.add(types.InlineKeyboardButton("📭 No Scripts", callback_data="no_scripts"))
    else:
        for i, script_info in enumerate(scripts):
            btn_text = f"▶️ {i+1}. {script_info['name']}"
            markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"run_script_{i}"))
    
    markup.add(types.InlineKeyboardButton("⬅️ Back", callback_data="back_menu"))
    return markup

# ================================
# MESSAGE HANDLERS
# ================================

@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = message.from_user.id
    active_users.add(user_id)
    
    welcome = f"""
╔══════════════════════════════════╗
║  🚀 HOSTING BOT v3.1             ║
║  SCRIPT EXECUTION SYSTEM         ║
╚══════════════════════════════════╝

👤 Welcome {message.from_user.first_name}!
🆔 User ID: `{user_id}`
📊 Status: ✅ ONLINE

📤 UPLOAD & RUN PYTHON SCRIPTS!

Use buttons to manage scripts
"""
    bot.send_message(message.chat.id, welcome, 
                    parse_mode='Markdown',
                    reply_markup=get_main_menu())

@bot.message_handler(commands=['help'])
def help_handler(message):
    help_text = """
📋 SCRIPT EXECUTION BOT HELP

🎮 FEATURES:
✅ Upload Python scripts (.py)
✅ Run scripts with output capture
✅ See execution results
✅ Stop running scripts
✅ Store multiple scripts

🚀 HOW TO USE:

1️⃣ UPLOAD SCRIPT:
   • Click "📤 Upload Script" button
   • OR send .py file directly
   • Bot saves it automatically

2️⃣ RUN SCRIPT:
   • Click "▶️ Run Script" button
   • Select script to run
   • Bot executes it
   • Output shown in 1-2 seconds

3️⃣ VIEW RESULTS:
   • Script output appears
   • Errors shown clearly
   • Execution time displayed

4️⃣ STOP SCRIPT:
   • Click "🛑 Stop Running"
   • Running script stops
   • Return to menu

⚠️ LIMITS:
• Max 5 scripts
• Max 10MB per script
• Max 30 seconds execution time
• Output limit: 4000 chars

📝 SUPPORTED:
• Python 3.9+
• Any valid Python code
• print() outputs captured
• Errors displayed

💡 EXAMPLES:

Simple print:
```
print("Hello World!")
```

Math operations:
```
result = 2 + 2
print(f"Result: {result}")
```

Loop:
```
for i in range(5):
    print(i)
```

Use /start for menu!
"""
    bot.reply_to(message, help_text)

# ================================
# CALLBACK HANDLERS
# ================================

@bot.callback_query_handler(func=lambda call: call.data == "back_menu")
def back_menu(call):
    bot.edit_message_text(
        "🚀 HOSTING BOT - MAIN MENU",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=get_main_menu()
    )

@bot.callback_query_handler(func=lambda call: call.data == "upload_script")
def upload_script_callback(call):
    msg = """
📤 UPLOAD PYTHON SCRIPT

1️⃣ Send .py file directly to bot
2️⃣ Or click "Send File" below
3️⃣ Bot saves automatically
4️⃣ Use "▶️ Run Script" to execute

📝 EXAMPLE FILES:
• hello.py
• math_calc.py
• data_process.py

⚠️ LIMITS:
• Max 5 scripts
• Max 10MB per file
• .py files only

⬅️ Use Back button when done
"""
    markup = types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton("⬅️ Back", callback_data="back_menu")
    )
    bot.send_message(call.message.chat.id, msg, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "run_script")
def run_script_callback(call):
    user_id = call.from_user.id
    scripts = user_scripts.get(user_id, [])
    
    if not scripts:
        msg = "📭 No scripts uploaded yet!\n\nUse '📤 Upload Script' to add scripts"
        markup = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("⬅️ Back", callback_data="back_menu")
        )
    else:
        msg = "▶️ SELECT SCRIPT TO RUN:\n"
        markup = get_scripts_menu(user_id)
    
    bot.send_message(call.message.chat.id, msg, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("run_script_"))
def execute_script_callback(call):
    user_id = call.from_user.id
    script_index = int(call.data.split("_")[-1])
    scripts = user_scripts.get(user_id, [])
    
    if script_index >= len(scripts):
        bot.answer_callback_query(call.id, "❌ Script not found!", show_alert=True)
        return
    
    script_info = scripts[script_index]
    script_path = script_info['path']
    
    # Send "Running..." message
    status_msg = bot.send_message(call.message.chat.id, f"⏳ Running '{script_info['name']}'...\n\n⏱️ This may take up to 30 seconds")
    
    try:
        # Execute script
        result = subprocess.run(
            ['python3', script_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        output = result.stdout
        error = result.stderr
        
        # Limit output
        if len(output) > 4000:
            output = output[-4000:]
        
        if error and len(error) > 4000:
            error = error[-4000:]
        
        # Build response
        if error:
            response = f"""
❌ EXECUTION COMPLETED WITH ERRORS

📄 Script: {script_info['name']}
⏰ Time: {datetime.now().strftime('%H:%M:%S')}

📋 STDOUT:
```
{output if output else "(empty)"}
```

⚠️ STDERR:
```
{error}
```
"""
        else:
            response = f"""
✅ EXECUTION SUCCESSFUL!

📄 Script: {script_info['name']}
⏰ Time: {datetime.now().strftime('%H:%M:%S')}

📋 OUTPUT:
```
{output if output else "(no output)"}
```
"""
        
        # Edit status message with results
        bot.edit_message_text(
            response,
            call.message.chat.id,
            status_msg.message_id,
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("▶️ Run Again", callback_data=f"run_script_{script_index}"),
                types.InlineKeyboardButton("⬅️ Back", callback_data="back_menu")
            )
        )
        
        logger.info(f"Script executed: {script_info['name']} by user {user_id}")
        
    except subprocess.TimeoutExpired:
        bot.edit_message_text(
            f"⏱️ TIMEOUT! Script took too long (>30 seconds)\n\n📄 {script_info['name']}",
            call.message.chat.id,
            status_msg.message_id,
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("⬅️ Back", callback_data="back_menu")
            )
        )
    except Exception as e:
        bot.edit_message_text(
            f"❌ EXECUTION ERROR:\n\n{str(e)}",
            call.message.chat.id,
            status_msg.message_id,
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("⬅️ Back", callback_data="back_menu")
            )
        )

@bot.callback_query_handler(func=lambda call: call.data == "my_scripts")
def my_scripts_callback(call):
    user_id = call.from_user.id
    scripts = user_scripts.get(user_id, [])
    
    if not scripts:
        msg = "📭 No scripts yet!\n\nUse '📤 Upload Script' to add"
    else:
        msg = f"📁 YOUR SCRIPTS ({len(scripts)}/5):\n\n"
        for i, s in enumerate(scripts, 1):
            msg += f"{i}. {s['name']} ({s['size']:.2f}KB)\n"
        msg += "\nClick script name to run it"
    
    bot.send_message(call.message.chat.id, msg, 
                    reply_markup=get_scripts_menu(user_id))

@bot.callback_query_handler(func=lambda call: call.data == "check_status")
def check_status_callback(call):
    user_id = call.from_user.id
    scripts = user_scripts.get(user_id, [])
    
    msg = f"""
✅ BOT STATUS: ONLINE

📊 YOUR SCRIPTS: {len(scripts)}/5
📝 Total files: {len(scripts)}

🔧 FEATURES:
✅ Upload & Store
✅ Execute Scripts
✅ Capture Output
✅ Show Errors

⏱️ Limits:
• Execution: 30 seconds max
• Output: 4000 chars
• File size: 10MB max
"""
    markup = types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton("⬅️ Back", callback_data="back_menu")
    )
    bot.send_message(call.message.chat.id, msg, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "show_help")
def show_help_callback(call):
    help_text = """
❓ QUICK GUIDE

📤 UPLOAD:
Send any .py file

▶️ RUN:
Select script from list
Bot executes it
Output shown instantly

📊 OUTPUT:
✅ Prints captured
❌ Errors shown
⏰ Execution time displayed

💡 EXAMPLE SCRIPTS:

hello.py:
print("Hello World!")

math.py:
x = 10 + 20
print(f"Sum: {x}")

loop.py:
for i in range(3):
    print(i)

Use /help for full guide
"""
    markup = types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton("⬅️ Back", callback_data="back_menu")
    )
    bot.send_message(call.message.chat.id, help_text, reply_markup=markup)

# ================================
# FILE UPLOAD HANDLER
# ================================

@bot.message_handler(content_types=['document'])
def file_handler(message):
    user_id = message.from_user.id
    
    if user_id not in user_scripts:
        user_scripts[user_id] = []
    
    # Check script count
    if len(user_scripts[user_id]) >= 5:
        bot.reply_to(message, "❌ Max 5 scripts! Delete some to upload more")
        return
    
    # Check file type
    file_name = message.document.file_name
    if not file_name.endswith('.py'):
        bot.reply_to(message, "❌ Only .py files allowed!")
        return
    
    # Check file size
    file_size = message.document.file_size
    if file_size > 10 * 1024 * 1024:
        bot.reply_to(message, f"❌ File too large! Max 10MB\nYour: {file_size/(1024*1024):.2f}MB")
        return
    
    try:
        # Download file
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        # Save file
        file_path = os.path.join(UPLOAD_DIR, f"{user_id}_{file_name}")
        with open(file_path, 'wb') as f:
            f.write(downloaded)
        
        # Store info
        script_record = {
            "name": file_name,
            "size": file_size / 1024,  # KB
            "uploaded_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "path": file_path
        }
        user_scripts[user_id].append(script_record)
        
        # Success message
        success_msg = f"""
✅ SCRIPT UPLOADED!

📄 Name: {file_name}
📊 Size: {file_size/(1024):.2f} KB
⏰ Time: {script_record['uploaded_at']}

📁 Your Scripts: {len(user_scripts[user_id])}/5

Use "▶️ Run Script" to execute!
"""
        markup = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("▶️ Run Now", callback_data="run_script"),
            types.InlineKeyboardButton("⬅️ Menu", callback_data="back_menu")
        )
        bot.reply_to(message, success_msg, reply_markup=markup)
        logger.info(f"Script uploaded: {file_name} by user {user_id}")
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        bot.reply_to(message, f"❌ Upload failed: {str(e)}")

@bot.message_handler(func=lambda message: True)
def echo_handler(message):
    markup = types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton("🎮 Menu", callback_data="back_menu")
    )
    bot.reply_to(message, 
                "📨 Send .py files or use /start for menu",
                reply_markup=markup)

# ================================
# STARTUP
# ================================

if __name__ == '__main__':
    logger.info("="*50)
    logger.info("🚀 HOSTING BOT v3.1 - SCRIPT EXECUTION")
    logger.info(f"👑 Owner: {OWNER_ID}")
    logger.info(f"📁 Scripts: {UPLOAD_DIR}")
    logger.info("="*50)
    
    keep_alive()
    time.sleep(1)
    
    logger.info("🤖 Bot started!")
    
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=30)
        except requests.exceptions.ReadTimeout:
            logger.warning("⚠️ Timeout. Restarting...")
            time.sleep(5)
        except Exception as e:
            logger.error(f"💥 Error: {e}")
            time.sleep(30)
