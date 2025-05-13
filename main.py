import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from flask import Flask, request
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("🔴 BOT_TOKEN environment variable not set.")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

SELECT_TYPE, GET_INPUTS, GET_PRICE = range(3)
user_data = {}

app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("ورق", callback_data='ورق'), InlineKeyboardButton("میلگرد", callback_data='میلگرد')],
        [InlineKeyboardButton("نبشی", callback_data='نبشی'), InlineKeyboardButton("ناودانی", callback_data='ناودانی')],
        [InlineKeyboardButton("تیرآهن", callback_data='تیرآهن')],
        [InlineKeyboardButton("قوطی/پروفیل", callback_data='قوطی')],
        [InlineKeyboardButton("لوله", callback_data='لوله')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("✅ لطفاً نوع مقطع را انتخاب کنید:", reply_markup=reply_markup)
    return SELECT_TYPE

async def select_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    product = query.data
    user_data[query.from_user.id] = {'type': product}

    instructions = {
        'ورق': "طول، عرض، ضخامت (متر) - مثال: 2 1 0.005",
        'میلگرد': "قطر (میلیمتر)، طول (متر) - مثال: 12 6",
        'نبشی': "طول شاخه (متر)، وزن هر متر (کیلوگرم) - مثال: 6 5.2",
        'ناودانی': "طول شاخه (متر)، وزن هر متر (کیلوگرم) - مثال: 6 7.3",
        'تیرآهن': "طول شاخه (متر)، وزن هر متر (کیلوگرم) - مثال: 12 14.8",
        'قوطی': "محیط مقطع (سانتی‌متر)، ضخامت (میلیمتر)، طول (متر) - مثال: 40 2 6",
        'لوله': "قطر بیرونی (میلیمتر)، ضخامت (میلیمتر)، طول (متر) - مثال: 100 2 6"
    }

    await query.edit_message_text(
        f"🔹 شما '{product}' را انتخاب کردید.
"
        f"لطفاً مشخصات را به این صورت وارد کنید:
{instructions[product]}"
    )
    return GET_INPUTS

async def get_inputs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    product_type = user_data[user_id]['type']
    try:
        values = list(map(float, update.message.text.strip().split()))
        weight = 0

        if product_type == 'ورق':
            length, width, thickness = values
            weight = length * width * thickness * 7850
        elif product_type == 'میلگرد':
            diameter, length = values
            weight = (diameter ** 2) * length * 0.00617
        elif product_type in ['نبشی', 'ناودانی', 'تیرآهن']:
            length, unit_weight = values
            weight = length * unit_weight
        elif product_type == 'قوطی':
            perimeter_cm, thickness_mm, length = values
            perimeter = perimeter_cm / 100
            thickness = thickness_mm / 1000
            weight = perimeter * thickness * length * 7850
        elif product_type == 'لوله':
            outer_dia, thickness_mm, length = values
            weight = 0.02466 * (outer_dia - thickness_mm) * thickness_mm * length

        user_data[user_id]['weight'] = weight
        await update.message.reply_text(
            f"✅ وزن تقریبی: {weight:.2f} کیلوگرم

"
            f"📞 برای دریافت قیمت تماس بگیرید: 09123456789
"
            f"💬 حالا لطفاً قیمت هر کیلوگرم را وارد کنید (تومان):"
        )
        return GET_PRICE

    except Exception:
        await update.message.reply_text("❌ ورودی نامعتبر است. لطفاً طبق فرمت خواسته‌شده دوباره وارد کنید.")
        return GET_INPUTS

async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        price_per_kg = float(update.message.text.strip())
        weight = user_data[user_id]['weight']
        total = price_per_kg * weight
        await update.message.reply_text(f"💰 قیمت کل: {total:,.0f} تومان")
        user_data.pop(user_id, None)
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ عدد وارد شده معتبر نیست. دوباره وارد کنید:")
        return GET_PRICE

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data.pop(update.message.from_user.id, None)
    await update.message.reply_text("⛔ عملیات لغو شد.")
    return ConversationHandler.END

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "OK"

if __name__ == "__main__":
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECT_TYPE: [CallbackQueryHandler(select_type)],
            GET_INPUTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_inputs)],
            GET_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_price)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    port = int(os.environ.get("PORT", 10000))
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        webhook_url=f"https://zarinsteelbot.onrender.com/{TOKEN}"
    )
