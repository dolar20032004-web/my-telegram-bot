import json
import os
import requests
from telegram import Update, LabeledPrice, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    CallbackQueryHandler, 
    MessageHandler, 
    PreCheckoutQueryHandler, 
    ChatMemberHandler,
    filters, 
    ContextTypes
)

# --- البيانات الأساسية ---
BOT_TOKEN = "8754152241:AAEldN4fkw2Y8Qncm4dopE3VJ1taQPF9hnA"
SMS_MAN_API_KEY = "CHxOs9fV4IMmWeZia3dRTAOH6REWzoyw"
ADMIN_ID = 8832960176
ASIA_PHONE = "07702645825"
FORCE_CHANNEL = "@numbers19"
DATA_FILE = "bot_data.json"
# ----------------------

users_balance = {}
user_states = {}
asia_deposit_data = {}
admins_list = [ADMIN_ID]
maintenance_mode = False

country_prices = {
    "السعر الافتراضي": 0.20,
    "الهند": 0.15,
    "إندونيسيا": 0.15,
    "كازاخستان": 0.25,
}

# قاموس شامل لترجمة أسماء الدول من الإنجليزية إلى العربية
country_names_ar = {
    "russia": "روسيا 🇷🇺",
    "kazakhstan": "كازاخستان 🇰🇿",
    "ukraine": "أوكرانيا 🇺🇦",
    "philippines": "الفلبين 🇵🇭",
    "indonesia": "إندونيسيا 🇮🇩",
    "malaysia": "ماليزيا 🇲🇾",
    "kenya": "كينيا 🇰🇪",
    "tanzania": "تنزانيا 🇹🇿",
    "vietnam": "فيتنام 🇻🇳",
    "kyrgyzstan": "قيرغيزستان 🇰🇬",
    "usa": "أمريكا 🇺🇸",
    "china": "الصين 🇨🇳",
    "romania": "رومانيا 🇷🇴",
    "poland": "بولندا 🇵🇱",
    "india": "الهند 🇮🇳",
    "brazil": "البرازيل 🇧🇷",
    "canada": "كندا 🇨🇦",
    "pakistan": "باكستان 🇵🇰",
    "myanmar": "ميانمار 🇲🇲",
    "bangladesh": "بغلاديش 🇧🇩",
    "egypt": "مصر 🇪🇬",
    "iraq": "العراق 🇮🇶"
}

def save_data():
    data = {
        "users_balance": users_balance,
        "admins_list": admins_list,
        "maintenance_mode": maintenance_mode,
        "country_prices": country_prices
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_data():
    global users_balance, admins_list, maintenance_mode, country_prices
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                users_balance = {int(k): v for k, v in data.get("users_balance", {}).items()}
                admins_list = data.get("admins_list", [ADMIN_ID])
                maintenance_mode = data.get("maintenance_mode", False)
                if "country_prices" in data:
                    country_prices.update(data["country_prices"])
        except Exception as e:
            print(f"خطأ في قراءة ملف البيانات: {e}")

load_data()

def smsman_get_balance():
    try:
        url = f"https://api.sms-man.com/control/get-balance?token={SMS_MAN_API_KEY}"
        res = requests.get(url).json()
        return res.get("balance", 0.0)
    except:
        return None

def smsman_get_countries():
    try:
        url = f"https://api.sms-man.com/control/countries?token={SMS_MAN_API_KEY}"
        return requests.get(url).json()
    except:
        return {}

def smsman_buy_number(country_id, service_id=2):
    try:
        url = f"https://api.sms-man.com/control/get-number?token={SMS_MAN_API_KEY}&country_id={country_id}&service_id={service_id}"
        res = requests.get(url).json()
        if "error_msg" in res:
            return {"success": False, "error": res.get("error_msg")}
        return {"success": True, "request_id": res.get("request_id"), "phone": res.get("number")}
    except Exception as e:
        return {"success": False, "error": str(e)}

def smsman_get_sms(request_id):
    try:
        url = f"https://api.sms-man.com/control/get-sms?token={SMS_MAN_API_KEY}&request_id={request_id}"
        res = requests.get(url).json()
        status = res.get("status")
        if status in ["success", 1, "1"]:
            return {"status": "received", "sms": res.get("sms_code")}
        elif status in ["pending", 0, "0"]:
            return {"status": "pending"}
        else:
            return {"status": "wait"}
    except:
        return {"status": "error"}

def smsman_close_number(request_id):
    try:
        url = f"https://api.sms-man.com/control/close?token={SMS_MAN_API_KEY}&request_id={request_id}"
        requests.get(url)
    except:
        pass

async def check_subscription(user_id, context: ContextTypes.DEFAULT_TYPE):
    if user_id in admins_list:
        return True
    try:
        member = await context.bot.get_chat_member(chat_id=FORCE_CHANNEL, user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
    except:
        return True 
    return False

def get_main_keyboard(user_id):
    keyboard = [
        [InlineKeyboardButton("🌐 طلب رقم تليجرام تلقائي", callback_data="api_buy_telegram")],
        [InlineKeyboardButton("شحن رصيد 👛", callback_data="deposit"), InlineKeyboardButton("الدعم الفني 💬", callback_data="support")]
    ]
    if int(user_id) in admins_list:
        keyboard.append([InlineKeyboardButton("⚙️ لوحة التحكم الشاملة (الأدمن)", callback_data="admin_panel")])
    return InlineKeyboardMarkup(keyboard)

async def track_bot_block(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if result:
        user = result.new_chat_member.user
        old_status = result.old_chat_member.status
        new_status = result.new_chat_member.status
        if old_status in ['member', 'restricted'] and new_status == 'kicked':
            username = f"@{user.username}" if user.username else "لا يوجد"
            text = f"🚨 **تنبيه: قام مستخدم بحظر البوت!**\n\n👤 الاسم: {user.full_name}\n🆔 الآيدي: `{user.id}`\n🔗 المعرف: {username}"
            for admin in admins_list:
                try:
                    await context.bot.send_message(chat_id=admin, text=text, parse_mode="Markdown")
                except:
                    pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = update.effective_user
    user_states[user_id] = None
    
    if user_id not in users_balance:
        users_balance[user_id] = 0.0
        save_data()
        
        username = f"@{user.username}" if user.username else "لا يوجد"
        alert_text = f"👤 **عضو جديد دخل البوت!**\n\n▫️ الاسم: {user.full_name}\n▫️ الآيدي: `{user.id}`\n▫️ المعرف: {username}"
        for admin in admins_list:
            try:
                await context.bot.send_message(chat_id=admin, text=alert_text, parse_mode="Markdown")
            except:
                pass

    if not await check_subscription(user_id, context):
        keyboard = [
            [InlineKeyboardButton("اشترك في القناة 📢", url=f"https://t.me/{FORCE_CHANNEL.replace('@', '')}")],
            [InlineKeyboardButton("تحقق من الاشتراك ✅", callback_data="check_sub")]
        ]
        text = f"⚠️ **عذراً، يجب عليك الاشتراك في قناة البوت أولاً لاستخدامه!**\n\n📢 القناة: {FORCE_CHANNEL}\n\nبعد الانضمام، اضغط على زر **(تحقق من الاشتراك ✅)**."
        if update.message:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        elif update.callback_query:
            try:
                await update.callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            except:
                await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    if maintenance_mode and user_id not in admins_list:
        if update.message:
            await update.message.reply_text("🛠️ البوت في وضع الصيانة حالياً.\nيرجى المحاولة لاحقاً!")
        return

    text = f"ـ 🐍 أهلاً بك عزيزي 『 †𓅓دلاࢪ 『 🎃\n\nـ ✈️ أفضل بوت لطلب أرقام تليجرام الوهمية تلقائياً\n\n🆔 معرف حسابك: {user_id}\n💵 رصيدك الحالي: ${users_balance[user_id]}"
    if update.message:
        await update.message.reply_text(text, reply_markup=get_main_keyboard(user_id))
    elif update.callback_query:
        try:
            await update.callback_query.message.edit_text(text, reply_markup=get_main_keyboard(user_id))
        except:
            await update.callback_query.message.reply_text(text, reply_markup=get_main_keyboard(user_id))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global maintenance_mode
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    if data == "check_sub":
        if await check_subscription(user_id, context):
            await query.answer("✅ تم التحقق بنجاح، شكراً للاشتراك!", show_alert=True)
            await start(update, context)
        else:
            await query.answer("❌ لم تقم بالاشتراك في القناة بعد!", show_alert=True)
        return

    if not await check_subscription(user_id, context):
        await query.answer("❌ يجب عليك الاشتراك في قناة البوت أولاً!", show_alert=True)
        await start(update, context)
        return

    if maintenance_mode and user_id not in admins_list:
        await query.answer("🛠️ البوت في وضع الصيانة حالياً!", show_alert=True)
        return

    if data == "main_menu":
        user_states[user_id] = None
        text = f"ـ 🐍 أهلاً بك عزيزي 『 †𓅓دلاࢪ 『 🎃\n\n🆔 معرف حسابك: {user_id}\n💵 رصيدك الحالي: ${users_balance.get(user_id, 0.0)}"
        try:
            await query.edit_message_text(text, reply_markup=get_main_keyboard(user_id))
        except:
            await query.message.reply_text(text, reply_markup=get_main_keyboard(user_id))
        await query.answer()

    elif data == "api_buy_telegram":
        service_id = 2
        countries = smsman_get_countries()
        keyboard = []
        if isinstance(countries, dict):
            for c_id, c_data in list(countries.items())[:15]:
                eng_code = c_data.get("code", "").lower()
                eng_title = c_data.get("title", "").lower()
                c_name = country_names_ar.get(eng_code, country_names_ar.get(eng_title, c_data.get("title", f"دولة {c_id}")))
                
                price = country_prices.get(c_name, country_prices.get("السعر الافتراضي", 0.20))
                keyboard.append([InlineKeyboardButton(f"🌍 {c_name} - ${price}", callback_data=f"apibuy_{service_id}_{c_id}")])
        
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")])
        try:
            await query.edit_message_text("🌍 اختر الدولة المطلوبة لطلب رقم تليجرام:", reply_markup=InlineKeyboardMarkup(keyboard))
        except:
            await query.message.reply_text("🌍 اختر الدولة المطلوبة لطلب رقم تليجرام:", reply_markup=InlineKeyboardMarkup(keyboard))
        await query.answer()

    elif data.startswith("apibuy_"):
        parts = data.split("_")
        service_id = parts[1]
        country_id = parts[2]
        
        countries = smsman_get_countries()
        c_data = countries.get(str(country_id), {}) if isinstance(countries, dict) else {}
        eng_code = c_data.get("code", "").lower()
        eng_title = c_data.get("title", "").lower()
        c_name = country_names_ar.get(eng_code, country_names_ar.get(eng_title, c_data.get("title", f"دولة {country_id}")))
        
        cost = country_prices.get(c_name, country_prices.get("السعر الافتراضي", 0.20))
        user_bal = users_balance.get(user_id, 0.0)
        
        if user_bal < cost:
            await query.answer(f"⚠️ رصيدك غير كافٍ!\nتكلفة الرقم: ${cost}\nرصيدك: ${user_bal}", show_alert=True)
            return
            
        res = smsman_buy_number(country_id, service_id)
        if not res["success"]:
            await query.answer(f"❌ خطأ من الموقع: {res.get('error', 'غير معروف')}", show_alert=True)
            return
            
        req_id = res["request_id"]
        phone = res["phone"]
        
        users_balance[user_id] = round(user_bal - cost, 2)
        save_data()
        
        keyboard = [
            [InlineKeyboardButton("🔄 جلب كود التحقق (SMS)", callback_data=f"getsmscode_{req_id}")],
            [InlineKeyboardButton("🔙 الرئيسية", callback_data="main_menu")]
        ]
        
        text = f"🎉 **تم طلب رقم التليجرام بنجاح!**\n\n📱 الرقم: `{phone}`\n💵 التكلفة المخصومة: ${cost}\n💰 رصيدك المتبقي: ${users_balance[user_id]}\n\n⏳ اضغط على زر (جلب كود التحقق) أدناه فور وصول الرسالة:"
        try:
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        except:
            await query.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        await query.answer("✅ تم طلب الرقم!")

    elif data.startswith("getsmscode_"):
        req_id = data.split("_")[1]
        sms_res = smsman_get_sms(req_id)
        
        if sms_res["status"] == "received":
            code = sms_res["sms"]
            smsman_close_number(req_id)
            await query.answer("✅ تم استلام الكود بنجاح!", show_alert=True)
            try:
                await query.edit_message_text(f"🎉 **كود التحقق الخاص بك هو:**\n\n`{code}`\n\n✨ شكراً لاستخدامك البوت!", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 الرئيسية", callback_data="main_menu")]]))
            except:
                pass
        else:
            await query.answer("⏳ لم تصل الرسالة بعد، حاول مرة أخرى بعد قليل.", show_alert=True)

    elif data == "deposit":
        user_states[user_id] = None
        keyboard = [
            [InlineKeyboardButton("⭐ شحن تلقائي عبر نجوم التلجرام", callback_data="pay_stars")],
            [InlineKeyboardButton("📲 شحن عبر تحويل آسياسيل", callback_data="pay_asia")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]
        ]
        try:
            await query.edit_message_text("💳 اختر وسيلة الشحن:", reply_markup=InlineKeyboardMarkup(keyboard))
        except:
            await query.message.reply_text("💳 اختر وسيلة الشحن:", reply_markup=InlineKeyboardMarkup(keyboard))
        await query.answer()

    elif data == "pay_stars":
        user_states[user_id] = "waiting_stars"
        keyboard = [[InlineKeyboardButton("🔙 إلغاء", callback_data="deposit")]]
        try:
            await query.edit_message_text("⭐ أدخل عدد النجوم للشحن (كل 1 نجمة = 0.01$):", reply_markup=InlineKeyboardMarkup(keyboard))
        except:
            await query.message.reply_text("⭐ أدخل عدد النجوم للشحن (كل 1 نجمة = 0.01$):", reply_markup=InlineKeyboardMarkup(keyboard))
        await query.answer()

    elif data == "pay_asia":
        user_states[user_id] = "waiting_asia_amount"
        keyboard = [[InlineKeyboardButton("🔙 إلغاء", callback_data="deposit")]]
        try:
            await query.edit_message_text("📲 شحن عبر تحويل آسياسيل:\n\n📌 أرسل الآن كمية كارت الآسيا المراد تحويله:\n*(ملاحظة: كل 1$ آسيا = 0.3$ رصيد بالبوت)*", reply_markup=InlineKeyboardMarkup(keyboard))
        except:
            await query.message.reply_text("📲 شحن عبر تحويل آسياسيل:\n\n📌 أرسل الآن كمية كارت الآسيا المراد تحويله:\n*(ملاحظة: كل 1$ آسيا = 0.3$ رصيد بالبوت)*", reply_markup=InlineKeyboardMarkup(keyboard))
        await query.answer()

    elif data.startswith("approve_asia_"):
        if user_id in admins_list:
            parts = data.split("_")
            target_id = int(parts[2])
            amount_str = parts[3]
            try:
                raw_val = float(''.join(c for c in amount_str if c.isdigit() or c == '.'))
                val = round(raw_val * 0.3, 2)
            except:
                val = 0.3
                
            users_balance[target_id] = round(users_balance.get(target_id, 0.0) + val, 2)
            save_data()
            
            await query.answer("✅ تم قبول الشحن وإضافة الرصيد بنجاح!", show_alert=True)
            try:
                await query.edit_message_caption(caption=f"{query.message.caption}\n\n✅ تمت الموافقة وتطبيق الصرف.\n💰 المضاف: ${val}")
            except:
                pass
            try:
                await context.bot.send_message(chat_id=target_id, text=f"🎉 تمت الموافقة على طلب الشحن!\n💰 تم إضافة ${val} إلى رصيدك بالبوت.")
            except:
                pass

    elif data.startswith("reject_asia_"):
        if user_id in admins_list:
            target_id = int(data.split("_")[2])
            await query.answer("❌ تم رفض طلب الشحن!", show_alert=True)
            try:
                await query.edit_message_caption(caption=f"{query.message.caption}\n\n❌ تم رفض طلب الشحن.")
            except:
                pass
            try:
                await context.bot.send_message(chat_id=target_id, text="❌ عذراً، تم رفض طلب الشحن الخاص بك.")
            except:
                pass

    elif data == "support":
        await query.message.reply_text("💬 للدعم الفني:\nراسل الأدمن: @rrrrrux")
        await query.answer()

    elif data == "admin_panel":
        if user_id in admins_list:
            user_states[user_id] = None
            total_bal = sum(users_balance.values())
            m_status = "مفعل 🛠️" if maintenance_mode else "معطل 🟢"
            smsman_bal = smsman_get_balance()
            smsman_str = f"${smsman_bal}" if smsman_bal is not None else "غير متصل"
            
            admin_text = f"⚙️ لوحة التحكم الشاملة (الأدمن):\n\n🌐 رصيد موقع SMS-Man: {smsman_str}\n📊 الإحصائيات العامة:\n👥 المستخدمين: {len(users_balance)}\n💰 إجمالي أرصدة المستخدمين: ${round(total_bal, 2)}\n🛠️ وضع الصيانة: {m_status}\n👑 عدد الأدمنية: {len(admins_list)}"
            
            admin_buttons = [
                [InlineKeyboardButton("💵 إضافة رصيد", callback_data="adm_add_bal"), InlineKeyboardButton("💸 خصم رصيد", callback_data="adm_sub_bal")],
                [InlineKeyboardButton("🚫 تصفير رصيد مستخدم", callback_data="adm_zero_bal")],
                [InlineKeyboardButton("🏷️ تعديل أسعار الأرقام", callback_data="adm_set_price")],
                [InlineKeyboardButton("📢 إذاعة للمستخدمين", callback_data="adm_broadcast"), InlineKeyboardButton("🛠️ تفعيل/إيقاف الصيانة", callback_data="adm_toggle_maint")],
                [InlineKeyboardButton("👑 رفع أدمن جديد", callback_data="adm_add_admin"), InlineKeyboardButton("🔄 نقل ملكية البوت", callback_data="adm_transfer_owner")],
                [InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="main_menu")]
            ]
            try:
                await query.edit_message_text(admin_text, reply_markup=InlineKeyboardMarkup(admin_buttons))
            except:
                await query.message.reply_text(admin_text, reply_markup=InlineKeyboardMarkup(admin_buttons))
            await query.answer()

    elif data == "adm_set_price":
        if user_id in admins_list:
            user_states[user_id] = "adm_waiting_price"
            prices_str = "\n".join([f"• `{k}`: ${v}" for k, v in country_prices.items()])
            text = f"🏷️ **إدارة وتحكم الأسعار:**\n\nالأسعار الحالية:\n{prices_str}\n\n📌 لتغيير سعر دولة أو السعر الافتراضي، أرسل الرسالة بالشكل التالي:\n`اسم الدولة` مسافة `السعر الجديد`\n\nمثال:\n`السعر الافتراضي 0.25`\n`كازاخستان 0.30`"
            try:
                await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]]))
            except:
                await query.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]]))
            await query.answer()

    elif data == "adm_toggle_maint":
        if user_id in admins_list:
            maintenance_mode = not maintenance_mode
            save_data()
            status = "مفعل 🛠️" if maintenance_mode else "معطل 🟢"
            await query.answer(f"تم تغيير وضع الصيانة إلى: {status}", show_alert=True)
            await button_handler(update, context)

    elif data in ["adm_add_bal", "adm_sub_bal", "adm_zero_bal", "adm_broadcast", "adm_add_admin", "adm_transfer_owner"]:
        if user_id in admins_list:
            user_states[user_id] = data
            prompts = {
                "adm_add_bal": "💵 أرسل الآيدي والمبلغ المراد إضافته بالشكل:\nID AMOUNT (مثال: 6862109040 5.0)",
                "adm_sub_bal": "💸 أرسل الآيدي والمبلغ المراد خصمه بالشكل:\nID AMOUNT (مثال: 6862109040 2.0)",
                "adm_zero_bal": "🚫 أرسل ID المستخدم لتصفير رصيده:",
                "adm_broadcast": "📢 أرسل الرسالة التي تريد إذاعتها لجميع المستخدمين:",
                "adm_add_admin": "👑 أرسل ID المستخدم لرفعه أدمن:",
                "adm_transfer_owner": "🔄 أرسل ID الأدمن الجديد لنقل ملكية البوت إليه:"
            }
            try:
                await query.edit_message_text(prompts[data], reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 إلغاء", callback_data="admin_panel")]]))
            except:
                await query.message.reply_text(prompts[data], reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 إلغاء", callback_data="admin_panel")]]))
            await query.answer()

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await check_subscription(user_id, context):
        await update.message.reply_text(f"⚠️ يجب عليك الاشتراك في قناة البوت أولاً: {FORCE_CHANNEL}")
        return

    state = user_states.get(user_id)
    if state == "waiting_asia_photo":
        photo_file_id = update.message.photo[-1].file_id
        amount = asia_deposit_data.get(user_id, "غير محدد")
        user_states[user_id] = None
        
        await update.message.reply_text("✅ تم استلام صورة التحويل بنجاح!\nتم إرسال الطلب إلى الأدمن للمراجعة.")

        admin_markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ قبول وإضافة الرصيد", callback_data=f"approve_asia_{user_id}_{amount}"),
                InlineKeyboardButton("❌ رفض الطلب", callback_data=f"reject_asia_{user_id}")
            ]
        ])
        username_str = update.effective_user.username if update.effective_user.username else "لا يوجد"
        caption_text = f"📥 طلب شحن جديد (آسياسيل):\n\n👤 المستخدم: {update.effective_user.full_name}\n🆔 ID المستخدم: {user_id}\n🔗 المعرف: @{username_str}\n💰 كمية تحويل الآسيا: {amount}"

        for admin in admins_list:
            try:
                await context.bot.send_photo(chat_id=admin, photo=photo_file_id, caption=caption_text, reply_markup=admin_markup)
            except:
                pass

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await check_subscription(user_id, context):
        await update.message.reply_text(f"⚠️ يجب عليك الاشتراك في قناة البوت أولاً: {FORCE_CHANNEL}")
        return

    state = user_states.get(user_id)
    msg = update.message.text

    if state == "waiting_asia_amount" and msg:
        asia_deposit_data[user_id] = msg
        user_states[user_id] = "waiting_asia_photo"
        text = f"📲 كمية آسيا المراد تحويلها: {msg}\n\n1️⃣ يرجى تحويل المبلغ المطلوب للرقم التالي:\n{ASIA_PHONE}\n\n2️⃣ قم بإرسال صورة (سكرين شوت) لإثبات عملية التحويل الآن هنا. 📸"
        keyboard = [[InlineKeyboardButton("🔙 إلغاء", callback_data="deposit")]]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if user_id in admins_list and state and msg:
        if state == "adm_waiting_price":
            try:
                parts = msg.rsplit(" ", 1)
                c_key = parts[0].strip()
                new_price = float(parts[1])
                country_prices[c_key] = new_price
                user_states[user_id] = None
                save_data()
                await update.message.reply_text(f"✅ تم تحديث سعر `{c_key}` إلى `${new_price}` بنجاح!", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ لوحة الأدمن", callback_data="admin_panel")]]))
            except:
                await update.message.reply_text("❌ صيغة خاطئة! أرسل بالشكل:\n`السعر الافتراضي 0.25` أو `كازاخستان 0.30`", parse_mode="Markdown")
            return

        elif state == "adm_add_bal":
            try:
                target_id, amount = msg.split()
                target_id, amount = int(target_id), float(amount)
                users_balance[target_id] = round(users_balance.get(target_id, 0.0) + amount, 2)
                user_states[user_id] = None
                save_data()
                await update.message.reply_text(f"✅ تم إضافة ${amount} لرصيد {target_id}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ لوحة الأدمن", callback_data="admin_panel")]]))
            except:
                await update.message.reply_text("❌ صيغة خاطئة! أرسل بالشكل: ID AMOUNT")
            return

        elif state == "adm_sub_bal":
            try:
                target_id, amount = msg.split()
                target_id, amount = int(target_id), float(amount)
                users_balance[target_id] = round(max(0.0, users_balance.get(target_id, 0.0) - amount), 2)
                user_states[user_id] = None
                save_data()
                await update.message.reply_text(f"✅ تم خصم ${amount} من رصيد {target_id}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ لوحة الأدمن", callback_data="admin_panel")]]))
            except:
                await update.message.reply_text("❌ صيغة خاطئة! أرسل بالشكل: ID AMOUNT")
            return

        elif state == "adm_zero_bal":
            if msg.isdigit():
                target_id = int(msg)
                users_balance[target_id] = 0.0
                user_states[user_id] = None
                save_data()
                await update.message.reply_text(f"✅ تم تصفير رصيد {target_id}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ لوحة الأدمن", callback_data="admin_panel")]]))
            return

        elif state == "adm_broadcast":
            user_states[user_id] = None
            count = 0
            for u_id in list(users_balance.keys()):
                try:
                    await context.bot.send_message(chat_id=u_id, text=f"📢 إشعار عام:\n\n{msg}")
                    count += 1
                except:
                    pass
            await update.message.reply_text(f"✅ تم إرسال الإذاعة لـ {count} مستخدم.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ لوحة الأدمن", callback_data="admin_panel")]]))
            return

        elif state == "adm_add_admin":
            if msg.isdigit():
                new_admin = int(msg)
                if new_admin not in admins_list:
                    admins_list.append(new_admin)
                    save_data()
                user_states[user_id] = None
                await update.message.reply_text(f"👑 تم رفع {new_admin} أدمن بنجاح!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ لوحة الأدمن", callback_data="admin_panel")]]))
            return

        elif state == "adm_transfer_owner":
            if msg.isdigit():
                new_owner = int(msg)
                admins_list.clear()
                admins_list.append(new_owner)
                user_states[user_id] = None
                save_data()
                await update.message.reply_text(f"🔄 تم نقل ملكية البوت بالكامل إلى {new_owner}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 الرئيسية", callback_data="main_menu")]]))
            return

    if state == "waiting_stars" and msg:
        if msg.isdigit():
            count = int(msg)
            if count < 1:
                await update.message.reply_text("❌ أدخل رقم أكبر من 0.")
                return
            user_states[user_id] = None
            usd_val = round(count * 0.01, 2)
            prices = [LabeledPrice(label=f"شحن {count} نجمة", amount=count)]

            await context.bot.send_invoice(
                chat_id=update.effective_chat.id,
                title="⭐ شحن رصيد بالنجوم",
                description=f"شحن {count} نجمة لزيادة رصيدك بمقدار {usd_val}$",
                payload=f"stars_deposit_{count}_{usd_val}",
                provider_token="",
                currency="XTR",
                prices=prices
            )
        else:
            await update.message.reply_text("❌ أرسل أرقام فقط.")

async def precheckout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)

async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    payload = update.message.successful_payment.invoice_payload
    parts = payload.split('_')
    stars, usd_val = int(parts[2]), float(parts[3])

    users_balance[user_id] = round(users_balance.get(user_id, 0.0) + usd_val, 2)
    save_data()
    await update.message.reply_text(f"🎉 تم الشحن بنجاح!\n⭐ دفع: {stars} نجوم\n💵 إضافة: ${usd_val}\n💰 رصيدك: ${users_balance[user_id]}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_handler(PreCheckoutQueryHandler(precheckout_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    app.add_handler(ChatMemberHandler(track_bot_block, ChatMemberHandler.MY_CHAT_MEMBER))

    print("⚡ تم تشغيل البوت بنجاح وتعريب أسماء الدول بالكامل...")
    app.run_polling()
