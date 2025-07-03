import os
import asyncio
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)

app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

# Обработчик сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я работаю через webhook! 🎯")

# Регистрация обработчика
application.add_handler(MessageHandler(filters.ALL, handle_message))

# Flask endpoint для webhook
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    asyncio.create_task(application.process_update(update))
    return "ok", 200

# Главная страница для теста
@app.route("/")
def index():
    return "Бот работает!", 200

# Инициализация и запуск бота
async def startup():
    await application.initialize()
    await application.start()

asyncio.get_event_loop().run_until_complete(startup())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
