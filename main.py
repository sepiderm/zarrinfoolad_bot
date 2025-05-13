import logging
import os
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

# لاگ‌گیری
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# مراحل مکالمه
SELECT_TYPE, GET_DIMENSIONS, GET_PRICE = range(3)

# اطلاعات کاربران
user_data = {}

# توکن از محیط
TOKEN = os.getenv("BOT_TOKEN")

# ربات
app = Flask(__name__)

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "OK"

# شروع
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("ورق", callback_data='ورق')],
        [InlineKeyboardButton("میلگرد", callback_data='میلگرد')],
        [InlineKeyboardButton("نبشی", callback_data='نبشی')],
        [InlineKeyboardButton("ناودانی", callback_data='ناودانی')],
        [InlineKeyboardButton("تیرآهن", callback_data='تیرآهن')],
        [InlineKeyboardButton("قوطی", callback_data='قوطی')],
        [InlineKeyboardButton("لوله", callback_data='لوله')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🔘 نوع آهن‌آلات را انتخاب کنید:", reply_markup=reply_markup)
    return SELECT_TYPE

# انتخاب نوع
async def select_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    material = query.data
    user_data[query.from_user.id] = {'type': material}

    if material in ['ورق']:
        prompt = "طول، عرض، ضخامت را وارد کنید (متر):\nمثال: 2 1 0.005"
    elif material in ['میلگرد']:
        prompt = "طول و قطر را وارد کنید (متر):\nمثال: 12 0.016"
    elif material in ['نبشی', 'ناودانی', 'تیرآهن']:
        prompt = "طول و وزن هر متر را وارد کنید:\nمثال: 6 10"
    elif material in ['قوطی', 'لوله']:
        prompt = "طول، ضلع یا قطر بیرونی، ضخامت را وارد کنید (متر):\nمثال: 6 0.04 0.002"

    await query.edit_message_text(prompt)
    return GET_DIMENSIONS

# گرفتن ابعاد
async def get_dimensions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        parts = list(map(float, update.message.text.strip().split()))
        item = user_data[user_id]['type']

        if item == 'ورق' and len(parts) == 3:
            length, width, thickness = parts
            weight = length * width * thickness * 7850
        elif item == 'میلگرد' and len(parts) == 2:
            length, diameter = parts
            area = 3.14 * (diameter / 2) ** 2
            weight = length * area * 7850
        elif item in ['نبشی', 'ناودانی', 'تیرآهن'] and len(parts) == 2:
            length, unit_weight = parts
            weight = length * unit_weight
        elif item in ['قوطی', 'لوله'] and len(parts) == 3:
            length, outer, thickness = parts
            inner = outer - 2 * thickness
            area = 3.14 * ((outer / 2) ** 2 - (inner / 2) ** 2)
            weight = length * area * 7850
        else:
            raise ValueError

        user_data[user_id]['weight'] = weight
        await update.message.reply_text(f"✅ وزن تقریبی: {weight:.2f} کیلوگرم\n\n💰 حالا قیمت هر کیلو را وارد کنید (تومان):")
        return GET_PRICE

    except ValueError:
        await update.message.reply_text("❌ ورودی نادرست بود. لطفاً دوباره و طبق فرمت گفته‌شده وارد کنید.")
        return GET_DIMENSIONS

# گرفتن قیمت
async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        price_per_kg = float(update.message.text.strip())
        weight = user_data[user_id]['weight']
        total = weight * price_per_kg
        await update.message.reply_text(f"💸 قیمت کل: {total:,.0f} تومان")
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید.")
        return GET_PRICE

# لغو
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⛔ عملیات لغو شد.")
    return ConversationHandler.END

# اجرای اپلیکیشن
if __name__ == "__main__":
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECT_TYPE: [CallbackQueryHandler(select_type)],
            GET_DIMENSIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_dimensions)],
            GET_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_price)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    po
