
import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    ChatMemberHandler,
    filters,
    ContextTypes,
)

# --- البيانات الأساسية ---
BOT_TOKEN = "8754152241:AAE1dN4fkw2Y8..."  # توكن البوت
ADMIN_ID = 123456789  # آيدي الأدمن
SMS_MAN_API_KEY = "your_sms_man_api_key_here"  # مفتاح SMS-Man

# قاعدة بيانات مؤقتة
balances = {}
forced_channels = []  # قنوات الاشتراك الإجباري
maintenance_mode = False

# --- دالة التحقق من الاشتراك الإجباري ---
async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not forced_channels:
        return True
    for channel in forced_channels:
        try:
            member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ['left', 'kicked']:
                return False
        except Exception:
            pass
    return True

# --- البداية (Start) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    if user_id not in balances:
        balances[user_id] = 0.0
        # إشعار دخول مستخدم جديد للأدمن
        username = f"@{user.username}" if user.username else "لا يوجد"
        alert_text = f"👤 **عضو جديد دخل البوت!**\n\n▫️ الاسم: {user.full_name}\n▫️ الآيدي: `{user.id}`\n▫️ المعرف: {username}"
        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=alert_text, parse_mode="Markdown")
        except:
            pass

    # فحص الاشتراك الإجباري
    if not await check_subscription(user_id, context):
        keyboard = []
        for ch in forced_channels:
            keyboard.append([InlineKeyboardButton("📢 اشترك في القناة", url=f"https://t.me/{ch.replace('@', '')}")])
        keyboard.append([InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_sub")])
        
        await update.message.reply_text(
            "⚠️ **عذراً، يجب عليك الاشتراك في قنوات البوت لاستخدامه.**\nيرجى الاشتراك ثم اضغط على زر التحقق أدناه:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    welcome_text = (
        f"أهلاً بك يا {user.first_name} في بوت الأرقام والخدمات.\n\n"
        "اختر ما يناسبك من القائمة أدناه:"
    )
    
    keyboard = [
        [InlineKeyboardButton("🛒 شراء رقم وهمي", callback_data="buy_number")],
        [InlineKeyboardButton("💰 رصيدي", callback_data="my_balance")],
        [InlineKeyboardButton("⚙️ لوحة التحكم", callback_data="admin_panel")] if user_id == ADMIN_ID else []
    ]
    keyboard = [row for row in keyboard if row]

    await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard))

# --- تتبع حظر البوت ---
async def track_bot_block(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.my_chat_member
    if result:
        old_status = result.old_chat_member.status
        new_status = result.new_chat_member.status
        user = result.from_user
        
        if old_status in ['member', 'restricted'] and new_status == 'kicked':
            alert_text = f"🚨 **المستخدم قام بحظر البوت!**\n\n▫️ الاسم: {user.full_name}\n▫️ الآيدي: `{user.id}`"
            try:
                await context.bot.send_message(chat_id=ADMIN_ID, text=alert_text, parse_mode="Markdown")
            except:
                pass

# --- معالج الأزرار ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "check_sub":
        if await check_subscription(user_id, context):
            await query.message.edit_text("✅ شكراً لك! تم التحقق من اشتراكك بنجاح. ارسل /start للبدء.")
        else:
            await query.answer("❌ لم تقم بالاشتراك في جميع القنوات بعد!", show_alert=True)

    elif query.data == "my_balance":
        bal = balances.get(user_id, 0.0)
        await query.message.edit_text(f"💰 رصيدك الحالي هو: `{bal}` دولار", parse_mode="Markdown")

    elif query.data == "buy_number":
        await query.message.edit_text("🛒 خدمة شراء الأرقام قت التفعيل.")

    elif query.data == "admin_panel" and user_id == ADMIN_ID:
        panel_text = "⚙️ **لوحة تحكم الأدمن الشاملة:**"
        keyboard = [
            [InlineKeyboardButton("📢 إدارة قنوات الاشتراك الإجباري", callback_data="manage_channels")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]
        ]
        await query.message.edit_text(panel_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "main_menu":
        await query.message.edit_text("القائمة الرئيسية للبوت:")

# --- تشغيل البوت ---
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(ChatMemberHandler(track_bot_block, ChatMemberHandler.MY_CHAT_MEMBER))

    print("🤖 البوت يعمل الان بنجاح...")
    app.run_polling()

if __name__ == "__main__":
    main()
