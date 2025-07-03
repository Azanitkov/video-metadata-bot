import os
from flask import Flask, request
import requests
from pymediainfo import MediaInfo
from telegram import Bot, Update
from telegram.ext import Dispatcher, MessageHandler, Filters

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)

app = Flask(__name__)
dispatcher = Dispatcher(bot, None, workers=0)

def analyze_video(file_path):
    media_info = MediaInfo.parse(file_path)
    general = next((t for t in media_info.tracks if t.track_type == "General"), None)
    video = next((t for t in media_info.tracks if t.track_type == "Video"), None)

    report = []
    if general and general.encoded_application:
        report.append(f"✏️ Кодировалось через: {general.encoded_application}")
    if not general.encoded_application:
        report.append("⚠️ Отсутствует инфа о приложении — возможна обработка.")
    if video:
        report.append(f"🎞️ Кодек: {video.codec_id}, {video.width}x{video.height}")

    return "\n".join(report or ["Не удалось найти данные."])

def handle_video(update: Update, context):
    video = update.message.video or update.message.document
    file = bot.get_file(video.file_id)
    file_path = f"./{video.file_id}.mp4"
    file.download(file_path)

    try:
        result = analyze_video(file_path)
        update.message.reply_text(result)
    except Exception as e:
        update.message.reply_text(f"Ошибка анализа: {e}")
    finally:
        os.remove(file_path)

dispatcher.add_handler(MessageHandler(Filters.video | Filters.document.video, handle_video))

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

@app.route("/")
def index():
    return "Бот работает!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
