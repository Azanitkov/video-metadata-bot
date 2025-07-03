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

# Добавление обработчика
application.add_handler(MessageHandler(filters.ALL, handle_message))

# Flask endpoint для webhook
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)

    # Вместо create_task — run (safe in sync Flask)
    asyncio.run(application.process_update(update))
    return "ok", 200

# Главная страница
@app.route("/")
def index():
    return "Бот работает!", 200

# Асинхронная инициализация Application
async def startup():
    await application.initialize()
    await application.start()

# Инициализируем один раз при старте
asyncio.get_event_loop().run_until_complete(startup())

# Запуск Flask-сервера
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
