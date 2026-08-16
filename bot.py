import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# --- البيانات الأساسية ---
BOT_TOKEN = "8754152241:AAE1dN4fkw2Y8..."  # توكن البوت
ADMIN_ID = 123456789  # آيدي الأدمن
SMS_MAN_API_KEY = "your_sms_man_api_key_here"  # مفتاح SMS-Man

# قاعدة بيانات مؤقتة
balances = {}
forced_channels = []

# 🌐 حدد هنا حصراً الدول اللي تريدها تظهر في البوت مع معرفاتها (Country ID) الخاصة بـ SMS-Man
# يمكنك إضافة أو حذف أي دولة بسهولة من هنا:
SELECTED_COUNTRIES = [
    {"name": "🇰🇿 كازاخستان", "id": 15},
    {"name": "🇨🇳 الصين", "id": 2},
    {"name": "🇺🇸 أمريكا", "id": 1},
    {"name": "🇲🇾 ماليزيا", "id": 12},
    {"name": "🇮🇩 إندونيسيا", "id": 14},
    # أضف بقية الدول التي تشتريها هنا بهذا الشكل
]

# --- جلب الأسعار وعدد الأرقام المتاحة للدول المحددة فقط ---
def get_sms_man_prices_and_counts(country_id):
    try:
        url = f"https://api.sms-man.com/stubs/handler_api.php?api_key={SMS_MAN_API_KEY}&action=getPrices&country={country_id}&service=tg"
        response = requests.get(url, timeout=5)
        data = response.json()
        if str(country_id) in data and "tg" in data[str(country_id)]:
            service_info = data[str(country_id)]["tg"]
            price = service_info.get("cost", 0.2)
            count = service_info.get("count", 0)
            return price, count
    except Exception:
        pass
    return 0.2, 0

# --- /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    if user_id not in balances:
        balances[user_id] = 0.0

    welcome_text = f"أهلاً بك يا {user.first_name} في بوت شراء أرقام تيليجرام."
    keyboard = [
        [InlineKeyboardButton("🛒 شراء رقم وهمي", callback_data="buy_number")],
        [InlineKeyboardButton("💰 رصيدي", callback_data="my_balance")],
        [InlineKeyboardButton("⚙️ لوحة التحكم", callback_data="admin_panel")] if user_id == ADMIN_ID else []
    ]
    keyboard = [row for row in keyboard if row]
    await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard))

# --- معالج الأزرار ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "my_balance":
        bal = balances.get(user_id, 0.0)
        await query.message.edit_text(f"💰 رصيدك الحالي هو: `{bal}` دولار", parse_mode="Markdown")

    elif query.data == "buy_number":
        # عرض الدول المحددة في القائمة حصراً مع جلب السعر والعدد المتاح لكل دولة
        keyboard = []
        for country in SELECTED_COUNTRIES:
            price, count = get_sms_man_prices_and_counts(country["id"])
            btn_text = f"{country['name']} | السعر: {price}$ | العدد: {count}"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"get_num_{country['id']}")])
        
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")])
        await query.message.edit_text("🌐 **اختر الدولة المطلوبة لطلب رقم تيليجرام:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data.startswith("get_num_"):
        country_id = query.data.split("_")[2]
        await query.message.edit_text(f"⏳ جاري طلب الرقم للدولة المطلوبة...")

    elif query.data == "admin_panel" and user_id == ADMIN_ID:
        panel_text = "⚙️ **لوحة التحكم الشاملة:**"
        keyboard = [
            [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]
        ]
        await query.message.edit_text(panel_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "main_menu":
        welcome_text = "القائمة الرئيسية للبوت:"
        keyboard = [
            [InlineKeyboardButton("🛒 شراء رقم وهمي", callback_data="buy_number")],
            [InlineKeyboardButton("💰 رصيدي", callback_data="my_balance")],
            [InlineKeyboardButton("⚙️ لوحة التحكم", callback_data="admin_panel")] if user_id == ADMIN_ID else []
        ]
        keyboard = [row for row in keyboard if row]
        await query.message.edit_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard))

# --- تشغيل البوت ---
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 البوت يعمل الآن بنجاح...")
    app.run_polling()

if __name__ == "__main__":
    main()
