import os
import asyncio
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from pymediainfo import MediaInfo

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN env var is not set")

bot = Bot(token=TOKEN)
app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

async def analyze_video(file_path: str) -> str:
    media_info = MediaInfo.parse(file_path)
    general = next((t for t in media_info.tracks if t.track_type == "General"), None)
    video = next((t for t in media_info.tracks if t.track_type == "Video"), None)

    report = []
    if general and general.encoded_application:
        report.append(f"✏️ Кодировалось через: {general.encoded_application}")
    else:
        report.append("⚠️ Отсутствует инфо о приложении — возможна обработка.")
    if video:
        report.append(f"🎞️ Кодек: {video.codec_id}, {video.width}x{video.height}")

    return "\n".join(report or ["Не удалось найти данные."])

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video = update.message.video or update.message.document
    file = await context.bot.get_file(video.file_id)
    file_path = f"/tmp/{video.file_id}.mp4"
    await file.download_to_drive(file_path)

    try:
        result = await analyze_video(file_path)
        await update.message.reply_text(result)
    except Exception as e:
        await update.message.reply_text(f"Ошибка анализа: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отправьте видеофайл для анализа метаданных.")

application.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))
application.add_handler(MessageHandler(filters.ALL & ~(filters.VIDEO | filters.Document.VIDEO), handle_message))

# Инициализировать приложение при старте Flask
@app.before_first_request
def before_first_request():
    # Запускаем initialize и start в отдельном таске, чтобы не блокировать Flask
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(application.initialize())
    loop.run_until_complete(application.start())

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)

    # Здесь запускаем процесс обновления в синхронном контексте через новый event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(application.process_update(update))

    return "ok"

@app.route("/")
def index():
    return "Бот работает!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
