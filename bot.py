import telebot
import sqlite3
import hashlib
import os
from datetime import datetime, timedelta
from telebot import types
from flask import Flask, request

# ========== CONFIG - CHANGE THESE 3 LINES ==========
BOT_TOKEN = "8665740327:AAFTlgtFCg8B5hNlE46NcP8kUlt5rZ3FOaI" # Get from @BotFather
ADMIN_ID = 7440168853 # Get from @userinfobot
MIN_WITHDRAW = 2.00
MONETAG_LINK = "https://google.com/recaptcha/api2/demo" # Get from Monetag.com
# ===================================================

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Database setup - Render uses /tmp for temp files
DB_PATH = '/tmp/koloti.db'
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users
               (user_id INTEGER PRIMARY KEY, username TEXT, balance REAL DEFAULT 0, pin TEXT, password TEXT,
                ref_by INTEGER DEFAULT 0, ref_count INTEGER DEFAULT 0, last_daily TEXT, task_count INTEGER DEFAULT 0,
                join_date TEXT, state TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS withdraws
               (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, method TEXT,
                account TEXT, status TEXT DEFAULT 'pending', date TEXT)''')
conn.commit()

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('💰 Balance', '📋 Tasks')
    markup.row('🎁 Daily', '👥 Refer')
    markup.row('💸 Withdraw', '💳 Deposit')
    return markup

def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone()

def update_balance(user_id, amount):
    cursor.execute("UPDATE users SET balance = balance +? WHERE user_id=?", (amount, user_id))
    conn.commit()

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    username = message.from_user.username or message.from_user.first_name
    ref_by = 0
    if len(message.text.split()) > 1:
        try:
            ref_by = int(message.text.split()[1])
            if ref_by == user_id: ref_by = 0
        except: pass

    user = get_user(user_id)
    if not user:
        cursor.execute("INSERT INTO users (user_id, username, balance, ref_by, join_date) VALUES (?,?,?,?,?)",
                      (user_id, username, 0.10, ref_by, datetime.now().strftime('%Y-%m-%d %H:%M')))
        conn.commit()
        if ref_by!= 0:
            update_balance(ref_by, 0.05)
            cursor.execute("UPDATE users SET ref_count = ref_count + 1 WHERE user_id=?", (ref_by,))
            conn.commit()
            try: bot.send_message(ref_by, f"🎉 New Referral! +$0.05 bonus")
            except: pass
        bot.reply_to(message, f"Welcome {username}! 🎁\n\nJoining Bonus: $0.10\n\nUse the buttons below", reply_markup=main_menu())
    else:
        bot.reply_to(message, f"Welcome back {username}!", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == '💰 Balance')
def balance(message):
    user = get_user(message.chat.id)
    if user: bot.reply_to(message, f"💰 Balance: ${user[2]:.2f}\n📋 Tasks: {user[8]}\n👥 Referrals: {user[6]}\n\nMin Withdraw: ${MIN_WITHDRAW}")
    else: bot.reply_to(message, "Send /start first")

@bot.message_handler(func=lambda m: m.text == '🎁 Daily')
def daily(message):
    user_id = message.chat.id
    user = get_user(user_id)
    if not user: return
    last_daily = user[7]
    if last_daily:
        last_time = datetime.strptime(last_daily, '%Y-%m-%d %H:%M')
        if datetime.now() - last_time < timedelta(hours=24):
            remain = timedelta(hours=24) - (datetime.now() - last_time)
            bot.reply_to(message, f"⏰ Come back after {remain.seconds//3600}h {remain.seconds%3600//60}m")
            return
    update_balance(user_id, 0.05)
    cursor.execute("UPDATE users SET last_daily=? WHERE user_id=?", (datetime.now().strftime('%Y-%m-%d %H:%M'), user_id))
    conn.commit()
    new_bal = get_user(user_id)[2]
    bot.reply_to(message, f"🎁 Daily Bonus: +$0.05\n💰 New Balance: ${new_bal:.2f}")

@bot.message_handler(func=lambda m: m.text == '📋 Tasks')
def tasks(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📺 Watch Video Ad - $0.02", callback_data="ad_0.02"))
    markup.add(types.InlineKeyboardButton("🔗 Visit Link - $0.01", callback_data="ad_0.01"))
    bot.reply_to(message, "📋 Tasks:\nComplete tasks to earn. Cheating = Ban", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('ad_'))
def ad_task(call):
    reward = float(call.data.split('_')[1])
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📺 Click to Watch Ad", url=MONETAG_LINK))
    markup.add(types.InlineKeyboardButton("✅ Done Watching", callback_data=f"verify_{reward}"))
    bot.edit_message_text("1. Click link and watch 30s Ad\n2. Come back and press Verify", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('verify_'))
def verify_ad(call):
    reward = float(call.data.split('_')[1])
    update_balance(call.message.chat.id, reward)
    cursor.execute("UPDATE users SET task_count = task_count + 1 WHERE user_id=?", (call.message.chat.id,))
    conn.commit()
    bot.answer_callback_query(call.id, f"+${reward} added!")
    new_bal = get_user(call.message.chat.id)[2]
    bot.edit_message_text(f"✅ Verified! +${reward}\n💰 Balance: ${new_bal:.2f}", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: m.text == '👥 Refer')
def refer(message):
    user_id = message.chat.id
    user = get_user(user_id)
    link = f"https://t.me/{bot.get_me().username}?start={user_id}"
    bot.reply_to(message, f"👥 Your Link:\n`{link}`\n\nPer Refer: $0.05\nTotal: {user[6]} users", parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '💸 Withdraw')
def withdraw(message):
    user = get_user(message.chat.id)
    if user[2] < MIN_WITHDRAW:
        bot.reply_to(message, f"❌ Minimum ${MIN_WITHDRAW} required\nYour Balance: ${user[2]:.2f}")
        return
    cursor.execute("UPDATE users SET state='w_amount' WHERE user_id=?", (message.chat.id,))
    conn.commit()
    bot.reply_to(message, f"💸 How much to withdraw?\nBalance: ${user[2]:.2f}\n\nSend amount only. Example: 2.5")

@bot.message_handler(func=lambda m: m.text == '💳 Deposit')
def deposit(message):
    cursor.execute("UPDATE users SET state='d_amount' WHERE user_id=?", (message.chat.id,))
    conn.commit()
    bot.reply_to(message, "💳 How much to deposit?\n\nSend amount. Then send money to bKash: 01612345678 and provide TrxID")

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    user_id = message.chat.id
    user = get_user(user_id)
    if not user: return
    state = user[10]

    if state == 'w_amount':
        try:
            amount = float(message.text)
            if amount < MIN_WITHDRAW or amount > user[2]:
                bot.reply_to(message, "❌ Invalid amount")
                return
            cursor.execute("UPDATE users SET state=? WHERE user_id=?", (f'w_method_{amount}', user_id))
            conn.commit()
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.row('bKash', 'Nagad')
            bot.reply_to(message, "📱 Select Method:", reply_markup=markup)
        except: bot.reply_to(message, "❌ Numbers only")
    elif state and state.startswith('w_method_'):
        amount = float(state.split('_')[2])
        cursor.execute("UPDATE users SET state=? WHERE user_id=?", (f'w_acc_{amount}_{message.text}', user_id))
        conn.commit()
        bot.reply_to(message, f"🔢 Send your {message.text} number:", reply_markup=types.ReplyKeyboardRemove())
    elif state and state.startswith('w_acc_'):
        parts = state.split('_')
        amount, method, account = float(parts[2]), parts[3], message.text
        cursor.execute("UPDATE users SET balance = balance -?, state='' WHERE user_id=?", (amount, user_id))
        cursor.execute("INSERT INTO withdraws (user_id, amount, method, account, date) VALUES (?,?,?,?,?)",
                      (user_id, amount, method, account, datetime.now().strftime('%Y-%m-%d %H:%M')))
        conn.commit()
        bot.reply_to(message, f"✅ Withdraw Submitted!\n💵 ${amount}\n📱 {method}: {account}", reply_markup=main_menu())
        try: bot.send_message(ADMIN_ID, f"🔔 New Withdraw\nUser: {user_id}\nAmount: ${amount}\n{method}: {account}")
        except: pass
    elif state == 'd_amount':
        try:
            amount = float(message.text)
            cursor.execute("UPDATE users SET state=? WHERE user_id=?", (f'd_trx_{amount}', user_id))
            conn.commit()
            bot.reply_to(message, f"Sent ${amount}?\nSend TrxID now")
        except: bot.reply_to(message, "❌ Numbers only")
    elif state and state.startswith('d_trx_'):
        amount = float(state.split('_')[2])
        cursor.execute("UPDATE users SET state='' WHERE user_id=?", (user_id,))
        conn.commit()
        bot.reply_to(message, "✅ Deposit Submitted! Admin will approve within 24h", reply_markup=main_menu())
        try: bot.send_message(ADMIN_ID, f"🔔 New Deposit\nUser: {user_id}\nAmount: ${amount}\nTrxID: {message.text}")
        except: pass

# Flask webhook for Render
@app.route('/' + BOT_TOKEN, methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return '!', 200

@app.route('/')
def index():
    return 'Bot is Running 24/7!', 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 10000)))