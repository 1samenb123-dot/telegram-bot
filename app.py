# ====== Professional Telegram Referral Bot (Webhook Version) ======
# Deploy ready for Render / Railway

import os
import sqlite3
from flask import Flask, request
import telebot
from telebot import types

# ====== CONFIG ======
BOT_TOKEN = "8611223786:AAEPiXghHdd-rWl0NNYEaUZ3LlObIrus0U0"
ADMIN_ID = 5009189498
CHANNEL_USERNAME = "@WaveArbah"
WEBHOOK_URL = "https://your-app-name.onrender.com/"  # ضع رابط تطبيقك هنا

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# ====== DATABASE ======
conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    ref_by INTEGER,
    points INTEGER DEFAULT 0,
    joined INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)
""")

conn.commit()

# ====== HELPERS ======
def is_subscribed(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

def add_user(user_id, ref_by=None):
    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if cursor.fetchone():
        return False

    cursor.execute("INSERT INTO users (user_id, ref_by, joined) VALUES (?, ?, 1)", (user_id, ref_by))
    if ref_by and ref_by != user_id:
        cursor.execute("UPDATE users SET points = points + 1 WHERE user_id=?", (ref_by,))
    conn.commit()
    return True

def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("👥 رابط الإحالة", "💰 نقاطي")
    if user_id == ADMIN_ID:
        markup.add("📊 لوحة الادمن")
    return markup

# ====== START ======
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    args = message.text.split()

    if not is_subscribed(user_id):
        markup = types.InlineKeyboardMarkup()
        btn = types.InlineKeyboardButton(
            "اشترك بالقناة",
            url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}"
        )
        markup.add(btn)
        bot.send_message(message.chat.id, "⚠️ يجب الاشتراك في القناة أولاً", reply_markup=markup)
        return

    ref_by = None
    if len(args) > 1:
        try:
            ref_by = int(args[1])
        except:
            pass

    add_user(user_id, ref_by)
    bot.send_message(message.chat.id, "👑 أهلاً بك في WaveArbah Bot", reply_markup=main_menu(user_id))

# ====== REFERRAL LINK ======
@bot.message_handler(func=lambda m: m.text == "👥 رابط الإحالة")
def referral(message):
    link = f"https://t.me/{bot.get_me().username}?start={message.from_user.id}"
    bot.send_message(message.chat.id, f"🔗 رابط دعوتك:\n{link}")

# ====== MY POINTS ======
@bot.message_handler(func=lambda m: m.text == "💰 نقاطي")
def my_points(message):
    cursor.execute("SELECT points FROM users WHERE user_id=?", (message.from_user.id,))
    row = cursor.fetchone()
    points = row[0] if row else 0
    bot.send_message(message.chat.id, f"💰 لديك {points} نقطة")

# ====== ADMIN PANEL ======
@bot.message_handler(func=lambda m: m.text == "📊 لوحة الادمن")
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📢 إذاعة", "📈 إحصائيات")
    markup.add("🔙 رجوع")
    bot.send_message(message.chat.id, "لوحة تحكم الادمن", reply_markup=markup)

# ====== STATS ======
@bot.message_handler(func=lambda m: m.text == "📈 إحصائيات")
def stats(message):
    if message.from_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(points) FROM users")
    total_points = cursor.fetchone()[0] or 0

    bot.send_message(message.chat.id,
        f"📊 الإحصائيات:\n\n"
        f"👥 عدد المستخدمين: {total}\n"
        f"💰 مجموع النقاط: {total_points}"
    )

# ====== BROADCAST ======
@bot.message_handler(func=lambda m: m.text == "📢 إذاعة")
def broadcast_start(message):
    if message.from_user.id != ADMIN_ID:
        return
    msg = bot.send_message(message.chat.id, "ارسل نص الإذاعة:")
    bot.register_next_step_handler(msg, broadcast_send)

def broadcast_send(message):
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    success = 0

    for user in users:
        try:
            bot.send_message(user[0], message.text)
            success += 1
        except:
            pass

    bot.send_message(message.chat.id, f"✅ تم الإرسال إلى {success} مستخدم")

# ====== BACK ======
@bot.message_handler(func=lambda m: m.text == "🔙 رجوع")
def back(message):
    bot.send_message(message.chat.id, "تم الرجوع", reply_markup=main_menu(message.from_user.id))

# ====== WEBHOOK ROUTES ======
@app.route('/', methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

@app.route('/', methods=['GET'])
def index():
    return "Bot is running", 200

# ====== SET WEBHOOK ======
bot.remove_webhook()
bot.set_webhook(url=WEBHOOK_URL)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
