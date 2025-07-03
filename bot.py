from flask import Flask, request
import asyncio
from telegram import Update, Bot
from telegram.ext import Application

TOKEN = "ваш_токен"
bot = Bot(token=TOKEN)
app = Flask(__name__)

application = Application.builder().token(TOKEN).build()

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)

    # В Flask нельзя просто делать asyncio.get_event_loop(), надо запускать async корутину через asyncio.run
    asyncio.run(application.process_update(update))

    return "ok"

@app.route("/")
def index():
    return "Бот работает!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))