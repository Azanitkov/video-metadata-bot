import os
import asyncio
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from pymediainfo import MediaInfo

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set")

bot = Bot(token=TOKEN)
app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

async def analyze_video(file_path):
    media_info = MediaInfo.parse(file_path)
    general = next((t for t in media_info.tracks if t.track_type == "General"), None)
    video = next((t for t in media_info.tracks if t.track_type == "Video"), None)

    report = []
    if general and general.encoded_application:
        report.append(f"✏️ Кодировалось через: {general.encoded_application}")
    else:
        report.append("⚠️ Информация о приложении не найдена — возможно, видео редактировалось.")
    if video:
        report.append(f"🎞️ Кодек: {video.codec_id}, разрешение: {video.width}x{video.height}")

    return "\n".join(report or ["Не удалось получить данные о видео."])

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video = update.message.video or update.message.document
    if not video:
        await update.message.reply_text("Это не видео.")
        return

    file = await context.bot.get_file(video.file_id)
    file_path = f"./{video.file_id}.mp4"
    await file.download_to_drive(file_path)

    try:
        result = await analyze_video(file_path)
        await update.message.reply_text(result)
    except Exception as e:
        await update.message.reply_text(f"Ошибка при анализе видео: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

# Обработчик видео
application.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    asyncio.run(application.process_update(update))
    return "ok"

@app.route("/")
def index():
    return "Бот работает!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

