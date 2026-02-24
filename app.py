import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ====== الإعدادات ======
BOT_TOKEN = "8611223786:AAEPiXghHdd-rWl0NNYEaUZ3LlObIrus0U0"
ADMIN_ID = 5009189498
CHANNEL_USERNAME = "@WaveArbah"
REF_REWARD = 1
MIN_WITHDRAW = 5

# ====== قاعدة البيانات ======
conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0,
    invited_by INTEGER,
    referrals INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS withdrawals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount INTEGER,
    status TEXT DEFAULT 'pending'
)
""")

conn.commit()

# ====== تحقق الاشتراك ======
async def is_subscribed(user_id, context):
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# ====== /start ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    cursor.execute("SELECT * FROM users WHERE user_id=?", (user.id,))
    exists = cursor.fetchone()

    if not exists:
        invited_by = None
        if args:
            invited_by = int(args[0])
            if invited_by != user.id:
                cursor.execute("UPDATE users SET balance = balance + ?, referrals = referrals + 1 WHERE user_id=?",
                               (REF_REWARD, invited_by))

        cursor.execute("INSERT INTO users (user_id, invited_by) VALUES (?,?)",
                       (user.id, invited_by))
        conn.commit()

    if not await is_subscribed(user.id, context):
        keyboard = [[InlineKeyboardButton("اشترك بالقناة", url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}")],
                    [InlineKeyboardButton("تحقق", callback_data="check_sub")]]
        await update.message.reply_text("🚨 يجب الاشتراك بالقناة أولاً", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    keyboard = [
        [InlineKeyboardButton("👥 رابط الإحالة", callback_data="ref")],
        [InlineKeyboardButton("💰 رصيدي", callback_data="balance")],
        [InlineKeyboardButton("💸 طلب سحب", callback_data="withdraw")]
    ]

    if user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("لوحة الأدمن", callback_data="admin")])

    await update.message.reply_text("مرحباً بك في بوت الأرباح 🚀",
                                    reply_markup=InlineKeyboardMarkup(keyboard))

# ====== الأزرار ======
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == "check_sub":
        if await is_subscribed(user_id, context):
            await query.edit_message_text("✅ تم التحقق بنجاح أرسل /start")
        else:
            await query.answer("❌ لم تشترك بعد", show_alert=True)

    elif query.data == "ref":
        link = f"https://t.me/{context.bot.username}?start={user_id}"
        await query.edit_message_text(f"🔗 رابط إحالتك:\n{link}")

    elif query.data == "balance":
        cursor.execute("SELECT balance, referrals FROM users WHERE user_id=?", (user_id,))
        data = cursor.fetchone()
        await query.edit_message_text(f"💰 رصيدك: {data[0]} نقطة\n👥 عدد الإحالات: {data[1]}")

    elif query.data == "withdraw":
        cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
        balance = cursor.fetchone()[0]

        if balance < MIN_WITHDRAW:
            await query.edit_message_text(f"❌ الحد الأدنى للسحب {MIN_WITHDRAW} نقاط")
        else:
            cursor.execute("INSERT INTO withdrawals (user_id, amount) VALUES (?,?)",
                           (user_id, balance))
            cursor.execute("UPDATE users SET balance=0 WHERE user_id=?", (user_id,))
            conn.commit()
            await context.bot.send_message(ADMIN_ID,
                f"💸 طلب سحب جديد\nالمستخدم: {user_id}\nالمبلغ: {balance}")
            await query.edit_message_text("✅ تم إرسال طلب السحب للإدارة")

    elif query.data == "admin" and user_id == ADMIN_ID:
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        await query.edit_message_text(f"👑 لوحة الأدمن\n\n👥 عدد المستخدمين: {total_users}")

# ====== تشغيل البوت ======
def main():
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
