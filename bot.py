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

# Инициализируем приложение один раз при старте
async def init_app():
    await application.initialize()
    await application.start()
    await application.updater.start_polling()  # или пропусти, если только webhook

asyncio.get_event_loop().run_until_complete(init_app())

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)

    # Чтобы запустить async из sync в Flask, делаем так
    return asyncio.run(application.process_update(update))

@app.route("/")
def index():
    return "Бот работает!"

if __name__ == "__main__":
    app.run()
