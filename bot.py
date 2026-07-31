import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv
import sqlite3
import datetime
import json

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

# ==================== VERİTABANI ====================
def get_db():
    conn = sqlite3.connect("data.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            date TEXT NOT NULL,
            description TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# ==================== ADMIN KONTROL ====================
def is_admin(user_id):
    conn = get_db()
    admin = conn.execute("SELECT * FROM admins WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return admin is not None

# ==================== START ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "Bilinmiyor"
    
    keyboard = [
        [InlineKeyboardButton("📅 Etkinlikler", callback_data="events")],
        [InlineKeyboardButton("⚔️ RD4 Savaşları", callback_data="rd4")],
        [InlineKeyboardButton("🎁 Gift Kodları", callback_data="gifts")],
        [InlineKeyboardButton("📢 Duyurular", callback_data="announce")],
        [InlineKeyboardButton("📊 Yardım", callback_data="help")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"🏰 **Whiteout Survival - ATA Klan Botu**\n\n"
        f"Hoş geldin {username}!\n"
        "State 3912 / ATA\n"
        "Aşağıdaki menüden bir seçenek belirleyin:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# ==================== BUTONLAR ====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    conn = get_db()
    
    if data == "events":
        events = conn.execute("SELECT * FROM events ORDER BY date").fetchall()
        if not events:
            text = "📅 **Henüz etkinlik eklenmemiş.**"
        else:
            text = "📅 **Etkinlik Takvimi:**\n\n"
            for e in events:
                text += f"• {e['name']} - {e['date']}\n"
                if e['description']:
                    text += f"  {e['description']}\n\n"
        await query.edit_message_text(text, parse_mode="Markdown")
    
    elif data == "rd4":
        text = "⚔️ **RD4 Savaşları:**\n\n"
        text += "Henüz savaş eklenmemiş."
        await query.edit_message_text(text, parse_mode="Markdown")
    
    elif data == "gifts":
        text = "🎁 **Gift Kodları:**\n\n"
        text += "Henüz gift kodu eklenmemiş."
        await query.edit_message_text(text, parse_mode="Markdown")
    
    elif data == "announce":
        text = "📢 **Duyurular:**\n\n"
        text += "Henüz duyuru yok."
        await query.edit_message_text(text, parse_mode="Markdown")
    
    elif data == "help":
        text = (
            "📊 **Yardım Menüsü**\n\n"
            "**Herkes İçin:**\n"
            "/start - Ana menü\n"
            "/events - Etkinlikleri listele\n\n"
            "**Admin Komutları:**\n"
            "/addevent <ad> <tarih> - Etkinlik ekle\n"
            "/rmevent <id> - Etkinlik sil\n"
            "/addadmin <user_id> - Admin ekle"
        )
        await query.edit_message_text(text, parse_mode="Markdown")
    
    conn.close()

# ==================== KOMUTLAR ====================
async def add_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bu komutu kullanma yetkiniz yok!")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("Kullanım: /addevent <ad> <YYYY-MM-DD>")
        return
    
    name = context.args[0]
    date = context.args[1]
    desc = " ".join(context.args[2:]) if len(context.args) > 2 else ""
    
    conn = get_db()
    conn.execute(
        "INSERT INTO events (name, date, description) VALUES (?, ?, ?)",
        (name, date, desc)
    )
    conn.commit()
    conn.close()
    await update.message.reply_text(f"✅ Etkinlik eklendi: {name} - {date}")

async def remove_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bu komutu kullanma yetkiniz yok!")
        return
    
    if not context.args:
        await update.message.reply_text("Kullanım: /rmevent <id>")
        return
    
    event_id = context.args[0]
    conn = get_db()
    conn.execute("DELETE FROM events WHERE id=?", (event_id,))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"✅ Etkinlik silindi (ID: {event_id})")

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Kullanım: /addadmin <user_id>")
        return
    
    user_id = int(context.args[0])
    conn = get_db()
    try:
        conn.execute("INSERT INTO admins (user_id) VALUES (?)", (user_id,))
        conn.commit()
        await update.message.reply_text(f"✅ Admin eklendi: {user_id}")
    except:
        await update.message.reply_text("❌ Bu kullanıcı zaten admin.")
    conn.close()

async def events_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db()
    events = conn.execute("SELECT * FROM events ORDER BY date").fetchall()
    conn.close()
    
    if not events:
        await update.message.reply_text("📅 Henüz etkinlik yok.")
        return
    
    text = "📅 **Etkinlikler:**\n\n"
    for e in events:
        text += f"ID: {e['id']} - {e['name']} ({e['date']})\n"
    await update.message.reply_text(text, parse_mode="Markdown")

# ==================== ANA PROGRAM ====================
def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    app.add_handler(CommandHandler("events", events_list))
    app.add_handler(CommandHandler("addevent", add_event))
    app.add_handler(CommandHandler("rmevent", remove_event))
    app.add_handler(CommandHandler("addadmin", add_admin))
    
    print("🚀 Bot başlatıldı!")
    app.run_polling()

if __name__ == "__main__":
    main()
