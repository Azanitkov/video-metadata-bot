import os
import asyncio
import logging
import sys

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(message)s'
)
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
app = Flask(__name__)

application = Application.builder().token(TOKEN).build()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет!")

application.add_handler(MessageHandler(filters.ALL, handle_message))

# Запускаем инициализацию и старт Application один раз
async def init():
    await application.initialize()
    await application.start()
    # Обрати внимание: мы НЕ запускаем polling, т.к. используем webhook

asyncio.get_event_loop().run_until_complete(init())

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_update = request.get_json(force=True)
    update = Update.de_json(json_update, bot)

    # Запускаем process_update в фоновом режиме текущего цикла
    loop = asyncio.get_event_loop()
    future = asyncio.run_coroutine_threadsafe(application.process_update(update), loop)
    try:
        future.result(timeout=5)
    except Exception as e:
        print(f"Error processing update: {e}")

    return "OK"

@app.route("/")
def index():
    return "Бот работает!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
