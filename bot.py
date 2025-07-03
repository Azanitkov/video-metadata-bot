import os
import asyncio
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
app = Flask(__name__)

application = Application.builder().token(TOKEN).build()

# Обработчик сообщений (пример)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет!")

application.add_handler(MessageHandler(filters.ALL, handle_message))

# Инициализация приложения (делаем один раз)
async def init_app():
    await application.initialize()
    await application.start()
    # Для webhook polling не нужен, не вызываем .updater.start_polling()

# Запускаем инициализацию при старте
asyncio.run(init_app())

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    # Flask — синхронный, telegram.ext Application — асинхронный,
    # чтобы запустить обработку обновления асинхронно — используем asyncio.run()
    asyncio.run(application.process_update(update))
    return "ok"

@app.route("/")
def index():
    return "Бот работает!"

if __name__ == "__main__":
    # В боевом режиме надо запускать через gunicorn или другой WSGI сервер
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
